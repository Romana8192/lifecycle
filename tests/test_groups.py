import pytest

from lifecycle import (
    AllGroup,
    BaseExecutableHook,
    BaseGroup,
    CircularDependencyError,
    DependenceOrder,
    ExecutableHook,
    HookContext,
    HookDependency,
    HookExistsError,
    HookNameExistsError,
    HookRequirement,
    HookResult,
    InvalidStateError,
    LifeCycleError,
    LifeState,
    LifeStateError,
    OneGroup,
    SelectionMode,
    create_group,
)


class SimpleHook(BaseExecutableHook):
    def __init__(
        self,
        name: str,
        init_result: HookResult = HookResult.SUCCESS,
        quit_result: HookResult = HookResult.SUCCESS,
        reset_result: HookResult = HookResult.SUCCESS,
        error_result: HookResult = HookResult.SUCCESS,
    ) -> None:
        super().__init__(name)
        self.init_result = init_result
        self.quit_result = quit_result
        self.reset_result = reset_result
        self.error_result = error_result

    def _do_init(self) -> HookResult:
        return self.init_result

    def _do_quit(self) -> HookResult:
        return self.quit_result

    def _do_reset(self) -> HookResult:
        return self.reset_result

    def _do_error(self) -> HookResult:
        return self.error_result


class RequiredSimpleHook(SimpleHook):
    requirement = HookRequirement.REQUIRED


class FatalSimpleHook(SimpleHook):
    def _do_init(self) -> HookResult:
        return HookResult.FATAL

    def _do_quit(self) -> HookResult:
        return HookResult.FATAL

    def _do_reset(self) -> HookResult:
        return HookResult.FATAL

    def _do_error(self) -> HookResult:
        return HookResult.FATAL


