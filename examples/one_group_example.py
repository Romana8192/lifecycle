import sys
from typing import ClassVar

from lifecycle import (
    BaseExecutableHook,
    HookContext,
    HookRequirement,
    HookResult,
    LifeState,
    OneGroup,
)


class RiskyHook(BaseExecutableHook):
    """Хук, который при INIT всегда возвращает FATAL (переводит группу в ERROR)."""

    requirement: ClassVar[HookRequirement] = HookRequirement.REQUIRED

    def _do_init(self) -> HookResult:
        print("RiskyHook: возвращаю FATAL")
        return HookResult.FATAL


def safe_quit(group: OneGroup) -> None:
    """Безопасно останавливает группу: сначала RESET (если ERROR), затем QUIT."""
    if group.state == LifeState.RUNNING:
        group.process(HookContext.QUIT)
    elif group.state == LifeState.ERROR:
        print("Группа в ERROR, выполняю RESET для восстановления...")
        reset_res = group.process(HookContext.RESET)
        if reset_res == HookResult.SUCCESS:
            print("RESET успешен, теперь можно QUIT")
            group.process(HookContext.QUIT)
        else:
            print("Не удалось выйти из ERROR, QUIT невозможен")
    else:
        print(f"Группа в состоянии {group.state.name}, QUIT не требуется")


def main() -> None:
    group = OneGroup("test", [RiskyHook("R")])

    print("--- INIT (должен перевести в ERROR) ---")
    res = group.process(HookContext.INIT)
    print(f"Результат INIT: {res.name}")
    print(f"Состояние группы: {group.state.name}")

    print("\n--- Безопасный QUIT ---")
    safe_quit(group)
    print(f"Состояние после: {group.state.name}")


if __name__ == "__main__":
    sys.exit(main())
