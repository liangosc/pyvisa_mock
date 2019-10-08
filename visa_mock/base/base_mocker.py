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
    def combine(cls, function1: Callable, function2: Callable):

        parameters1, annotations1, _ = \
            cls._get_params_and_annotations(function1)

        parameters2, annotations2, return_type = \
            cls._get_params_and_annotations(function2)

        parameters = dict(parameters1)
        annotations = dict(annotations1)

        parameters.update(parameters2)
        annotations.update(annotations2)

        def function(*args):
            args1 = args[:len(parameters1)]
            args2 = args[len(parameters1):]
            self = function1(*args1)
            return function2(self, *args2)

        return cls(function, parameters, annotations, return_type)

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

            for scpi, handler in return_type.__scpi_dict__.items():
                __tmp_scpi_dict__[scpi_string + scpi] = SCPIHandler.combine(
                    function, handler.function
                )

        return decorator

    def send(self, scpi_string: str) -> Any:

        found = False
        args = None
        function = None

        for regex_pattern in self.__scpi_dict__:
            search_result = re.search(regex_pattern, scpi_string)
            if search_result:
                if not found:
                    found = True
                    function = self.__scpi_dict__[regex_pattern]
                    args = search_result.groups()
                else:
                    raise MockingError(
                        f"SCPI command {scpi_string} matches multiple mocker "
                        f"class entries"
                    )

        if not found:
            raise ValueError(f"Unknown SCPI command {scpi_string}")

        return str(function(self, *args))


scpi = BaseMocker.scpi

