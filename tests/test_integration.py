from lifecycle import (
    BaseExecutableHook,
    DependenceOrder,
    HookCallbacks,
    HookDependency,
    HookRequirement,
    HookResult,
    LifeCycle,
    LifeState,
    OneGroup,
    create_adapter,
)


class DatabaseHook(BaseExecutableHook):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.connected = False

    def _do_init(self) -> HookResult:
        self.connected = True
        return HookResult.SUCCESS

    def _do_quit(self) -> HookResult:
        self.connected = False
        return HookResult.SUCCESS


class ServiceHook(BaseExecutableHook):
    def __init__(self, name: str, db_hook_name: str) -> None:
        super().__init__(name)
        self.db_hook_name = db_hook_name
        self.started = False

    @property
    def dependencies(self) -> tuple[HookDependency, ...]:
        return (HookDependency(self.db_hook_name, init_order=DependenceOrder.AFTER),)

    def _do_init(self) -> HookResult:
        self.started = True
        return HookResult.SUCCESS

    def _do_quit(self) -> HookResult:
        self.started = False
        return HookResult.SUCCESS


def test_complex_lifecycle_with_dependencies() -> None:
    db = DatabaseHook("db")
    service = ServiceHook("service", "db")
    lc = LifeCycle(hooks=[db, service])
    assert lc.initialize() is True
    assert db.connected is True
    assert service.started is True
    assert lc.finalize() is True
    assert db.connected is False
    assert service.started is False


def test_one_group_fallback() -> None:
    class PrimaryHook(BaseExecutableHook):
        def _do_init(self) -> HookResult:
            return HookResult.FAILURE

        def _do_quit(self) -> HookResult:
            return HookResult.SUCCESS

    class BackupHook(BaseExecutableHook):
        def _do_init(self) -> HookResult:
            return HookResult.SUCCESS

        def _do_quit(self) -> HookResult:
            return HookResult.SUCCESS

    group = OneGroup("fallback", [PrimaryHook("primary"), BackupHook("backup")])
    lc = LifeCycle(group=group)
    assert lc.initialize() is True


def test_adapter_integration() -> None:
    init_called = False
    quit_called = False

    def on_init() -> HookResult:
        nonlocal init_called
        init_called = True
        return HookResult.SUCCESS

    def on_quit() -> HookResult:
        nonlocal quit_called
        quit_called = True
        return HookResult.SUCCESS

    callbacks = HookCallbacks(init=on_init, quit=on_quit)
    hook = create_adapter("adapter", callbacks, requirement=HookRequirement.REQUIRED)
    lc = LifeCycle(hooks=[hook])
    assert lc.initialize() is True
    assert init_called
    assert lc.finalize() is True
    assert quit_called


def test_reset_with_rollback() -> None:
    class CounterHook(BaseExecutableHook):
        def __init__(self, name: str) -> None:
            super().__init__(name)
            self.init_count = 0
            self.quit_count = 0
            self.reset_count = 0

        def _do_init(self) -> HookResult:
            self.init_count += 1
            return HookResult.SUCCESS

        def _do_quit(self) -> HookResult:
            self.quit_count += 1
            return HookResult.SUCCESS

        def _do_reset(self) -> HookResult:
            self.reset_count += 1
            return HookResult.SUCCESS

    hook = CounterHook("counter")
    lc = LifeCycle(hooks=[hook])
    lc.initialize()
    assert hook.init_count == 1
    lc.reset()
    assert hook.reset_count == 1
    lc.finalize()
    assert hook.quit_count == 1


def test_error_handling_in_group() -> None:
    class FailInitHook(BaseExecutableHook):
        def _do_init(self) -> HookResult:
            raise RuntimeError("init failed")

    hook = FailInitHook("fail")
    lc = LifeCycle(hooks=[hook])
    assert lc.initialize() is False
    assert lc.state is LifeState.ERROR
    assert lc.finalize() is False
    assert lc.reset() is True
    assert lc.state is LifeState.RUNNING