class TestBaseGroup:
    def test_constructor(self) -> None:
        group = BaseGroup("test")
        assert group.name == "test"
        assert group.state is LifeState.NEW
        assert len(group) == 0
        assert group.hooks == []

    def test_extend_adds_hooks(self, success_hook: ExecutableHook) -> None:
        group = BaseGroup("test")
        group.extend(success_hook)
        assert len(group) == 1
        assert success_hook in group
        assert group.hooks[0] is success_hook

    def test_extend_duplicate_name_raises(self, success_hook: ExecutableHook) -> None:
        group = BaseGroup("test")
        group.extend(success_hook)
        duplicate = SimpleHook("success")
        with pytest.raises(HookNameExistsError):
            group.extend(duplicate)

    def test_extend_duplicate_object_raises(self, success_hook: ExecutableHook) -> None:
        group = BaseGroup("test")
        group.extend(success_hook)
        with pytest.raises(HookExistsError):
            group.extend(success_hook)

    def test_extend_invalid_state(self, success_hook: ExecutableHook) -> None:
        group = BaseGroup("test")
        group.process(HookContext.INIT)
        with pytest.raises(LifeStateError):
            group.extend(success_hook)

    def test_remove_by_name(self, success_hook: ExecutableHook) -> None:
        group = BaseGroup("test")
        group.extend(success_hook)
        group.remove("success")
        assert len(group) == 0

    def test_remove_by_object(self, success_hook: ExecutableHook) -> None:
        group = BaseGroup("test")
        group.extend(success_hook)
        group.remove(success_hook)
        assert len(group) == 0

    def test_remove_not_found(self) -> None:
        group = BaseGroup("test")
        with pytest.raises(ValueError, match="не найден"):
            group.remove("unknown")

    def test_remove_invalid_state(self, success_hook: ExecutableHook) -> None:
        group = BaseGroup("test")
        group.extend(success_hook)
        group.process(HookContext.INIT)
        with pytest.raises(LifeStateError):
            group.remove(success_hook)

    def test_contains(self, success_hook: ExecutableHook) -> None:
        group = BaseGroup("test")
        assert success_hook not in group
        group.extend(success_hook)
        assert success_hook in group

    def test_len(self, success_hook: ExecutableHook, fail_hook: ExecutableHook) -> None:
        group = BaseGroup("test")
        group.extend(success_hook, fail_hook)
        assert len(group) == 2

    def test_state_property(self) -> None:
        group = BaseGroup("test")
        assert group.state is LifeState.NEW
        group.process(HookContext.INIT)
        assert group.state is LifeState.RUNNING

    def test_process_init_all_success(self) -> None:
        h1 = SimpleHook("A")
        h2 = SimpleHook("B")
        group = BaseGroup("test", [h1, h2])
        result = group.process(HookContext.INIT)
        assert result is HookResult.SUCCESS
        assert group.state is LifeState.RUNNING

    def test_process_init_with_failure(self) -> None:
        h1 = SimpleHook("A", init_result=HookResult.SUCCESS)
        h2 = SimpleHook("B", init_result=HookResult.FAILURE)
        group = BaseGroup("test", [h1, h2])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FAILURE
        assert group.state is LifeState.RUNNING

    def test_process_init_with_fatal(self) -> None:
        h1 = SimpleHook("A", init_result=HookResult.SUCCESS)
        h2 = FatalSimpleHook("B")
        group = BaseGroup("test", [h1, h2])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR

    def test_process_quit_success(self) -> None:
        h1 = SimpleHook("A")
        h2 = SimpleHook("B")
        group = BaseGroup("test", [h1, h2])
        group.process(HookContext.INIT)
        result = group.process(HookContext.QUIT)
        assert result is HookResult.SUCCESS
        assert group.state is LifeState.STOPPED

    def test_process_quit_failure(self) -> None:
        h1 = SimpleHook("A", quit_result=HookResult.FAILURE)
        group = BaseGroup("test", [h1])
        group.process(HookContext.INIT)
        result = group.process(HookContext.QUIT)
        assert result is HookResult.FAILURE
        assert group.state is LifeState.STOPPED

    def test_process_quit_fatal(self) -> None:
        h1 = FatalSimpleHook("A")
        group = BaseGroup("test", [h1])
        group.process(HookContext.INIT)
        with pytest.raises(InvalidStateError):
            group.process(HookContext.QUIT)

    def test_process_reset_success(self) -> None:
        h1 = SimpleHook("A")
        group = BaseGroup("test", [h1])
        group.process(HookContext.INIT)
        result = group.process(HookContext.RESET)
        assert result is HookResult.SUCCESS
        assert group.state is LifeState.RUNNING

    def test_process_error(self) -> None:
        h1 = SimpleHook("A", error_result=HookResult.SUCCESS)
        group = BaseGroup("test", [h1])
        group.process(HookContext.INIT)
        group._state = LifeState.RUNNING
        result = group.process(HookContext.ERROR)
        assert result is HookResult.SUCCESS
        assert group.state is LifeState.ERROR

    def test_process_error_failure(self) -> None:
        h1 = SimpleHook("A", error_result=HookResult.FAILURE)
        group = BaseGroup("test", [h1])
        group.process(HookContext.INIT)
        group._state = LifeState.RUNNING
        result = group.process(HookContext.ERROR)
        assert result is HookResult.FAILURE
        assert group.state is LifeState.ERROR

    def test_process_error_fatal(self) -> None:
        class FatalOnErrorHook(SimpleHook):
            def _do_error(self) -> HookResult:
                return HookResult.FATAL

        h1 = FatalOnErrorHook("A", init_result=HookResult.SUCCESS)
        group = BaseGroup("test", [h1])
        group.process(HookContext.INIT)
        result = group.process(HookContext.ERROR)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR

    def test_process_init_invalid_state(self) -> None:
        group = BaseGroup("test")
        group.process(HookContext.INIT)
        with pytest.raises(InvalidStateError):
            group.process(HookContext.INIT)

    def test_process_quit_invalid_state(self) -> None:
        group = BaseGroup("test")
        with pytest.raises(InvalidStateError):
            group.process(HookContext.QUIT)

    def test_process_error_invalid_state(self) -> None:
        group = BaseGroup("test")
        with pytest.raises(InvalidStateError):
            group.process(HookContext.ERROR)

    def test_init_fatal_with_rollback(self) -> None:
        class RollbackHook(SimpleHook):
            def _do_quit(self) -> HookResult:
                self.quit_called = True
                return HookResult.SUCCESS

        h1 = RollbackHook("A", init_result=HookResult.SUCCESS)
        h2 = FatalSimpleHook("B")
        group = BaseGroup("test", [h1, h2])
        h1.quit_called = False
        result = group.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR
        assert h1.quit_called is True

    def test_group_do_init_raises_exception(self) -> None:
        class BadGroup(BaseGroup):
            def _do_init(self) -> HookResult:
                raise RuntimeError("group crash")

        group = BadGroup("bad")
        result = group.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR

    def test_lifecycle_error_in_hook_optional(self) -> None:
        class ErrorHook(SimpleHook):
            def _do_init(self) -> HookResult:
                raise LifeCycleError("test error")

        group = BaseGroup("test", [ErrorHook("err")])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FAILURE
        assert group.state is LifeState.RUNNING

    def test_lifecycle_error_in_hook_required(self) -> None:
        class RequiredErrorHook(RequiredSimpleHook):
            def _do_init(self) -> HookResult:
                raise LifeCycleError("fatal error")

        group = BaseGroup("test", [RequiredErrorHook("err")])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR


