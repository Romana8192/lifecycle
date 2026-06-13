"""Пример использования зависимостей (BEFORE / AFTER) для разных контекстов."""

import logging
import sys
from typing import ClassVar

from lifecycle import (
    BaseExecutableHook,
    DependenceOrder,
    HookDependency,
    HookResult,
    LifeCycle,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")


class LoggerHook(BaseExecutableHook):
    """Хук, который просто логирует своё выполнение."""

    def __init__(self, name: str, message: str) -> None:
        super().__init__(name)
        self.message = message

    def _do_init(self) -> HookResult:
        print(f"[{self.name}] {self.message} (INIT)")
        return HookResult.SUCCESS

    def _do_quit(self) -> HookResult:
        print(f"[{self.name}] {self.message} (QUIT)")
        return HookResult.SUCCESS


def main() -> None:
    dep_a_on_b = HookDependency(
        name="B",
        init_order=DependenceOrder.BEFORE,
        quit_order=DependenceOrder.AFTER,
    )

    dep_b_on_a = HookDependency(
        name="A",
        init_order=DependenceOrder.AFTER,
        quit_order=DependenceOrder.BEFORE,
    )

    class HookA(LoggerHook):
        dependencies: ClassVar[tuple[HookDependency, ...]] = (dep_a_on_b,)

    class HookB(LoggerHook):
        dependencies: ClassVar[tuple[HookDependency, ...]] = (dep_b_on_a,)

    hook_a = HookA("A", "Выполняется A")
    hook_b = HookB("B", "Выполняется B")

    lc = LifeCycle(hooks=[hook_a, hook_b])

    print("--- Инициализация (ожидаемый порядок: A, B) ---")
    lc.initialize()

    print("\n--- Завершение (ожидаемый порядок: B, A) ---")
    lc.finalize()


if __name__ == "__main__":
    sys.exit(main())
