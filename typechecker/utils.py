import warnings

from typechecker.exceptions import TypeCheckError, TypeCheckWarning


def raise_exception_or_warning(msg: str, *, use_warning: bool):
    """
    Utility function to raise an exception or a warning.
    """
    if use_warning:
        warnings.warn(msg, TypeCheckWarning)
    else:
        raise TypeCheckError(msg)