class TestAllGroup:
    def test_all_group_is_base_group(self, success_hook: ExecutableHook) -> None:
        group = AllGroup("all", [success_hook])
        assert isinstance(group, BaseGroup)
        assert group.name == "all"
        assert len(group) == 1


class TestOneGroup:
    def test_constructor(self) -> None:
        group = OneGroup("one")
        assert group.name == "one"
        assert group.state is LifeState.NEW
        assert len(group) == 0

    def test_validation_no_multiple_required(self) -> None:
        h1 = RequiredSimpleHook("A")
        h2 = RequiredSimpleHook("B")
        group = OneGroup("one", [h1, h2])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR

    def test_validation_no_internal_dependencies(self) -> None:
        class DepHook(SimpleHook):
            dependencies = (HookDependency("A"),)

        h1 = SimpleHook("A")
        h2 = DepHook("B")
        group = OneGroup("one", [h1, h2])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR

    def test_activation_successful_optional(self) -> None:
        h1 = SimpleHook("A", init_result=HookResult.FAILURE)
        h2 = SimpleHook("B", init_result=HookResult.SUCCESS)
        group = OneGroup("one", [h1, h2])
        result = group.process(HookContext.INIT)
        assert result is HookResult.SUCCESS
        assert group.state is LifeState.RUNNING

    def test_activation_required_preferred(self) -> None:
        h1 = RequiredSimpleHook("A")
        h2 = SimpleHook("B")
        group = OneGroup("one", [h1, h2])
        result = group.process(HookContext.INIT)
        assert result is HookResult.SUCCESS

    def test_activation_failure_then_success(self) -> None:
        h1 = SimpleHook("A", init_result=HookResult.FAILURE)
        h2 = SimpleHook("B", init_result=HookResult.SUCCESS)
        group = OneGroup("one", [h1, h2])
        result = group.process(HookContext.INIT)
        assert result is HookResult.SUCCESS

    def test_all_fail(self) -> None:
        h1 = SimpleHook("A", init_result=HookResult.FAILURE)
        h2 = SimpleHook("B", init_result=HookResult.FAILURE)
        group = OneGroup("one", [h1, h2])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR

    def test_fatal_during_init(self) -> None:
        h1 = FatalSimpleHook("A")
        h2 = SimpleHook("B")
        group = OneGroup("one", [h1, h2])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR

    def test_quit_no_active(self) -> None:
        h1 = SimpleHook("A")
        group = OneGroup("one", [h1])
        group.process(HookContext.INIT)
        result = group.process(HookContext.QUIT)
        assert result is HookResult.SUCCESS
        assert group.state is LifeState.STOPPED

    def test_error_handling(self) -> None:
        h1 = SimpleHook("A", error_result=HookResult.SUCCESS)
        group = OneGroup("one", [h1])
        group.process(HookContext.INIT)
        group._state = LifeState.RUNNING
        result = group.process(HookContext.ERROR)
        assert result is HookResult.SUCCESS
        assert group.state is LifeState.ERROR

    def test_error_fatal(self) -> None:
        h1 = FatalSimpleHook("A")
        group = OneGroup("one", [h1])
        group.process(HookContext.INIT)
        group._state = LifeState.RUNNING
        result = group.process(HookContext.ERROR)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR

    def test_all_candidates_fail_raises_exception(self) -> None:
        h1 = SimpleHook("A", init_result=HookResult.FAILURE)
        h2 = SimpleHook("B", init_result=HookResult.FAILURE)
        group = OneGroup("one", [h1, h2])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR

    def test_reset_with_active_optional_success(self) -> None:
        class ResetTracker(SimpleHook):
            def _do_quit(self) -> HookResult:
                self.quit_called = True
                return HookResult.SUCCESS

            def _do_reset(self) -> HookResult:
                return HookResult.SUCCESS

        opt = ResetTracker("opt", init_result=HookResult.SUCCESS)
        alt = SimpleHook("alt", init_result=HookResult.SUCCESS)
        group = OneGroup("one", [opt, alt])
        group.process(HookContext.INIT)
        assert group._active_hook is opt
        opt.quit_called = False
        result = group.process(HookContext.RESET)
        assert result is HookResult.SUCCESS
        assert opt.quit_called is True
        assert group._active_hook is not None

    def test_reset_with_required_that_fails_on_quit(self) -> None:
        class FatalOnQuitHook(RequiredSimpleHook):
            def _do_quit(self) -> HookResult:
                return HookResult.FATAL

            def _do_init(self) -> HookResult:
                return HookResult.SUCCESS

        h = FatalOnQuitHook("fatal")
        group = OneGroup("one", [h])
        group.process(HookContext.INIT)
        result = group.process(HookContext.RESET)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR


