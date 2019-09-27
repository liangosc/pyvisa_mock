from inspect import signature
from typing import Dict, Callable, Any, get_type_hints
import re


__tmp_scpi_dict__: Dict[str, Callable] = {}


def cast_from_annotation(function):
    """
    Cast function arguments to types given in the hints provided in the
    type annotation.

    Example:
         >>> @cast_from_annotation
         ... def f(x: int, y: float):
         ...   return x + y
         >>> f("2", "3.4")
         ... 5.4
    """
    parameters = dict(signature(function).parameters)

    annotations = {}
    if "self" in parameters:
        annotations["self"] = lambda x: x

    annotations.update(get_type_hints(function))
    annotations.pop("return", None)

    if len(annotations) != len(parameters):
        raise ValueError(
            "This decorator requires all arguments to be annotated"
        )

    def inner(*args, **kwargs):

        kwargs.update(dict(zip(annotations, args)))

        new_kwargs = {
            name: annotations[name](value)
            for name, value in kwargs.items()
        }

        return function(**new_kwargs)

    return inner


class MockingError(Exception):
    pass


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
            __tmp_scpi_dict__[scpi_string] = cast_from_annotation(
                function
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

        new_function = function
        return str(new_function(self, *args))


scpi = BaseMocker.scpi

