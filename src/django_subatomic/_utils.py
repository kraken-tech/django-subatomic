import functools
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Literal


def contextmanager[**P_Args, T_YieldType](
    func: Callable[P_Args, Generator[T_YieldType]],
) -> Callable[P_Args, AbstractContextManager[T_YieldType]]:
    """
    Make a generator function into a context manager.

    Similar to `contextlib.contextmanager`, except it does not allow the
    returned function to be used as a decorator
    """

    @functools.wraps(func)
    def wrapper(
        *args: P_Args.args, **kwargs: P_Args.kwargs
    ) -> AbstractContextManager[T_YieldType]:
        gen = func(*args, **kwargs)
        return _ContextManagerOnly(gen)

    return wrapper


class DidNotYield(Exception):
    pass


class UnexpectedSecondYield(Exception):
    pass


class _ContextManagerOnly[T_YieldType]:
    """
    Wraps a generator to act as a context manager.
    """

    def __init__(self, gen: Generator[T_YieldType]) -> None:
        self.gen = gen

    def __enter__(self) -> T_YieldType:
        try:
            # Run the generator up until the 'yield'.
            return next(self.gen)
        except StopIteration as e:
            raise DidNotYield from e

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[True] | None:
        # An exception was raised from the 'with' block.
        if exc_val is not None:
            try:
                # Throw the exception into the generator's 'yield' point.
                self.gen.throw(exc_val)
            except StopIteration:
                # The generator handled the exception. Returning `True`
                # suppresses the exception from propagating.
                return True
            else:
                # The generator handled the exception but then yielded again.
                raise UnexpectedSecondYield

        # The 'with' block completed without exception.
        else:
            try:
                # Run the generator after the 'yield'.
                next(self.gen)
            except StopIteration:
                # A clean exit.
                return None
            else:
                # The generator yielded a second time.
                raise UnexpectedSecondYield