class TestCreateGroup:
    def test_create_all_group(self) -> None:
        h = SimpleHook("A")
        group = create_group(SelectionMode.ALL, "mygroup", [h])
        assert isinstance(group, AllGroup)
        assert group.name == "mygroup"
        assert len(group) == 1

    def test_create_one_group(self) -> None:
        h = SimpleHook("A")
        group = create_group(SelectionMode.ONE, "mygroup", [h])
        assert isinstance(group, OneGroup)
        assert group.name == "mygroup"
        assert len(group) == 1

    def test_create_with_requirement_and_deps(self) -> None:
        h = SimpleHook("A")
        dep = HookDependency("B")
        group = create_group(
            SelectionMode.ALL,
            "mygroup",
            [h],
            requirement=HookRequirement.REQUIRED,
            dependencies=[dep],
        )
        assert group.requirement == HookRequirement.REQUIRED
        assert group.dependencies == (dep,)


class TestBaseGroupAdvanced:
    def test_circular_dependency_raises(self) -> None:
        class HookA(BaseExecutableHook):
            dependencies = (HookDependency("B", init_order=DependenceOrder.AFTER),)

        class HookB(BaseExecutableHook):
            dependencies = (HookDependency("A", init_order=DependenceOrder.AFTER),)

        group = BaseGroup("circ", [HookA("A"), HookB("B")])
        with pytest.raises(CircularDependencyError):
            group.process(HookContext.INIT)

    def test_rollback_calls_quit_on_successful_hooks_only(self) -> None:
        order = []

        class TraceHook(BaseExecutableHook):
            def __init__(self, name: str, fail_init: bool = False):
                super().__init__(name)
                self.fail_init = fail_init

            def _do_init(self) -> HookResult:
                order.append(f"init_{self.name}")
                return HookResult.FATAL if self.fail_init else HookResult.SUCCESS

            def _do_quit(self) -> HookResult:
                order.append(f"quit_{self.name}")
                return HookResult.SUCCESS

        a = TraceHook("A")
        b = TraceHook("B", fail_init=True)
        group = BaseGroup("test", [a, b])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR
        assert order == ["init_A", "init_B", "quit_A"]

    def test_lifecycle_error_in_optional_hook_group(self) -> None:
        class ErrorHook(SimpleHook):
            def _do_init(self) -> HookResult:
                raise LifeCycleError("error")

        group = BaseGroup("test", [ErrorHook("err")])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FAILURE
        assert group.state is LifeState.RUNNING

    def test_lifecycle_error_in_required_hook_group(self) -> None:
        class RequiredErrorHook(RequiredSimpleHook):
            def _do_init(self) -> HookResult:
                raise LifeCycleError("error")

        group = BaseGroup("test", [RequiredErrorHook("err")])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR


class TestOneGroupAdvanced:
    def test_required_failure_leads_to_error(self) -> None:
        class RequiredFails(RequiredSimpleHook):
            def _do_init(self) -> HookResult:
                return HookResult.FAILURE

        group = OneGroup("one", [RequiredFails("req")])
        result = group.process(HookContext.INIT)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR

    def test_reset_with_fatal_on_quit_of_optional_returns_fatal(self) -> None:
        class FatalOnQuitHook(SimpleHook):
            def _do_quit(self) -> HookResult:
                return HookResult.FATAL

        opt = FatalOnQuitHook("opt", init_result=HookResult.SUCCESS)
        group = OneGroup("one", [opt])
        group.process(HookContext.INIT)
        result = group.process(HookContext.RESET)
        assert result is HookResult.FATAL
        assert group.state is LifeState.ERROR
