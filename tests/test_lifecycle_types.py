import pytest

from lifecycle import (
    DependenceOrder,
    HookCallbacks,
    HookContext,
    HookDependency,
    HookRequirement,
    HookResult,
    LifeState,
    SelectionMode,
)


def test_life_state_enum() -> None:
    assert LifeState.NEW.name == "NEW"
    assert LifeState.INITIALIZING.name == "INITIALIZING"
    assert LifeState.RUNNING.name == "RUNNING"
    assert LifeState.STOPPING.name == "STOPPING"
    assert LifeState.STOPPED.name == "STOPPED"
    assert LifeState.ERROR.name == "ERROR"
    assert LifeState.RESETTING.name == "RESETTING"


def test_hook_requirement_enum() -> None:
    assert HookRequirement.OPTIONAL.name == "OPTIONAL"
    assert HookRequirement.REQUIRED.name == "REQUIRED"


def test_hook_context_enum() -> None:
    assert HookContext.INIT.name == "INIT"
    assert HookContext.QUIT.name == "QUIT"
    assert HookContext.ERROR.name == "ERROR"
    assert HookContext.RESET.name == "RESET"


def test_selection_mode_enum() -> None:
    assert SelectionMode.ALL.name == "ALL"
    assert SelectionMode.ONE.name == "ONE"


def test_hook_result_enum() -> None:
    assert HookResult.SUCCESS.name == "SUCCESS"
    assert HookResult.FATAL.name == "FATAL"
    assert HookResult.FAILURE.name == "FAILURE"


def test_dependence_order_enum() -> None:
    assert DependenceOrder.UNORDERED.name == "UNORDERED"
    assert DependenceOrder.BEFORE.name == "BEFORE"
    assert DependenceOrder.AFTER.name == "AFTER"


class TestHookDependency:
    def test_constructor_default(self) -> None:
        dep = HookDependency("test")
        assert dep.name == "test"
        assert dep.get_order(HookContext.INIT) is DependenceOrder.UNORDERED
        assert dep.get_order(HookContext.QUIT) is DependenceOrder.UNORDERED
        assert dep.get_order(HookContext.RESET) is DependenceOrder.UNORDERED
        assert dep.get_order(HookContext.ERROR) is DependenceOrder.UNORDERED

    def test_constructor_custom(self) -> None:
        dep = HookDependency(
            "test",
            init_order=DependenceOrder.BEFORE,
            quit_order=DependenceOrder.AFTER,
            reset_order=DependenceOrder.BEFORE,
            error_order=DependenceOrder.AFTER,
        )
        assert dep.get_order(HookContext.INIT) is DependenceOrder.BEFORE
        assert dep.get_order(HookContext.QUIT) is DependenceOrder.AFTER
        assert dep.get_order(HookContext.RESET) is DependenceOrder.BEFORE
        assert dep.get_order(HookContext.ERROR) is DependenceOrder.AFTER

    def test_hook_dependency_get_order_all_contexts(self) -> None:
        dep = HookDependency(
            "test",
            init_order=DependenceOrder.BEFORE,
            quit_order=DependenceOrder.AFTER,
            reset_order=DependenceOrder.UNORDERED,
            error_order=DependenceOrder.BEFORE,
        )
        assert dep.get_order(HookContext.INIT) is DependenceOrder.BEFORE
        assert dep.get_order(HookContext.QUIT) is DependenceOrder.AFTER
        assert dep.get_order(HookContext.RESET) is DependenceOrder.UNORDERED
        assert dep.get_order(HookContext.ERROR) is DependenceOrder.BEFORE


class TestHookCallbacks:
    def test_constructor_at_least_one_callback(self) -> None:
        with pytest.raises(ValueError, match="Должен быть задан хотя бы один колбэк"):
            HookCallbacks()

    def test_constructor_init_only(self) -> None:
        def cb() -> HookResult:
            return HookResult.SUCCESS

        hc = HookCallbacks(init=cb)
        assert hc.init is cb
        assert hc.quit is None
        assert hc.error is None
        assert hc.reset is None
        assert repr(hc) == "HookCallbacks(init)"

    def test_constructor_multiple(self) -> None:
        def cb1() -> HookResult:
            return HookResult.SUCCESS

        def cb2() -> HookResult:
            return HookResult.FAILURE

        hc = HookCallbacks(init=cb1, quit=cb2)
        assert hc.init is cb1
        assert hc.quit is cb2
        assert repr(hc) == "HookCallbacks(init, quit)"
