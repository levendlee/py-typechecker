import collections
import inspect
import typing

from typechecker.exceptions import TypeCheckError


class TypeChecker(object):
    """
    A general type checker that performs a basic type checking through
    `isinstance` function.
    """

    def __init__(self, type_: typing.Type):
        """
        :param type_: The expected type, presented as type annotation.
        """
        self._type = type_

    def __call__(self, obj: typing.Any) -> typing.Any:
        if not isinstance(obj, self._type):
            self.raise_error(obj)
        return obj

    def raise_error(self, obj: typing.Any, msg: str = None) -> None:
        msg = (msg or
               'Expect: "{expect_type}".\n'
               'Actual "{actual_type}({obj})".\n'.format(
                   expect_type=repr(self._type),
                   actual_type=repr(obj.__class__),
                   obj=repr(obj))
               )
        raise TypeCheckError(msg)


class TupleTypeChecker(TypeChecker):
    """
    A tuple type checker that checks if an object is a tuple and checks its
    elements types.
    """

    def __init__(self, type_: typing.Type):
        super().__init__(type_)
        self._elem_checkers = tuple(get_type_checker(t) for t in type_.__args__)

    def __call__(self, obj: typing.Any) -> typing.Any:
        # check if the object is a tuple
        if not isinstance(obj, tuple):
            self.raise_error(obj)
        # check the length of the tuple
        # TODO: Handle ellipsis
        if len(obj) != len(self._elem_checkers):
            self.raise_error(obj, "Length of the tuple mismatch!")
        # check the element types of the tuple
        for idx, checker in enumerate(self._elem_checkers):
            do_type_check(checker,
                          obj[idx],
                          "The #{} element has incompatible type!".format(idx))
        return obj


class ListTypeChecker(TypeChecker):
    """
    A list type checker that checks if an object is a list and checks its
    element type.
    """

    def __init__(self, type_: typing.Type):
        super().__init__(type_)
        self._elem_checker = get_type_checker(type_.__args__[0])

    def __call__(self, obj: typing.Any) -> typing.Any:
        # check if the object is a list
        if not isinstance(obj, list):
            self.raise_error(obj)
        # check the element types of the list
        checker = self._elem_checker
        for idx, item in enumerate(obj):
            do_type_check(checker,
                          item,
                          "The #{} element has incompatible type!".format(idx))
        return obj


class DictTypeChecker(TypeChecker):
    """
    A list type checker that checks if an object is a list and checks its
    key and value types.
    """

    def __init__(self, type_: typing.Type):
        super().__init__(type_)
        self._key_checker = get_type_checker(type_.__args__[0])
        self._val_checker = get_type_checker(type_.__args__[1])

    def __call__(self, obj: typing.Any) -> typing.Any:
        # check if the object is a list
        if not isinstance(obj, dict):
            self.raise_error(obj)
        # check the element types of the list
        key_checker = self._key_checker
        val_checker = self._val_checker
        for key, val in obj.items():
            do_type_check(key_checker,
                          key,
                          "Found a key that has incompatible type!")
            do_type_check(val_checker,
                          val,
                          "Found a value that has incompatible type!")
        return obj


class SetTypeChecker(TypeChecker):
    """
    A set type checker that checks if an object is a set and checks its
    element types.
    """

    def __init__(self, type_: typing.Type):
        super().__init__(type_)
        self._elem_checker = get_type_checker(type_.__args__[0])

    def __call__(self, obj: typing.Any) -> typing.Any:
        if not isinstance(obj, set):
            self.raise_error(obj)
        # check the element types
        checker = self._elem_checker
        for idx, item in enumerate(obj):
            do_type_check(checker,
                          item,
                          "Found an element that has incompatible type!")
        return obj


class EmptyTypeChecker(TypeChecker):
    """
    An empty type checker that does nothing at runtime.
    """

    def __init__(self):
        super().__init__(typing.Any)

    def __call__(self, obj: typing.Any) -> typing.Any:
        return obj


# a simple way to achieve singleton
EmptyTypeChecker = EmptyTypeChecker()


def get_type_checker(type_: typing.Type) -> TypeChecker:
    """
    A dynamic dispatch for type checker creation.
    :param type_: The target type
    :return: The type checker for the dispatch.
    """

    def create_type_checker(type_: typing.Type) -> TypeChecker:
        if isinstance(type_, typing._VariadicGenericAlias):
            return TypeChecker(type_)

        if isinstance(type_, typing._GenericAlias):
            alias_checkers = {
                tuple: TupleTypeChecker,
                list: ListTypeChecker,
                dict: DictTypeChecker,
                set: SetTypeChecker
            }
            origin = type_.__origin__
            if origin in alias_checkers:
                return alias_checkers[origin](type_)

        if type_ == typing.Any or type_ == typing.NoReturn or type_ is None:
            return EmptyTypeChecker

        return TypeChecker(type_)

    cache = get_type_checker._cache
    if type_ not in cache:
        cache[type_] = create_type_checker(type_)
    return cache[type_]


get_type_checker._cache = {}


