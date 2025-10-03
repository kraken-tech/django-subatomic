from collections.abc import Generator

import pytest

from django_subatomic import _utils as utils


class _AnError(Exception):
    pass


class TestContextManager:
    """
    Tests for the `contextmanager` decorator.
    """

    def test_context_manager(self) -> None:
        """
        Generators that yield once can be used as context managers.
        """

        @utils.contextmanager
        def good_example(steps: list[str]) -> Generator[str, None, None]:
            steps.append("enter")
            yield "yielded"
            steps.append("exit")

        steps: list[str] = []
        with good_example(steps) as yielded:
            steps.append("body")

        assert steps == ["enter", "body", "exit"]
        assert yielded == "yielded"

    def test_context_body_raises_exception(self) -> None:
        """
        Exceptions raised in the context body are propagated.
        """

        @utils.contextmanager
        def basic_context() -> Generator[None, None, None]:
            yield

        with pytest.raises(_AnError):
            with basic_context():
                raise _AnError

    def test_context_manager_handles_exception(self) -> None:
        """
        Context managers may handle exceptions raised in the context body.
        """

        @utils.contextmanager
        def handle_exception() -> Generator[None, None, None]:
            # Make sure the error is raised, but don't propagate it.
            with pytest.raises(_AnError):
                yield

        with handle_exception():
            raise _AnError

    def test_context_manager_handles_exception_but_then_yields(self) -> None:
        """
        A second yield must not happen after an exception is handled.
        """

        @utils.contextmanager
        def handle_exception_but_yield_twice() -> Generator[None, None, None]:
            try:
                yield
            except _AnError:
                yield

        with pytest.raises(utils.UnexpectedSecondYield):
            with handle_exception_but_yield_twice():
                raise _AnError

    def test_fails_without_yield(self) -> None:
        """
        Decorated functions must yield once.
        """

        @utils.contextmanager
        def yield_not_run() -> Generator[None, None, None]:
            if False:
                # Yield makes this a generator, but the yield is never run.
                yield  # type: ignore[unreachable]

        with pytest.raises(utils.DidNotYield):
            with yield_not_run():
                ...

    def test_fails_on_multiple_yields(self) -> None:
        """
        Decorated functions must not yield multiple times.
        """

        @utils.contextmanager
        def yields_twice(steps: list[str]) -> Generator[None, None, None]:
            steps.append("enter")
            yield
            steps.append("between")
            yield  # This line causes the failure.
            # The following line will never be reached.
            steps.append("after")  # pragma: no cover

        steps: list[str] = []
        with pytest.raises(utils.UnexpectedSecondYield):
            with yields_twice(steps):
                steps.append("body")

        assert steps == ["enter", "body", "between"]

    def test_does_not_work_as_a_decorator(self) -> None:
        """
        Functions decorated with `contextmanager` cannot be used as decorators.
        """

        @utils.contextmanager
        def not_a_decorator() -> Generator[None, None, None]:
            yield  # pragma: no cover

        with pytest.raises(
            TypeError, match="takes 0 positional arguments but 1 was given"
        ):
            # This doesn't work as a decorator.
            @not_a_decorator  # type: ignore[call-arg]
            def not_reached() -> None: ...
