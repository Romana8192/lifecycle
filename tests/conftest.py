import pytest

from lifecycle import (
    BaseExecutableHook,
    HookRequirement,
    HookResult,
)


class SuccessfulHook(BaseExecutableHook):
    def _do_init(self) -> HookResult:
        return HookResult.SUCCESS

    def _do_quit(self) -> HookResult:
        return HookResult.SUCCESS

    def _do_reset(self) -> HookResult:
        return HookResult.SUCCESS

    def _do_error(self) -> HookResult:
        return HookResult.SUCCESS


class FailingHook(BaseExecutableHook):
    def _do_init(self) -> HookResult:
        return HookResult.FAILURE

    def _do_quit(self) -> HookResult:
        return HookResult.FAILURE

    def _do_reset(self) -> HookResult:
        return HookResult.FAILURE

    def _do_error(self) -> HookResult:
        return HookResult.FAILURE


class FatalHook(BaseExecutableHook):
    requirement = HookRequirement.REQUIRED

    def _do_init(self) -> HookResult:
        return HookResult.FATAL

    def _do_quit(self) -> HookResult:
        return HookResult.FATAL

    def _do_reset(self) -> HookResult:
        return HookResult.FATAL

    def _do_error(self) -> HookResult:
        return HookResult.FATAL


class ExceptionHook(BaseExecutableHook):
    def _do_init(self) -> HookResult:
        raise RuntimeError("test error")

    def _do_quit(self) -> HookResult:
        raise RuntimeError("test error")

    def _do_reset(self) -> HookResult:
        raise RuntimeError("test error")

    def _do_error(self) -> HookResult:
        raise RuntimeError("test error")


@pytest.fixture
def success_hook() -> SuccessfulHook:
    return SuccessfulHook("success")


@pytest.fixture
def fail_hook() -> FailingHook:
    return FailingHook("fail")


@pytest.fixture
def fatal_hook() -> FatalHook:
    return FatalHook("fatal")


@pytest.fixture
def exception_hook() -> ExceptionHook:
    return ExceptionHook("exception")
