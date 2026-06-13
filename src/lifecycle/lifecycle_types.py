"""
Модуль типов данных системы жизненного цикла.

Содержит перечисления (Enum) для состояний, контекстов, результатов,
а также классы для описания зависимостей (HookDependency) и колбэков (HookCallbacks).

Все типы используются в остальных модулях пакета для обеспечения
типобезопасности и единообразия.

Пример:
    >>> from lifecycle import HookContext, HookResult, LifeState
    >>> context = HookContext.INIT
    >>> context.name
    'INIT'
    >>> HookResult.SUCCESS.value
    <enum 'auto'>
"""

from __future__ import annotations

import logging
from collections.abc import Callable  # noqa: TC003
from enum import Enum, auto

from typeguard import typechecked

from .exceptions import UnknownContextError

__all__ = [
    "DependenceOrder",
    "HookCallbacks",
    "HookContext",
    "HookDependency",
    "HookRequirement",
    "HookResult",
    "LifeState",
    "SelectionMode",
]

logger = logging.getLogger(__name__)


class LifeState(Enum):
    """
    Состояния жизненного цикла хука или группы.

    NEW — только что создан, не инициализирован.
    INITIALIZING — инициализация в процессе.
    RUNNING — нормальная работа.
    STOPPING — остановка в процессе.
    STOPPED — остановлен.
    ERROR — произошла фатальная ошибка.
    RESETTING — сброс в процессе.
    """

    NEW = auto()
    INITIALIZING = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()
    RESETTING = auto()


class HookRequirement(Enum):
    """Требование к хуку: обязательный (REQUIRED) или опциональный (OPTIONAL)."""

    OPTIONAL = auto()
    REQUIRED = auto()


class HookContext(Enum):
    """Контекст выполнения хука: инициализация, завершение, ошибка, сброс."""

    INIT = auto()
    QUIT = auto()
    ERROR = auto()
    RESET = auto()


class SelectionMode(Enum):
    """Режим выбора хуков в группе: выполнить все (ALL) или один (ONE)."""

    ALL = auto()
    ONE = auto()


class HookResult(Enum):
    """Результат выполнения хука: успех, фатальная ошибка, некритичная ошибка."""

    SUCCESS = auto()
    FATAL = auto()
    FAILURE = auto()


class DependenceOrder(Enum):
    """Порядок зависимости между хуками для конкретного контекста.

    UNORDERED — порядок не важен.
    BEFORE — текущий хук должен выполняться до указанного.
    AFTER — текущий хук должен выполняться после указанного.
    """

    UNORDERED = auto()
    BEFORE = auto()
    AFTER = auto()


class HookDependency:
    """
    Описание зависимости между хуками.

    Позволяет задать порядок выполнения для каждого контекста отдельно.
    Зависимость привязана к имени целевого хука.

    Attributes:
        name (str): Имя хука, от которого зависит текущий.

    Example:
        >>> dep = HookDependency("other", init_order=DependenceOrder.AFTER)
        >>> dep.name
        'other'
        >>> dep.get_order(HookContext.INIT) is DependenceOrder.AFTER
        True
    """

    _name: str
    _init_order: DependenceOrder
    _quit_order: DependenceOrder
    _reset_order: DependenceOrder
    _error_order: DependenceOrder

    __slots__ = ("_error_order", "_init_order", "_name", "_quit_order", "_reset_order")

    @typechecked
    def __init__(
        self,
        name: str,
        init_order: DependenceOrder = DependenceOrder.UNORDERED,
        quit_order: DependenceOrder = DependenceOrder.UNORDERED,
        reset_order: DependenceOrder = DependenceOrder.UNORDERED,
        error_order: DependenceOrder = DependenceOrder.UNORDERED,
    ) -> None:
        """
        Инициализирует зависимость.

        Args:
            name: Имя хука, от которого зависит текущий.
            init_order: Порядок выполнения в контексте INIT.
            quit_order: Порядок выполнения в контексте QUIT.
            reset_order: Порядок выполнения в контексте RESET.
            error_order: Порядок выполнения в контексте ERROR.
        """
        self._name = name
        self._init_order = init_order
        self._quit_order = quit_order
        self._reset_order = reset_order
        self._error_order = error_order
        logger.debug(
            "Создана зависимость: name='%s', init=%s, quit=%s, reset=%s, error=%s",
            name,
            init_order.name,
            quit_order.name,
            reset_order.name,
            error_order.name,
        )

    @typechecked
    def get_order(self, context: HookContext) -> DependenceOrder:
        """
        Возвращает порядок зависимости для указанного контекста.

        Args:
            context: Контекст выполнения.

        Returns:
            DependenceOrder для данного контекста.

        Raises:
            UnknownContextError: Если передан неизвестный контекст.
        """
        if context == HookContext.INIT:
            return self._init_order
        if context == HookContext.QUIT:
            return self._quit_order
        if context == HookContext.RESET:
            return self._reset_order
        if context == HookContext.ERROR:
            return self._error_order
        raise UnknownContextError(f"Неизвестный контекст {context.name}")

    @property
    def name(self) -> str:
        """Имя хука, от которого зависит текущий."""
        return self._name


class HookCallbacks:
    """
    Контейнер для callback-функций хука.

    Используется при создании адаптера (create_adapter) для задания
    пользовательской логики на каждый контекст.

    Attributes:
        init: Callback для контекста INIT.
        quit: Callback для контекста QUIT.
        error: Callback для контекста ERROR.
        reset: Callback для контекста RESET.

    Example:
        >>> def on_init() -> HookResult:
        ...     print("Init called")
        ...     return HookResult.SUCCESS
        >>> callbacks = HookCallbacks(init=on_init)
        >>> callbacks.init is on_init
        True
    """

    init: Callable[[], HookResult] | None
    quit: Callable[[], HookResult] | None
    error: Callable[[], HookResult] | None
    reset: Callable[[], HookResult] | None

    __slots__ = ("error", "init", "quit", "reset")

    @typechecked
    def __init__(
        self,
        init: Callable[[], HookResult] | None = None,
        quit: Callable[[], HookResult] | None = None,  # noqa: A002
        error: Callable[[], HookResult] | None = None,
        reset: Callable[[], HookResult] | None = None,
    ) -> None:
        """
        Инициализирует контейнер колбэков.

        Args:
            init: Функция без аргументов, возвращающая HookResult.
            quit: Функция без аргументов, возвращающая HookResult.
            error: Функция без аргументов, возвращающая HookResult.
            reset: Функция без аргументов, возвращающая HookResult.

        Raises:
            ValueError: Если не передан ни один колбэк.
        """
        if (init is None) and (quit is None) and (error is None) and (reset is None):
            raise ValueError("Должен быть задан хотя бы один колбэк")

        self.init = init
        self.quit = quit
        self.error = error
        self.reset = reset
        logger.debug(
            "Создан HookCallbacks: init=%s, quit=%s, error=%s, reset=%s",
            bool(init),
            bool(quit),
            bool(error),
            bool(reset),
        )

    def __repr__(self) -> str:
        parts = [name for name in ("init", "quit", "error", "reset") if getattr(self, name)]
        return f"HookCallbacks({', '.join(parts)})"
