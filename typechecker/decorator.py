import functools
import typing

from typechecker.checkers import FuncCallTypeChecker


def type_check(func: typing.Callable = None, *,
               check_args: bool = True,
               check_return: bool = True,
               force_annotations: bool = False) -> typing.Callable:
    """
    It works as a decorator or a function to generate a decorator for type
    checking.
    If `func` is supplied, it will decorate the function with type checking.
    The type checker can be found at the `._type_checker` attribute.
    >>> @type_check
    ... def foo(x: int, y: float) -> float:
    ...    return x * y
    >>> try: foo(1, 2)
    ... except Exception as exc: repr(exc) # doctest:+ELLIPSIS
    typechecker.exceptions.TypeCheckError...
    If `func` is not supplied, it will generates a specified decorator. The 
    specified decorator will decorate the function with type checking, 
    configured with the keyword only arguments supplied at generation.
    >>> @type_check(check_args=False)
    ... def foo(x: int, y: float) -> float:
    ...    return x * y
    >>> foo(1.0, 2) # doctest:+ELLIPSIS
    3
    :param func: The target function to be decorated.
    :param check_args: If check the argument types or not. Default is True.
    :param check_return: If check the return types or not. Default is True.
    :param force_annotation: If all checked arguments / returns needs to
    be annotated. Default is False.
    :return: A decorated function or a decorator, depends on whether `func` 
        argument is supplied.
    """
    if func is None:
        def type_check_decorator(func):
            return type_check(func,
                              check_args=check_args,
                              check_return=check_return,
                              force_annotations=force_annotations)

        return type_check_decorator
    else:
        checker = FuncCallTypeChecker(func,
                                      check_args=check_args,
                                      check_return=check_return,
                                      force_annotation=force_annotations)

        @functools.wraps(func)
        def type_checked(*args, **kwargs):
            return checker(*args, **kwargs)

        type_checked._type_checker = checker
        return type_checked


def type_check_setting(*, check_iterator: bool = None,
                       check_callable: bool = None) -> None:
    """
    Global settings for type check. Supply keyword arguments to change them.
    :param check_iterator: If check iterator types or not. If set `True`,
        the iterators will be checked while it is being consumed. If set
        `False`, the iterators will not be checked.
    :param check_callable: If check callable types or not. If set `True`,
        the callable will be checked against its annotations. If set `False`,
        the callable will not be checked.
    :return: None.
    """
    if check_iterator is not None:
        type_check._settings[check_iterator] = check_iterator
    if check_callable is not None:
        type_check._settings[check_callable] = check_callable