def do_type_check(checker: TypeChecker, obj: typing.Any, message: str) -> \
        typing.Any:
    """
    A utility function to form the trace of the type checking error.
    :param checker: Typechekcer to be used.
    :param obj: The object to be checked.
    :param message: The error message to print on current level.
    :return: The object for type checking.
    """
    try:
        return checker(obj)
    except TypeCheckError as err:
        raise TypeCheckError(message) from err


class FuncCallTypeChecker(object):
    """
    A function call type checker that checks if a function call matches the
    typing annotations at runtime.
    """

    def __init__(self, func: typing.Callable, *,
                 check_args: bool, check_return: bool, force_annotation: bool):
        """
        Initialize the function type checker with target function and settings.
        :param func: The target function to be checked at call.
        :param check_args: If check the arguments types or not.
        :param check_return: If check the return types or not.
        :param force_annotation: If all arguments / returns needs to be
            annotated.
        """
        self._func = func
        self._check_args = check_args
        self._check_return = check_return

        # argspec is a namedtuple. details in `inspect` module documentation
        argspec = inspect.getfullargspec(func)

        def create_checker(arg_name: str):
            """
            Create a `TypeChecker` if argument / return is annotated.
            Otherwise create a `EmptyChecker` to avoid type check.
            """
            try:
                annotation = argspec.annotations.get(arg_name)
            except KeyError:
                if force_annotation:
                    raise TypeError('Function "{}" must be fully '
                                    'annotated.'.format(repr(func)))
                annotation = None
            return get_type_checker(annotation)

        def create_checker_dict(arg_name_list: typing.Sequence[str]) \
                -> typing.Mapping[str, TypeChecker]:
            """
            Create a ordered dict mapping from positional / keyword-only
            argument names to their corresponding type checkers.
            """
            return collections.OrderedDict(
                (arg_name, create_checker(arg_name)) for arg_name in
                arg_name_list
            )

        # positional argument type checkers
        self._arg_checkers = create_checker_dict(argspec.args)
        # keyword-only argument type checkers
        self._kw_checkers = create_checker_dict(argspec.kwonlyargs)
        # *args (variadic positional-only arguments) type checker
        self._varg_checker = create_checker(argspec.varargs)
        # **kwargs (variadic keyword-only arguments) type checker
        self._vkw_checker = create_checker(argspec.varkw)
        # return type checker
        self._ret_checker = create_checker('return')

        # get positional argument defaults
        arg_defaults = argspec.defaults or []
        self._arg_defaults = {
            arg: default
            for arg, default in
            zip(argspec.args[-len(arg_defaults):0], arg_defaults)
        }
        # check positional argument defaults types at initialization
        for name, default in self._arg_defaults.items():
            do_type_check(
                self._arg_checkers[name],
                default,
                'Positional argument "{}" has '
                'an incompatible default value!'.format(name)
            )

        self._kw_defaults = argspec.kwonlydefaults or {}
        # check keyword-only argument defaults types at initialization
        for name, default in self._kw_defaults.items():
            do_type_check(
                self._kw_checkers[name],
                default,
                'Keyword-only argument "{}" has '
                'an incompatible default value!'.format(name)
            )

    def __call__(self, *args, **kwargs):
        """
        Perform type checking at call time and pass through the function call
        return.
        Here we ignores the missing / redundant argument check. It can be
        done. But it is unnecessary (as the `RuntimeError` will be raised by the
        interpreter) and it is not the responsibility of type checking.
        """
        if self._check_args:
            arg_idx, num_arg = 0, len(args)
            # check position argument types
            for name, checker in self._arg_checkers.items():
                if arg_idx == num_arg:
                    break
                do_type_check(
                    checker,
                    args[arg_idx],
                    'Positional argument "{}" '
                    'takes a incompatible value!'.format(name)
                )
                arg_idx += 1

            # all the unchecked positional arguments will be checked against
            # the *args argument (variadic positional argument) type.
            # if redundant positional arguments are supplied, but there is no
            # *args argument (get an empty checker), then these arguments won't
            # be checked.
            checker = self._varg_checker
            while arg_idx != num_arg:
                do_type_check(
                    checker,
                    args[arg_idx],
                    "#{} positional argument "
                    "takes a incompatible value".format(arg_idx)
                )
                arg_idx += 1

            # check keyword argument types
            for name, value in kwargs.items():
                # first, check against positional arguments
                if name in self._arg_checkers:
                    checker = self._arg_checkers[name]
                # second, check against keyword-only arguments
                elif name in self._kw_checkers:
                    checker = self._kw_checkers[name]
                # third, check against the **kwargs argument
                # all the unchecked keyword arguments will be checked against
                # the **kwargs type.
                # if redundant keyword arguments are supplied, but there is not
                # **kwargs argument (get an empty checker), then these arguments
                # won't be checked.
                else:
                    checker = self._vkw_checker
                do_type_check(
                    checker,
                    value,
                    'Keyword argument "{}" '
                    'takes a incompatible value!'.format(name)
                )

        ret = self._func(*args, **kwargs)

        if self._check_return:
            # check return types
            do_type_check(self._ret_checker,
                          ret,
                          'Return a incompatible value!')

        return ret
