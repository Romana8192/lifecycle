"""Пример создания хуков путём наследования от BaseExecutableHook."""

import logging
import sys

from lifecycle import BaseExecutableHook, HookResult, LifeCycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")


class DatabaseHook(BaseExecutableHook):
    """Хук, имитирующий подключение к базе данных."""

    def __init__(self, name: str = "DB") -> None:
        super().__init__(name)
        self._connected = False

    def _do_init(self) -> HookResult:
        print(f"{self.name}: устанавливаю соединение с БД...")
        self._connected = True
        return HookResult.SUCCESS

    def _do_quit(self) -> HookResult:
        if self._connected:
            print(f"{self.name}: закрываю соединение с БД...")
            self._connected = False
        return HookResult.SUCCESS

    def _do_error(self) -> HookResult:
        print(f"{self.name}: аварийное закрытие соединения (очистка)")
        self._connected = False
        return HookResult.SUCCESS


class CacheHook(BaseExecutableHook):
    """Хук для работы с кэшем."""

    def __init__(self, name: str = "Cache") -> None:
        super().__init__(name)
        self._ready = False

    def _do_init(self) -> HookResult:
        print(f"{self.name}: инициализация кэша...")
        self._ready = True
        return HookResult.SUCCESS

    def _do_quit(self) -> HookResult:
        if self._ready:
            print(f"{self.name}: сброс кэша...")
            self._ready = False
        return HookResult.SUCCESS


def main() -> None:
    db_hook = DatabaseHook()
    cache_hook = CacheHook()

    lc = LifeCycle(hooks=[db_hook, cache_hook])

    print("--- INIT ---")
    lc.initialize()
    print("--- QUIT ---")
    lc.finalize()


if __name__ == "__main__":
    sys.exit(main())
