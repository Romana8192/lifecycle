from unittest.mock import MagicMock

from lifecycle import (
    BaseExecutableHook,
    DependenceOrder,
    ExecutableHook,
    HookCallbacks,
    HookContext,
    HookDependency,
    HookRequirement,
    HookResult,
    LifeCycleError,
    LifeState,
    create_adapter,
)


class TestBaseExecutableHook:
    def test_initial_state(self) -> None:
        hook = BaseExecutableHook("test")
        assert hook.name == "test"
        assert hook.state is LifeState.NEW
        assert hook.requirement == HookRequirement.OPTIONAL
        assert hook.dependencies == ()

    def test_process_init_success(self) -> None:
        class MyHook(BaseExecutableHook):
            def _do_init(self) -> HookResult:
                return HookResult.SUCCESS

        hook = MyHook("test")
        result = hook.process(HookContext.INIT)
        assert result is HookResult.SUCCESS
        assert hook.state is LifeState.RUNNING

    def test_process_init_already_running(self) -> None:
        hook = BaseExecutableHook("test")
        hook.process(HookContext.INIT)
        result = hook.process(HookContext.INIT)
        assert result is HookResult.SUCCESS
        assert hook.state is LifeState.RUNNING

    def test_process_init_invalid_state(self) -> None:
        hook = BaseExecutableHook("test")
        hook.process(HookContext.INIT)
        hook._state = LifeState.ERROR
        result = hook.process(HookContext.INIT)
        assert result is HookResult.FAILURE
        assert hook.state is LifeState.ERROR

    def test_process_quit_success(self) -> None:
        class MyHook(BaseExecutableHook):
            def _do_quit(self) -> HookResult:
                return HookResult.SUCCESS

        hook = MyHook("test")
        hook.process(HookContext.INIT)
        result = hook.process(HookContext.QUIT)
        assert result is HookResult.SUCCESS
        assert hook.state is LifeState.STOPPED

    def test_process_quit_already_stopped(self) -> None:
        hook = BaseExecutableHook("test")
        hook.process(HookContext.INIT)
        hook.process(HookContext.QUIT)
        result = hook.process(HookContext.QUIT)
        assert result is HookResult.SUCCESS
        assert hook.state is LifeState.STOPPED

    def test_process_quit_not_running(self) -> None:
        hook = BaseExecutableHook("test")
        result = hook.process(HookContext.QUIT)
        assert result is HookResult.FAILURE
        assert hook.state is LifeState.NEW

    def test_process_reset_success(self) -> None:
        class MyHook(BaseExecutableHook):
            def _do_reset(self) -> HookResult:
                return HookResult.SUCCESS

        hook = MyHook("test")
        hook.process(HookContext.INIT)
        result = hook.process(HookContext.RESET)
        assert result is HookResult.SUCCESS
        assert hook.state is LifeState.NEW

    def test_process_reset_already_new(self) -> None:
        hook = BaseExecutableHook("test")
        result = hook.process(HookContext.RESET)
        assert result is HookResult.SUCCESS
        assert hook.state is LifeState.NEW

    def test_process_reset_quit_fails(self) -> None:
        class BadQuitHook(BaseExecutableHook):
            def _do_quit(self) -> HookResult:
                return HookResult.FAILURE

            def _do_reset(self) -> HookResult:
                return HookResult.SUCCESS

        hook = BadQuitHook("test")
        hook.process(HookContext.INIT)
        result = hook.process(HookContext.RESET)
        assert result is HookResult.SUCCESS
        assert hook.state is LifeState.NEW

    def test_process_error(self) -> None:
        hook = BaseExecutableHook("test")
        hook.process(HookContext.INIT)
        hook._state = LifeState.RUNNING
        result = hook.process(HookContext.ERROR)
        assert result is HookResult.SUCCESS
        assert hook.state is LifeState.ERROR

    def test_do_init_exception_optional(self) -> None:
        class ExcHook(BaseExecutableHook):
            def _do_init(self) -> HookResult:
                raise ValueError("fail")

        hook = ExcHook("test")
        result = hook.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert hook.state is LifeState.ERROR

    def test_do_init_exception_required(self) -> None:
        class ExcRequiredHook(BaseExecutableHook):
            requirement = HookRequirement.REQUIRED

            def _do_init(self) -> HookResult:
                raise ValueError("fail")

        hook = ExcRequiredHook("test")
        result = hook.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert hook.state is LifeState.ERROR

    def test_do_quit_exception_optional(self) -> None:
        class ExcHook(BaseExecutableHook):
            def _do_quit(self) -> HookResult:
                raise ValueError("fail")

        hook = ExcHook("test")
        hook.process(HookContext.INIT)
        result = hook.process(HookContext.QUIT)
        assert result is HookResult.FATAL
        assert hook.state is LifeState.ERROR

    def test_do_quit_exception_required(self) -> None:
        class ExcRequiredHook(BaseExecutableHook):
            requirement = HookRequirement.REQUIRED

            def _do_quit(self) -> HookResult:
                raise ValueError("fail")

        hook = ExcRequiredHook("test")
        hook.process(HookContext.INIT)
        result = hook.process(HookContext.QUIT)
        assert result is HookResult.FATAL
        assert hook.state is LifeState.ERROR

    def test_do_reset_exception_optional(self) -> None:
        class ExcHook(BaseExecutableHook):
            def _do_reset(self) -> HookResult:
                raise ValueError("fail")

        hook = ExcHook("test")
        hook.process(HookContext.INIT)
        result = hook.process(HookContext.RESET)
        assert result is HookResult.FATAL
        assert hook.state is LifeState.ERROR

    def test_do_reset_exception_required(self) -> None:
        class ExcRequiredHook(BaseExecutableHook):
            requirement = HookRequirement.REQUIRED

            def _do_reset(self) -> HookResult:
                raise ValueError("fail")

        hook = ExcRequiredHook("test")
        hook.process(HookContext.INIT)
        result = hook.process(HookContext.RESET)
        assert result is HookResult.FATAL
        assert hook.state is LifeState.ERROR

    def test_do_error_exception(self) -> None:
        class ExcHook(BaseExecutableHook):
            def _do_error(self) -> HookResult:
                raise ValueError("fail")

        hook = ExcHook("test")
        hook._state = LifeState.RUNNING
        result = hook.process(HookContext.ERROR)
        assert result is HookResult.FATAL
        assert hook.state is LifeState.ERROR

    def test_lifecycle_error_in_do_init_optional(self) -> None:
        class ErrorHook(BaseExecutableHook):
            def _do_init(self) -> HookResult:
                raise LifeCycleError("test")

        hook = ErrorHook("test")
        result = hook.process(HookContext.INIT)
        assert result is HookResult.FAILURE
        assert hook.state is LifeState.NEW

    def test_lifecycle_error_in_do_init_required(self) -> None:
        class RequiredErrorHook(BaseExecutableHook):
            requirement = HookRequirement.REQUIRED

            def _do_init(self) -> HookResult:
                raise LifeCycleError("test")

        hook = RequiredErrorHook("test")
        result = hook.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert hook.state is LifeState.ERROR


