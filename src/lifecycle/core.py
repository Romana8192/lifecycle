"""
Модуль ядра системы жизненного цикла.

Содержит класс LifeCycle, который является основным интерфейсом для управления
группой хуков. LifeCycle обрабатывает контексты INIT, QUIT, RESET и делегирует
выполнение корневой группе хуков.

Пример:
    >>> from lifecycle import LifeCycle, create_adapter, HookCallbacks, HookResult
    >>> cb = HookCallbacks(init=lambda: HookResult.SUCCESS)
    >>> hook = create_adapter("test", cb)
    >>> lc = LifeCycle(hooks=[hook])
    >>> lc.state.name
    'NEW'
    >>> lc.initialize()
    True
    >>> lc.state.name
    'RUNNING'
    >>> lc.finalize()
    True
"""

import logging
from collections.abc import Iterable

from typeguard import typechecked

from .groups import BaseGroup, create_group
from .hooks import ExecutableHook
from .lifecycle_types import HookContext, HookRequirement, HookResult, LifeState, SelectionMode

logger = logging.getLogger(__name__)

__all__ = ["LifeCycle"]


class LifeCycle:
    """
    Основной класс управления жизненным циклом.

    Инкапсулирует корневую группу хуков и управляет её состояниями.
    Позволяет добавлять/удалять хуки, инициализировать, завершать и сбрасывать
    жизненный цикл. Внутри использует топологическую сортировку зависимостей.

    Attributes:
        _root_group (BaseGroup): Корневая группа хуков.
        _state (LifeState): Текущее состояние жизненного цикла.

    Example:
        >>> lc = LifeCycle(hooks=[])
        >>> lc.initialize()
        True
        >>> lc.state is LifeState.RUNNING
        True
        >>> lc.finalize()
        True
    """

    _root_group: BaseGroup
    _state: LifeState

    __slots__ = ("_root_group", "_state")

    @typechecked
    def __init__(
        self,
        hooks: Iterable[ExecutableHook] | None = None,
        *,
        group: BaseGroup | None = None,
    ) -> None:
        """
        Инициализирует экземпляр LifeCycle.

        Args:
            hooks: Итерируемый объект хуков для автоматического создания группы
                   типа ALL с именем "root". Не может быть указан одновременно с group.
            group: Готовая корневая группа. Должна находиться в состоянии NEW или STOPPED.
                   Не может быть указана одновременно с hooks.

        Raises:
            ValueError: Если указаны оба параметра hooks и group,
                        или ни один из них не указан,
                        или группа находится в недопустимом состоянии.

        Example:
            >>> from lifecycle import BaseExecutableHook
            >>> class MyHook(BaseExecutableHook):
            ...     pass
            >>> hook = MyHook("test")
            >>> lc = LifeCycle(hooks=[hook])
            >>> lc.state is LifeState.NEW
            True
        """
        logger.debug("Создание LifeCycle: hooks=%s, group=%s", hooks, group)
        if group is not None and hooks is not None:
            raise ValueError("Нельзя указать оба параметра 'group' и 'hooks'")

        if group is not None:
            if group.state not in (LifeState.NEW, LifeState.STOPPED):
                raise ValueError(
                    f"Состояние группы должно быть NEW или STOPPED, получено {group.state.name}",
                )
            self._root_group = group
            logger.info("LifeCycle инициализирован с готовой группой '%s'", group.name)
        elif hooks is not None:
            self._root_group = create_group(
                SelectionMode.ALL,
                "root",
                list(hooks),
                requirement=HookRequirement.REQUIRED,
            )
            logger.info("LifeCycle инициализирован с %d хуками", len(list(hooks)))
        else:
            raise ValueError("Должен быть указан либо 'group', либо 'hooks'")

        self._state = LifeState.NEW
        logger.debug("LifeCycle создан в состоянии NEW")

    @typechecked
    def add_hook(self, hook: ExecutableHook) -> bool:
        """
        Добавляет хук в корневую группу.

        Note:
            Если жизненный цикл находится в состоянии RUNNING или ERROR,
            добавление невозможно. Также метод перехватывает все исключения
            (например, дубликат имени) и возвращает False.

        Args:
            hook: Добавляемый исполняемый хук.

        Returns:
            True, если добавление успешно, False в противном случае
            (например, если жизненный цикл находится в состоянии RUNNING).

        Example:
            >>> lc = LifeCycle(hooks=[])
            >>> from lifecycle import BaseExecutableHook
            >>> h = BaseExecutableHook("new_hook")
            >>> lc.add_hook(h)
            True
        """
        logger.debug(
            "Попытка добавить хук '%s' в LifeCycle (текущее состояние %s)",
            hook.name,
            self._state.name,
        )
        if self._state not in (LifeState.NEW, LifeState.STOPPED):
            logger.warning("Невозможно добавить хук в состоянии %s", self._state.name)
            return False
        try:
            self._root_group.extend(hook)
            logger.info("Хук '%s' успешно добавлен в LifeCycle", hook.name)
            return True
        except Exception as e:
            logger.exception("Ошибка при добавлении хука '%s': %s", hook.name, e)
            return False

    @typechecked
    def remove_hook(self, hook: str | ExecutableHook) -> bool:
        """
        Удаляет хук из корневой группы по имени или по объекту.

        Args:
            hook: Имя хука (str) или сам объект ExecutableHook.

        Returns:
            True, если удаление успешно, False в противном случае.

        Example:
            >>> lc = LifeCycle(hooks=[])
            >>> from lifecycle import BaseExecutableHook
            >>> h = BaseExecutableHook("to_remove")
            >>> lc.add_hook(h)
            True
            >>> lc.remove_hook("to_remove")
            True
        """
        hook_identifier = hook.name if isinstance(hook, ExecutableHook) else hook
        logger.debug(
            "Попытка удалить хук '%s' из LifeCycle (состояние %s)",
            hook_identifier,
            self._state.name,
        )
        if self._state not in (LifeState.NEW, LifeState.STOPPED):
            logger.warning("Невозможно удалить хук в состоянии %s", self._state.name)
            return False
        try:
            self._root_group.remove(hook)
            logger.info("Хук '%s' успешно удалён из LifeCycle", hook_identifier)
            return True
        except Exception as e:
            logger.exception("Ошибка при удалении хука '%s': %s", hook_identifier, e)
            return False

    def initialize(self) -> bool:
        """
        Инициализирует жизненный цикл, обрабатывая контекст INIT в корневой группе.

        Returns:
            True, если инициализация прошла успешно (группа перешла в RUNNING),
            False в случае ошибки (переход в ERROR).

        Raises:
            Не генерирует исключений, все ошибки логируются и приводят к False.

        Example:
            >>> lc = LifeCycle(hooks=[])
            >>> lc.initialize()
            True
            >>> lc.state is LifeState.RUNNING
            True
        """
        logger.info("Запуск инициализации LifeCycle (текущее состояние %s)", self._state.name)
        if self._state == LifeState.RUNNING:
            logger.debug("LifeCycle уже в состоянии RUNNING, инициализация не требуется")
            return True
        if self._state != LifeState.NEW:
            logger.warning(
                "Невозможно инициализировать LifeCycle из состояния %s",
                self._state.name,
            )
            return False

        try:
            result = self._root_group.process(HookContext.INIT)
            logger.debug("Результат обработки INIT корневой группой: %s", result.name)
        except Exception as e:
            logger.exception("Исключение при инициализации корневой группы: %s", e)
            self._state = LifeState.ERROR
            return False

        if result == HookResult.SUCCESS:
            self._state = LifeState.RUNNING
            logger.info("LifeCycle успешно инициализирован, переход в RUNNING")
            return True
        if result == HookResult.FAILURE:
            self._state = LifeState.RUNNING
            logger.warning("LifeCycle инициализирован с ошибками (FAILURE), но перешёл в RUNNING")
            return True
        self._state = LifeState.ERROR
        logger.error("LifeCycle перешёл в ERROR из-за результата %s", result.name)
        return False

    def finalize(self) -> bool:
        """
        Завершает жизненный цикл, обрабатывая контекст QUIT в корневой группе.

        Returns:
            True, если завершение успешно (группа перешла в STOPPED),
            False в случае ошибки (переход в ERROR).

        Example:
            >>> lc = LifeCycle(hooks=[])
            >>> lc.initialize()
            True
            >>> lc.finalize()
            True
            >>> lc.state is LifeState.STOPPED
            True
        """
        logger.info("Запуск завершения LifeCycle (текущее состояние %s)", self._state.name)
        if self._state == LifeState.STOPPED:
            logger.debug("LifeCycle уже в состоянии STOPPED, завершение не требуется")
            return True
        if self._state != LifeState.RUNNING:
            logger.warning("Невозможно завершить LifeCycle из состояния %s", self._state.name)
            return False

        try:
            result = self._root_group.process(HookContext.QUIT)
            logger.debug("Результат обработки QUIT корневой группой: %s", result.name)
        except Exception as e:
            logger.exception("Исключение при завершении корневой группы: %s", e)
            self._state = LifeState.ERROR
            return False

        if result == HookResult.SUCCESS:
            self._state = LifeState.STOPPED
            logger.info("LifeCycle успешно завершён, переход в STOPPED")
            return True
        if result == HookResult.FAILURE:
            self._state = LifeState.STOPPED
            logger.warning("LifeCycle завершён с ошибками (FAILURE), но перешёл в STOPPED")
            return True
        self._state = LifeState.ERROR
        logger.error("LifeCycle перешёл в ERROR из-за результата %s", result.name)
        return False

    def reset(self) -> bool:
        """
        Сбрасывает жизненный цикл, обрабатывая контекст RESET в корневой группе.

        Returns:
            True, если сброс успешен (группа возвращается в RUNNING),
            False в случае ошибки (переход в ERROR).

        Example:
            >>> lc = LifeCycle(hooks=[])
            >>> lc.initialize()
            True
            >>> lc.reset()
            True
            >>> lc.state is LifeState.RUNNING
            True
        """
        logger.info("Запуск сброса LifeCycle (текущее состояние %s)", self._state.name)
        if self._state == LifeState.NEW:
            logger.debug("LifeCycle уже в состоянии NEW, сброс не требуется")
            return True

        try:
            result = self._root_group.process(HookContext.RESET)
            logger.debug("Результат обработки RESET корневой группой: %s", result.name)
        except Exception as e:
            logger.exception("Исключение при сбросе корневой группы: %s", e)
            self._state = LifeState.ERROR
            return False

        if result in (HookResult.SUCCESS, HookResult.FAILURE):
            self._state = LifeState.RUNNING
            if result == HookResult.SUCCESS:
                logger.info("LifeCycle успешно сброшен, переход в RUNNING")
            else:
                logger.warning("LifeCycle сброшен с ошибками (FAILURE), но перешёл в RUNNING")
            return True
        self._state = LifeState.ERROR
        logger.error("LifeCycle перешёл в ERROR из-за результата %s", result.name)
        return False

    @property
    def state(self) -> LifeState:
        """Текущее состояние жизненного цикла."""
        return self._state

    @property
    def hooks(self) -> list[ExecutableHook]:
        """Копия списка хуков корневой группы."""
        return self._root_group.hooks

    @property
    def root_group(self) -> BaseGroup:
        """Корневая группа хуков."""
        return self._root_group

    def __contains__(self, hook: ExecutableHook) -> bool:
        """
        Проверяет, содержится ли хук в корневой группе.

        Args:
            hook: Проверяемый хук.

        Returns:
            True, если хук присутствует, иначе False.
        """
        return hook in self._root_group

    def __len__(self) -> int:
        """Возвращает количество хуков в корневой группе."""
        return len(self._root_group)
