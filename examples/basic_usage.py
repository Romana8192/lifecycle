"""Базовый пример: создание LifeCycle из двух хуков-адаптеров."""

import logging
import sys

from lifecycle import HookCallbacks, HookResult, LifeCycle, create_adapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> None:
    callbacks1 = HookCallbacks(
        init=lambda: (print("Хук A: инициализация"), HookResult.SUCCESS)[1],
        quit=lambda: (print("Хук A: завершение"), HookResult.SUCCESS)[1],
    )
    callbacks2 = HookCallbacks(
        init=lambda: (print("Хук B: инициализация"), HookResult.SUCCESS)[1],
        quit=lambda: (print("Хук B: завершение"), HookResult.SUCCESS)[1],
    )

    hook_a = create_adapter("A", callbacks1)
    hook_b = create_adapter("B", callbacks2)

    lc = LifeCycle(hooks=[hook_a, hook_b])

    print("Состояние до инициализации:", lc.state.name)
    lc.initialize()
    print("Состояние после инициализации:", lc.state.name)

    lc.finalize()
    print("Состояние после завершения:", lc.state.name)

    lc.reset()
    print("Состояние после сброса:", lc.state.name)


if __name__ == "__main__":
    sys.exit(main())
