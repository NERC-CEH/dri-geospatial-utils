import pytest

from mypackage.module import add_int


def test_errors() -> None:
    with pytest.raises(TypeError):
        add_int(1, "3")
    with pytest.raises(TypeError):
        add_int({1, 2}, 5)


@pytest.mark.parametrize("x,y,expected", [[1, 2, 3], [-4, 10, 6], [1000, 100, 1100]])
def test_result(x: int, y: int, expected: int) -> None:
    assert add_int(x, y) == expected
