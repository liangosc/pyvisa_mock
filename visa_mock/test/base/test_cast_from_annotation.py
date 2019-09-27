import pytest
from visa_mock.base.base_mocker import cast_from_annotation


def test_main():

    @cast_from_annotation
    def test_function(z: int, b: float) -> float:
        return z + b

    assert test_function("2", "3.4") == 5.4


def test_mixing_args_and_kwargs():

    @cast_from_annotation
    def test_function(z: int, b: float, c: float) -> float:
        return (z + b) / c

    assert test_function("2", c="3.4", b="2") == 4 / 3.4


def test_error():

    with pytest.raises(
            ValueError,
            match="This decorator requires all arguments to be annotated"
    ):
        @cast_from_annotation
        def test_function(z: int, b: float, c) -> float:
            return z + b


def test_classes():

    class TestClass:

        @cast_from_annotation
        def test_function(self, z: int, b: float) -> float:
            return z + b

    test_class = TestClass()
    assert test_class.test_function("2", "3.4") == 5.4