class TestCreateAdapter:
    def test_adapter_with_callbacks(self) -> None:
        init_mock = MagicMock(return_value=HookResult.SUCCESS)
        quit_mock = MagicMock(return_value=HookResult.SUCCESS)
        callbacks = HookCallbacks(init=init_mock, quit=quit_mock)
        hook = create_adapter("adapter", callbacks)
        assert hook.name == "adapter"
        assert hook.requirement == HookRequirement.OPTIONAL
        assert hook.dependencies == ()
        hook.process(HookContext.INIT)
        init_mock.assert_called_once()
        hook.process(HookContext.QUIT)
        quit_mock.assert_called_once()

    def test_adapter_with_requirement(self) -> None:
        callbacks = HookCallbacks(init=lambda: HookResult.SUCCESS)
        hook = create_adapter("adapter", callbacks, requirement=HookRequirement.REQUIRED)
        assert hook.requirement == HookRequirement.REQUIRED

    def test_adapter_with_dependencies(self) -> None:
        dep = HookDependency("other", init_order=DependenceOrder.AFTER)
        callbacks = HookCallbacks(init=lambda: HookResult.SUCCESS)
        hook = create_adapter("adapter", callbacks, dependencies=[dep])
        assert hook.dependencies == (dep,)

    def test_adapter_default_methods(self) -> None:
        callbacks = HookCallbacks(init=lambda: HookResult.SUCCESS)
        hook = create_adapter("adapter", callbacks)
        assert hook.process(HookContext.INIT) is HookResult.SUCCESS
        assert hook.process(HookContext.QUIT) is HookResult.SUCCESS
        assert hook.process(HookContext.RESET) is HookResult.SUCCESS

    def test_adapter_protocol(self) -> None:
        callbacks = HookCallbacks(init=lambda: HookResult.SUCCESS)
        hook = create_adapter("adapter", callbacks)
        assert isinstance(hook, ExecutableHook)

    def test_create_adapter_with_requirement_and_deps(self) -> None:
        callbacks = HookCallbacks(init=lambda: HookResult.SUCCESS)
        dep = HookDependency("other")
        hook = create_adapter(
            "adap",
            callbacks,
            requirement=HookRequirement.REQUIRED,
            dependencies=[dep],
        )
        assert hook.requirement == HookRequirement.REQUIRED
        assert hook.dependencies == (dep,)
        assert hook.process(HookContext.INIT) is HookResult.SUCCESS

    def test_lifecycle_error_in_do_init_optional_hook(self) -> None:
        class ErrorHook(BaseExecutableHook):
            def _do_init(self) -> HookResult:
                raise LifeCycleError("err")

        hook = ErrorHook("err")
        result = hook.process(HookContext.INIT)
        assert result is HookResult.FAILURE
        assert hook.state is LifeState.NEW

    def test_lifecycle_error_in_do_init_required_hook(self) -> None:
        class RequiredErrorHook(BaseExecutableHook):
            requirement = HookRequirement.REQUIRED

            def _do_init(self) -> HookResult:
                raise LifeCycleError("err")

        hook = RequiredErrorHook("err")
        result = hook.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert hook.state is LifeState.ERROR
