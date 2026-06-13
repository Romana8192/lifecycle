import pytest

from lifecycle import (
    AllGroup,
    BaseExecutableHook,
    ExecutableHook,
    HookContext,
    HookRequirement,
    HookResult,
    LifeCycle,
    LifeCycleError,
    LifeState,
)


class SimpleHook(BaseExecutableHook):
    def __init__(self, name: str, init_ok: bool = True, quit_ok: bool = True) -> None:
        super().__init__(name)
        self.init_ok = init_ok
        self.quit_ok = quit_ok

    def _do_init(self) -> HookResult:
        return HookResult.SUCCESS if self.init_ok else HookResult.FAILURE

    def _do_quit(self) -> HookResult:
        return HookResult.SUCCESS if self.quit_ok else HookResult.FAILURE


class TestLifeCycle:
    def test_constructor_with_hooks(self) -> None:
        h = SimpleHook("test")
        lc = LifeCycle(hooks=[h])
        assert lc.state is LifeState.NEW
        assert len(lc) == 1
        assert lc.hooks[0] is h
        assert isinstance(lc.root_group, AllGroup)
        assert lc.root_group.name == "root"

    def test_constructor_with_group(self) -> None:
        group = AllGroup("custom", [])
        lc = LifeCycle(group=group)
        assert lc.root_group is group
        assert lc.state is LifeState.NEW

    def test_constructor_both_params_raises(self) -> None:
        group = AllGroup("g", [])
        h = SimpleHook("h")
        with pytest.raises(ValueError, match="Нельзя указать оба параметра"):
            LifeCycle(hooks=[h], group=group)

    def test_constructor_neither_param_raises(self) -> None:
        with pytest.raises(ValueError, match="Должен быть указан либо 'group', либо 'hooks'"):
            LifeCycle()

    def test_constructor_group_invalid_state(self) -> None:
        group = AllGroup("g", [])
        group.process(HookContext.INIT)
        with pytest.raises(ValueError, match="Состояние группы должно быть NEW или STOPPED"):
            LifeCycle(group=group)

    def test_add_hook_in_new_state(self, success_hook: ExecutableHook) -> None:
        lc = LifeCycle(hooks=[])
        assert lc.add_hook(success_hook) is True
        assert success_hook in lc

    def test_add_hook_in_running_state_fails(self, success_hook: ExecutableHook) -> None:
        lc = LifeCycle(hooks=[])
        lc.initialize()
        assert lc.add_hook(success_hook) is False
        assert success_hook not in lc

    def test_add_hook_in_stopped_state_succeeds(self, success_hook: ExecutableHook) -> None:
        lc = LifeCycle(hooks=[])
        lc.initialize()
        lc.finalize()
        assert lc.state is LifeState.STOPPED
        assert lc.add_hook(success_hook) is True

    def test_remove_hook_by_name(self, success_hook: ExecutableHook) -> None:
        lc = LifeCycle(hooks=[success_hook])
        assert lc.remove_hook("success") is True
        assert len(lc) == 0

    def test_remove_hook_by_object(self, success_hook: ExecutableHook) -> None:
        lc = LifeCycle(hooks=[success_hook])
        assert lc.remove_hook(success_hook) is True
        assert success_hook not in lc

    def test_remove_hook_not_found(self) -> None:
        lc = LifeCycle(hooks=[])
        assert lc.remove_hook("unknown") is False

    def test_remove_hook_in_running_state_fails(self, success_hook: ExecutableHook) -> None:
        lc = LifeCycle(hooks=[success_hook])
        lc.initialize()
        assert lc.remove_hook(success_hook) is False
        assert success_hook in lc

    def test_initialize_success(self) -> None:
        h = SimpleHook("test", init_ok=True)
        lc = LifeCycle(hooks=[h])
        assert lc.initialize() is True
        assert lc.state is LifeState.RUNNING

    def test_initialize_from_non_new_fails(self) -> None:
        lc = LifeCycle(hooks=[])
        lc.initialize()
        lc.finalize()
        assert lc.state is LifeState.STOPPED
        assert lc.initialize() is False

    def test_initialize_with_failure_still_running(self) -> None:
        h = SimpleHook("test", init_ok=False)
        lc = LifeCycle(hooks=[h])
        assert lc.initialize() is True
        assert lc.state is LifeState.RUNNING

    def test_initialize_with_exception_becomes_error(self) -> None:
        class BadHook(SimpleHook):
            def _do_init(self) -> HookResult:
                raise RuntimeError("crash")

        lc = LifeCycle(hooks=[BadHook("bad")])
        assert lc.initialize() is False
        assert lc.state is LifeState.ERROR

    def test_finalize_success(self) -> None:
        h = SimpleHook("test", quit_ok=True)
        lc = LifeCycle(hooks=[h])
        lc.initialize()
        assert lc.finalize() is True
        assert lc.state is LifeState.STOPPED

    def test_finalize_not_running_fails(self) -> None:
        lc = LifeCycle(hooks=[])
        assert lc.finalize() is False

    def test_finalize_with_failure_still_stopped(self) -> None:
        h = SimpleHook("test", quit_ok=False)
        lc = LifeCycle(hooks=[h])
        lc.initialize()
        assert lc.finalize() is True
        assert lc.state is LifeState.STOPPED

    def test_finalize_with_exception_becomes_error(self) -> None:
        class BadHook(SimpleHook):
            def _do_quit(self) -> HookResult:
                raise RuntimeError("crash")

        lc = LifeCycle(hooks=[BadHook("bad")])
        lc.initialize()
        assert lc.finalize() is False
        assert lc.state is LifeState.ERROR

    def test_reset_success(self) -> None:
        lc = LifeCycle(hooks=[])
        lc.initialize()
        assert lc.reset() is True
        assert lc.state is LifeState.RUNNING

    def test_reset_after_error(self) -> None:
        class BadHook(SimpleHook):
            def _do_init(self) -> HookResult:
                raise RuntimeError("crash")

        lc = LifeCycle(hooks=[BadHook("bad")])
        lc.initialize()
        assert lc.state is LifeState.ERROR
        h = SimpleHook("good", init_ok=True)
        lc = LifeCycle(hooks=[h])
        lc.initialize()
        lc._state = LifeState.ERROR
        lc._root_group._state = LifeState.ERROR
        result = lc.reset()
        assert result is True
        assert lc.state is LifeState.RUNNING

    def test_reset_with_failure_still_running(self) -> None:
        class ResetFailHook(SimpleHook):
            def _do_reset(self) -> HookResult:
                return HookResult.FAILURE

        lc = LifeCycle(hooks=[ResetFailHook("fail")])
        lc.initialize()
        assert lc.reset() is True
        assert lc.state is LifeState.RUNNING

    def test_reset_with_fatal_becomes_error(self) -> None:
        class ResetFatalHook(SimpleHook):
            requirement = HookRequirement.REQUIRED

            def _do_reset(self) -> HookResult:
                return HookResult.FATAL

        lc = LifeCycle(hooks=[ResetFatalHook("fatal")])
        lc.initialize()
        assert lc.reset() is False
        assert lc.state is LifeState.ERROR

    def test_state_property(self) -> None:
        lc = LifeCycle(hooks=[])
        assert lc.state is LifeState.NEW
        lc.initialize()
        assert lc.state is LifeState.RUNNING

    def test_hooks_property(self) -> None:
        h = SimpleHook("test")
        lc = LifeCycle(hooks=[h])
        hooks = lc.hooks
        assert len(hooks) == 1
        assert hooks[0] is h
        hooks.append(SimpleHook("extra"))
        assert len(lc.hooks) == 1

    def test_contains(self) -> None:
        h = SimpleHook("test")
        lc = LifeCycle(hooks=[h])
        assert h in lc
        assert SimpleHook("other") not in lc

    def test_len(self) -> None:
        lc = LifeCycle(hooks=[SimpleHook("a"), SimpleHook("b")])
        assert len(lc) == 2

    def test_initialize_with_fatal_returns_false(self) -> None:
        class FatalInitHook(SimpleHook):
            def _do_init(self) -> HookResult:
                return HookResult.FATAL

        lc = LifeCycle(hooks=[FatalInitHook("fatal")])
        assert lc.initialize() is False
        assert lc.state is LifeState.ERROR

    def test_finalize_with_fatal_returns_false(self) -> None:
        class FatalQuitHook(SimpleHook):
            def _do_quit(self) -> HookResult:
                return HookResult.FATAL

        lc = LifeCycle(hooks=[FatalQuitHook("fatal")])
        lc.initialize()
        assert lc.finalize() is False
        assert lc.state is LifeState.ERROR

    def test_reset_with_failure_returns_true(self) -> None:
        class ResetFailHook(SimpleHook):
            def _do_reset(self) -> HookResult:
                return HookResult.FAILURE

        lc = LifeCycle(hooks=[ResetFailHook("fail")])
        lc.initialize()
        assert lc.reset() is True
        assert lc.state is LifeState.RUNNING

    def test_initialize_when_already_running_returns_true(self) -> None:
        lc = LifeCycle(hooks=[])
        lc.initialize()
        assert lc.initialize() is True
        assert lc.state is LifeState.RUNNING

    def test_finalize_when_already_stopped_returns_true(self) -> None:
        lc = LifeCycle(hooks=[])
        lc.initialize()
        lc.finalize()
        assert lc.finalize() is True
        assert lc.state is LifeState.STOPPED

    def test_reset_when_already_new_returns_true(self) -> None:
        lc = LifeCycle(hooks=[])
        assert lc.reset() is True
        assert lc.state is LifeState.NEW

    def test_remove_hook_by_name_not_found_returns_false(self) -> None:
        lc = LifeCycle(hooks=[])
        assert lc.remove_hook("nonexistent") is False

    def test_remove_hook_by_object_not_found_returns_false(self) -> None:
        lc = LifeCycle(hooks=[])
        h = SimpleHook("test")
        assert lc.remove_hook(h) is False

    def test_order_cache_invalidation(self) -> None:
        h1 = SimpleHook("A")
        h2 = SimpleHook("B")
        lc = LifeCycle(hooks=[h1, h2])
        root = lc.root_group
        order1 = root._get_ordered_hooks(HookContext.INIT)
        assert len(order1) == 2
        h3 = SimpleHook("C")
        lc.add_hook(h3)
        order2 = root._get_ordered_hooks(HookContext.INIT)
        assert len(order2) == 3
        assert h3 in order2
        lc.remove_hook("C")
        order3 = root._get_ordered_hooks(HookContext.INIT)
        assert len(order3) == 2
        assert h3 not in order3

    def test_lifecycle_error_in_optional_hook_returns_failure_not_fatal(self) -> None:
        class ErrorHook(BaseExecutableHook):
            def _do_init(self) -> HookResult:
                raise LifeCycleError("test")

        lc = LifeCycle(hooks=[ErrorHook("opt")])
        assert lc.initialize() is True
        assert lc.state is LifeState.RUNNING

    def test_lifecycle_error_in_required_hook_returns_fatal(self) -> None:
        class RequiredErrorHook(BaseExecutableHook):
            requirement = HookRequirement.REQUIRED

            def _do_init(self) -> HookResult:
                raise LifeCycleError("test")

        lc = LifeCycle(hooks=[RequiredErrorHook("req")])
        assert lc.initialize() is False
        assert lc.state is LifeState.ERROR
