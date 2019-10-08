from inspect import signature
from typing import Dict, Callable, Any, get_type_hints
import re


__tmp_scpi_dict__: Dict[str, Callable] = {}


class MockingError(Exception):
    pass


class AnnotationError(Exception):
    pass


class SCPIHandler:

    @staticmethod
    def _get_params_and_annotations(function):
        parameters = dict(signature(function).parameters)
        annotations = {
            "self": lambda x: x
        }

        annotations.update(get_type_hints(function))

        try:
            return_type = annotations.pop("return")
        except KeyError:
            raise AnnotationError("All functions must have an annotated return type")

        if len(annotations) != len(parameters):
            raise AnnotationError(
                "This decorator requires all arguments to be annotated"
            )

        return parameters, annotations, return_type

    @classmethod
    def combine(cls, handler1: 'SCPIHandler', handler2: 'SCPIHandler'):

        parameters = dict(handler1.parameters)
        annotations = dict(handler1.annotations)

        parameters.update(handler2.parameters)
        annotations.update(handler2.annotations)

        def function(*args):
            args1 = args[:len(handler1.parameters)]
            args2 = args[len(handler1.parameters):]  # NOTE: This is *not* a bug... use 'handler1' here

            return handler2(
                handler1(*args1),
                *args2
            )

        return cls(
            function, parameters, annotations, handler2.return_type
        )

    def __init__(
            self,
            function: Callable,
            parameters: Dict = None,
            annotations: Dict = None,
            return_type: type = None
    ):

        self.function = function

        if all([parameters, annotations, return_type]):
            self.parameters = parameters
            self.annotations = annotations
            self.return_type = return_type
            return

        self.parameters, self.annotations, self.return_type = \
            self._get_params_and_annotations(function)

    def __call__(self, *args):

        new_args = [
            tp(value) for tp, value in zip(self.annotations.values(), args)
        ]

        return self.function(*new_args)


class MockerMetaClass(type):
    """
    We need a custom metaclass as right after class declaration
    we need to modify class attributes: The `__scpi_dict__` needs
    to be populated
    """

    def __new__(cls, *args, **kwargs):
        mocker_class = super().__new__(cls, *args, **kwargs)
        mocker_class.__scpi_dict__ = dict(__tmp_scpi_dict__)

        names = list(__tmp_scpi_dict__.keys())
        for name in names:
            __tmp_scpi_dict__.pop(name)

        return mocker_class


class BaseMocker(metaclass=MockerMetaClass):
    __scpi_dict__: Dict[str, Callable] = {}

    @classmethod
    def scpi(cls, scpi_string: str) -> Callable:
        def decorator(function):
            handler = SCPIHandler(function)
            return_type = handler.return_type

            if not isinstance(return_type, MockerMetaClass):
                __tmp_scpi_dict__[scpi_string] = handler
                return

            # The function being decorated itself returns a Mocker. This is very
            # useful as it allows mockers to be modular. Further processing of the
            # scpi string will be handled by the submodule.
            # For an example, see instruments.py in the folder 'tests\mock_instruments\'
            # and specifically study the class 'Mocker3'

            SubModule = return_type

            for scpi_sub_string, sub_handler in SubModule.__scpi_dict__.items():
                __tmp_scpi_dict__[scpi_string + scpi_sub_string] = SCPIHandler.combine(
                    handler, sub_handler
                )

        return decorator

    def send(self, scpi_string: str) -> Any:

        found = False
        args = None
        handler = None

        for regex_pattern in self.__scpi_dict__:
            search_result = re.search(regex_pattern, scpi_string)
            if search_result:
                if not found:
                    found = True
                    handler = self.__scpi_dict__[regex_pattern]
                    args = search_result.groups()
                else:
                    raise MockingError(
                        f"SCPI command {scpi_string} matches multiple mocker "
                        f"class entries"
                    )

        if not found:
            raise ValueError(f"Unknown SCPI command {scpi_string}")

        return str(handler(self, *args))


scpi = BaseMocker.scpi

