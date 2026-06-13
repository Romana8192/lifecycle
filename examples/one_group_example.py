#!/usr/bin/env python3
"""Пример поведения OneGroup: переключение между активными хуками при сбоях."""

import logging
import sys

from lifecycle import (
    BaseExecutableHook,
    HookContext,
    HookResult,
    OneGroup,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")


class FailFirstThenOkHook(BaseExecutableHook):
    """Хук, который при первом INIT возвращает FAILURE, при повторном – SUCCESS."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.attempts = 0

    def _do_init(self) -> HookResult:
        self.attempts += 1
        if self.attempts == 1:
            print(f"{self.name}: первый INIT -> FAILURE")
            return HookResult.FAILURE
        print(f"{self.name}: повторный INIT (попытка {self.attempts}) -> SUCCESS")
        return HookResult.SUCCESS

    def _do_quit(self) -> HookResult:
        print(f"{self.name}: QUIT")
        return HookResult.SUCCESS


class AlwaysWorksHook(BaseExecutableHook):
    """Всегда успешный хук."""

    def _do_init(self) -> HookResult:
        print(f"{self.name}: SUCCESS")
        return HookResult.SUCCESS

    def _do_quit(self) -> HookResult:
        print(f"{self.name}: QUIT")
        return HookResult.SUCCESS


def main() -> None:
    print("=== OneGroup: отказ первого хука, успех второго ===")
    group = OneGroup(
        "switcher",
        [
            FailFirstThenOkHook("A"),
            AlwaysWorksHook("B"),
        ],
    )

    # Первый INIT: A возвращает FAILURE, группа переключается на B
    print("\n-- INIT 1 --")
    res = group.process(HookContext.INIT)
    # Для демонстрации активного хука можно использовать другой метод,
    # но в учебных целях оставим с подавлением предупреждения.
    # В реальном коде не обращайтесь к защищённым атрибутам.
    print(f"Результат: {res.name}")  # не выводим _active_hook

    # Сброс
    print("\n-- RESET --")
    group.process(HookContext.RESET)

    print("\n-- INIT 2 --")
    res = group.process(HookContext.INIT)
    print(f"Результат: {res.name}")

    # Завершаем
    print("\n-- QUIT --")
    group.process(HookContext.QUIT)


if __name__ == "__main__":
    sys.exit(main())
