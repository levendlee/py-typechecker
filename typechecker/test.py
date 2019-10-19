import typing
from typechecker.decorator import type_check


@type_check
def basic(a: int, *b: float,
          c: typing.Tuple[int, float], **d: typing.List[int]) -> float:
    return a + sum(b) + sum(c) + sum(sum(_) for _ in d.values())


# basic(0.0,1,c=2,d=3)
# basic(0,1,c=2,d=3)
# basic(0, 1.0, 1.1, c=(2.0, 3), d=3)
# basic(0, 1.0, 1.1, c=(2, 3.0), d=3)
basic(0, 1.0, 1.1, c=(2, 3.0), d0=[3, 4], d1=[5, 6])
