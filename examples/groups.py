"""Пример использования групп (AllGroup, OneGroup) без LifeCycle."""

import logging
import sys

from lifecycle import (
    AllGroup,
    BaseExecutableHook,
    HookContext,
    HookRequirement,
    HookResult,
    OneGroup,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")


class TestHook(BaseExecutableHook):
    """Хук, который может возвращать SUCCESS или FAILURE в зависимости от аргумента."""

    def __init__(self, name: str, success: bool = True) -> None:
        super().__init__(name)
        self.success = success

    def _do_init(self) -> HookResult:
        print(f"{self.name}: init -> {'SUCCESS' if self.success else 'FAILURE'}")
        return HookResult.SUCCESS if self.success else HookResult.FAILURE

    def _do_quit(self) -> HookResult:
        print(f"{self.name}: quit -> SUCCESS")
        return HookResult.SUCCESS


def demo_all_group() -> None:
    """AllGroup выполняет все хуки."""
    print("\n=== AllGroup ===")
    group = AllGroup(
        "all_group",
        [
            TestHook("A", success=True),
            TestHook("B", success=False),
            TestHook("C", success=True),
        ],
    )
    result = group.process(HookContext.INIT)
    print(f"Результат группы: {result.name} (ожидается FAILURE, т.к. B упал)")


def demo_one_group() -> None:
    """OneGroup выполняет первый успешный хук."""
    print("\n=== OneGroup ===")
    group = OneGroup(
        "one_group",
        [
            TestHook("X", success=False),
            TestHook("Y", success=True),
            TestHook("Z", success=True),
        ],
    )
    result = group.process(HookContext.INIT)
    print(f"Результат группы: {result.name} (активен Y)")

    print("\n--- Остановка и повторный INIT ---")
    group.process(HookContext.QUIT)
    result2 = group.process(HookContext.INIT)
    print(f"Результат повторного INIT: {result2.name} (активен остаётся Y)")


def demo_required_in_one_group() -> None:
    """OneGroup с обязательным (REQUIRED) хуком."""
    print("\n=== OneGroup с REQUIRED ===")

    class RequiredHook(TestHook):
        requirement = HookRequirement.REQUIRED

    group = OneGroup(
        "required_group",
        [
            RequiredHook("Must", success=True),
            TestHook("Opt1", success=False),
        ],
    )
    result = group.process(HookContext.INIT)
    print(f"Результат: {result.name} (активен Must)")


def main() -> None:
    demo_all_group()
    demo_one_group()
    demo_required_in_one_group()


if __name__ == "__main__":
    sys.exit(main())
