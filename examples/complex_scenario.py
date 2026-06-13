"""Сложный сценарий: несколько групп, вложенность, разные требования."""

import logging
import sys

from lifecycle import (
    AllGroup,
    BaseExecutableHook,
    HookRequirement,
    HookResult,
    LifeCycle,
    OneGroup,
    SelectionMode,
    create_group,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")


class PrintHook(BaseExecutableHook):
    """Хук, просто печатающий своё имя и контекст."""

    def __init__(self, name: str, success: bool = True) -> None:
        super().__init__(name)
        self.success = success

    def _do_init(self) -> HookResult:
        print(f"  {self.name}: INIT -> {'SUCCESS' if self.success else 'FAILURE'}")
        return HookResult.SUCCESS if self.success else HookResult.FAILURE

    def _do_quit(self) -> HookResult:
        print(f"  {self.name}: QUIT")
        return HookResult.SUCCESS


def main() -> None:
    group_all = AllGroup(
        "all_sub",
        [
            PrintHook("A1"),
            PrintHook("A2"),
        ],
    )

    group_one = OneGroup(
        "one_sub",
        [
            PrintHook("B1", success=False),
            PrintHook("B2", success=True),
        ],
    )

    root_group = create_group(
        SelectionMode.ALL,
        "root",
        [group_all, group_one],
        requirement=HookRequirement.REQUIRED,
    )

    lc = LifeCycle(group=root_group)

    print("=== Инициализация ===")
    lc.initialize()

    print("\n=== Завершение ===")
    lc.finalize()


if __name__ == "__main__":
    sys.exit(main())
