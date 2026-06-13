"""Пример обработки ошибок: FATAL, FAILURE, REQUIRE vs OPTIONAL."""

import logging
import sys
from typing import ClassVar

from lifecycle import (
    BaseExecutableHook,
    HookRequirement,
    HookResult,
    LifeCycle,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")


class FailingOptionalHook(BaseExecutableHook):
    """Опциональный хук, который возвращает FAILURE (не критично)."""

    requirement: ClassVar[HookRequirement] = HookRequirement.OPTIONAL

    def _do_init(self) -> HookResult:
        print(f"{self.name}: возвращаю FAILURE")
        return HookResult.FAILURE


class FatalRequiredHook(BaseExecutableHook):
    """Обязательный хук, возвращающий FATAL (критично)."""

    requirement: ClassVar[HookRequirement] = HookRequirement.REQUIRED

    def _do_init(self) -> HookResult:
        print(f"{self.name}: возвращаю FATAL")
        return HookResult.FATAL


class GoodHook(BaseExecutableHook):
    """Успешный хук."""

    def _do_init(self) -> HookResult:
        print(f"{self.name}: SUCCESS")
        return HookResult.SUCCESS

    def _do_quit(self) -> HookResult:
        print(f"{self.name}: очистка")
        return HookResult.SUCCESS


def main() -> None:
    print("=== Сценарий 1: опциональный FAILURE ===")
    lc1 = LifeCycle(hooks=[FailingOptionalHook("Optional"), GoodHook("Good")])
    ok = lc1.initialize()
    print(f"initialize() вернула {ok} (True, т.к. нет FATAL)")
    print(f"Состояние LifeCycle: {lc1.state.name} (ожидается RUNNING)")
    lc1.finalize()

    print("\n=== Сценарий 2: обязательный FATAL ===")
    lc2 = LifeCycle(hooks=[FatalRequiredHook("Fatal"), GoodHook("Good")])
    ok = lc2.initialize()
    print(f"initialize() вернула {ok} (False из-за FATAL)")
    print(f"Состояние LifeCycle: {lc2.state.name} (ожидается ERROR)")


if __name__ == "__main__":
    sys.exit(main())
