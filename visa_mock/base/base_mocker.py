from inspect import signature
from typing import Dict, List, Callable, Any, cast, get_type_hints, Optional
import re
import time


class MockingError(Exception):
    pass


class AnnotationError(Exception):
    pass


class SCPIHandler:
    """
    SCPI handlers contain *class* methods which are called at runtime when
    a SCPI message needs to be handled.

    The handler has two tasks:

    1) Because SCPI messages are strings, this handler will cast string
        values to the appropriate type depending on the annotation of the
        input method. The method will be called with the recast arguments.

    2) A handler can combine two handlers into one. Each handler handles part
        of a scpi string, for example ":INSTR:CHANNEL(.*)" and ":VOLTAGE?".
        The handler of the former returns a mock sub-module instance, containing
        a handler method for the latter substring.
    """
    @classmethod
    def from_method(cls, method: Callable) -> 'SCPIHandler':
        """
        Construct a handler from a class method.
        """
        parameters = dict(signature(method).parameters)

        try:
            parameters.pop("self")
        except KeyError:
            raise AnnotationError("This can only decorate class methods")

        type_hints = get_type_hints(method)

        try:
            return_type = type_hints.pop("return")
        except KeyError:
            raise AnnotationError("All functions must have an annotated return type")

        annotations = list(type_hints.values())

        if len(annotations) != len(parameters):
            raise AnnotationError(
                "This decorator requires all arguments to be annotated"
            )

        return cls(method, annotations, return_type)

    @classmethod
    def combine(
            cls,
            handler: 'SCPIHandler',
            sub_handler: 'SCPIHandler'
    ) -> 'SCPIHandler':
        """
        Combine two handlers, each processing part of a SCPI message.
        """
        handler_arg_count = len(handler.annotations)
        annotations = list(handler.annotations)
        annotations.extend(sub_handler.annotations)

        def method(self, *args):
            handler_args = args[:handler_arg_count]
            sub_handler_args = args[handler_arg_count:]
            # The first handler returns a submodule
            sub_module = handler(self, *handler_args)
            # 'sub_handler' is a *class* method, meaning that the
            # first argument needs to be a 'self'. This is
            # provided by the first handler.
            return sub_handler(
                sub_module,
                *sub_handler_args
            )

        return cls(
            method, annotations, sub_handler.return_type
        )

    def __init__(
            self,
            method: Callable,
            annotations: List,
            return_type: type
    ) -> None:
        """
        The __init__ is never called directly. We use 'from_method' and 'combine'
        instead

        Arguments:
            method: A method of a mocker class (not an instance method)
            annotations: A list of types acquired by inspecting the
                method type hints
            return_type: Specify the return type of the method.
        """
        self.method = method
        self.annotations = annotations
        self.return_type = return_type
        self.call_delay = None

    def __call__(self, mocker_self, *args):
        """
        The values in the arguments are strings because we have parsed a
        SCPI message string. Convert these string to the appropriate type
        using the annotations and call the handler method.
        """
        new_args = [
            annotation_type(value)
            for annotation_type, value in zip(self.annotations, args)
        ]

        return self.method(mocker_self, *new_args)


__tmp_scpi_dict__: Dict[str, SCPIHandler] = {}


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

    def __init__(self, call_delay: float = 0.0):
        self._call_delay = call_delay

    def set_call_delay(
            self,
            call_delay: float,
            scpi_string: Optional[str] = None
    ) -> None:
        """
        This method set the call delay to either the whole instrument, or the
        scpi command specified.

        Args:
            call_delay: the intended delay value in second.
            scpi_string: when provided, this method will apply the call_delay
                to this scpi command only.
        """
        if scpi_string is None:
            self._call_delay = call_delay
        else:
            self.__scpi_dict__[scpi_string].call_delay = call_delay

    @classmethod
    def scpi(cls, scpi_string: str) -> Callable:
        def decorator(function):
            handler = SCPIHandler.from_method(function)
            return_type = handler.return_type

            if not isinstance(return_type, MockerMetaClass):
                __tmp_scpi_dict__[scpi_string] = handler
                return

            # The function being decorated itself returns a Mocker. This is very
            # useful as it allows mockers to be modular. Further processing of the
            # scpi string will be handled by the submodule.
            # For an example, see instruments.py in the folder 'tests\mock_instruments\'
            # and specifically study the class 'Mocker3'

            SubModule = cast(MockerMetaClass, return_type)

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

        if handler.call_delay is not None:
            time.sleep(handler.call_delay)
        else:
            time.sleep(self._call_delay)

        return str(handler(self, *args))


scpi = BaseMocker.scpi
