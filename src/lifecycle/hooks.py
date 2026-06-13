"""
Модуль хуков системы жизненного цикла.

Определяет базовый класс BaseExecutableHook и протокол ExecutableHook,
а также фабричную функцию для создания адаптеров из колбэков.
"""

import logging
from collections.abc import Iterable
from typing import ClassVar, Protocol, runtime_checkable

from typeguard import typechecked

from .exceptions import LifeCycleError
from .lifecycle_types import (
    HookCallbacks,
    HookContext,
    HookDependency,
    HookRequirement,
    HookResult,
    LifeState,
)

__all__ = ["BaseExecutableHook", "ExecutableHook", "create_adapter"]

logger = logging.getLogger(__name__)


@runtime_checkable
class ExecutableHook(Protocol):
    """
    Протокол, описывающий интерфейс исполняемого хука.
    """

    dependencies: ClassVar[tuple[HookDependency, ...]]
    requirement: ClassVar[HookRequirement]

    def process(self, context: HookContext) -> HookResult: ...

    @property
    def state(self) -> LifeState: ...

    @property
    def name(self) -> str: ...


class BaseExecutableHook:
    """
    Базовый класс для реализации хуков.
    """

    dependencies: ClassVar[tuple[HookDependency, ...]] = ()
    requirement: ClassVar[HookRequirement] = HookRequirement.OPTIONAL

    _name: str
    _state: LifeState

    __slots__ = ("_name", "_state")

    @typechecked
    def __init__(self, name: str) -> None:
        self._name = name
        self._state = LifeState.NEW
        logger.debug("Хук '%s' создан в состоянии NEW", name)

    @typechecked
    def process(self, context: HookContext) -> HookResult:
        logger.debug(
            "Хук '%s' обрабатывает контекст %s в состоянии %s",
            self._name,
            context.name,
            self._state.name,
        )
        if context == HookContext.INIT:
            return self._init()
        if context == HookContext.QUIT:
            return self._quit()
        if context == HookContext.ERROR:
            return self._error()
        if context == HookContext.RESET:
            return self._reset()
        logger.error("Хук '%s' получил неизвестный контекст %s", self._name, context)
        return HookResult.FATAL

    def _init(self) -> HookResult:
        if self._state == LifeState.RUNNING:
            logger.debug("Хук '%s' уже в состоянии RUNNING, пропускаем инициализацию", self._name)
            return HookResult.SUCCESS
        if self._state != LifeState.NEW:
            logger.warning(
                "Хук '%s' не может быть инициализирован из состояния %s",
                self._name,
                self._state.name,
            )
            return HookResult.FAILURE

        self._state = LifeState.INITIALIZING
        logger.info("Хук '%s' начинает инициализацию", self._name)
        try:
            result = self._do_init()
        except LifeCycleError as e:
            logger.warning("Хук '%s' выбросил LifeCycleError: %s", self._name, e)
            if self.requirement == HookRequirement.REQUIRED:
                result = HookResult.FATAL
            else:
                result = HookResult.FAILURE
        except Exception as e:
            logger.exception("Хук '%s' выбросил непредвиденное исключение: %s", self._name, e)
            result = HookResult.FATAL

        if result == HookResult.SUCCESS:
            self._state = LifeState.RUNNING
            logger.info("Хук '%s' успешно инициализирован, состояние RUNNING", self._name)
        elif result == HookResult.FATAL:
            self._state = LifeState.ERROR
            logger.error("Хук '%s' перешёл в ERROR из-за FATAL", self._name)
        else:  # FAILURE
            self._state = LifeState.NEW
            logger.warning("Хук '%s' не инициализирован (FAILURE), остаётся NEW", self._name)
        return result

    def _quit(self) -> HookResult:
        if self._state == LifeState.STOPPED:
            logger.debug("Хук '%s' уже в состоянии STOPPED", self._name)
            return HookResult.SUCCESS
        if self._state != LifeState.RUNNING:
            logger.warning(
                "Хук '%s' не может быть остановлен из состояния %s",
                self._name,
                self._state.name,
            )
            return HookResult.FAILURE

        self._state = LifeState.STOPPING
        logger.info("Хук '%s' начинает остановку", self._name)
        try:
            result = self._do_quit()
        except LifeCycleError as e:
            logger.warning("Хук '%s' выбросил LifeCycleError: %s", self._name, e)
            if self.requirement == HookRequirement.REQUIRED:
                result = HookResult.FATAL
            else:
                result = HookResult.FAILURE
        except Exception as e:
            logger.exception("Хук '%s' выбросил непредвиденное исключение: %s", self._name, e)
            result = HookResult.FATAL

        if result == HookResult.SUCCESS:
            self._state = LifeState.STOPPED
            logger.info("Хук '%s' остановлен, состояние STOPPED", self._name)
        elif result == HookResult.FATAL:
            self._state = LifeState.ERROR
            logger.error("Хук '%s' перешёл в ERROR при остановке", self._name)
        else:  # FAILURE
            self._state = LifeState.STOPPED
            logger.warning("Хук '%s' остановлен с результатом FAILURE", self._name)
        return result

    def _reset(self) -> HookResult:
        if self._state == LifeState.NEW:
            logger.debug("Хук '%s' уже в состоянии NEW", self._name)
            return HookResult.SUCCESS
        if self._state == LifeState.RUNNING:
            logger.info("Хук '%s' останавливается перед сбросом", self._name)
            quit_result = self._quit()
            if quit_result == HookResult.FATAL:
                logger.error("Хук '%s' не удалось остановить при сбросе", self._name)
                return HookResult.FATAL

        self._state = LifeState.RESETTING
        logger.info("Хук '%s' начинает сброс", self._name)
        try:
            result = self._do_reset()
        except LifeCycleError as e:
            logger.warning("Хук '%s' выбросил LifeCycleError: %s", self._name, e)
            if self.requirement == HookRequirement.REQUIRED:
                result = HookResult.FATAL
            else:
                result = HookResult.FAILURE
        except Exception as e:
            logger.exception("Хук '%s' выбросил непредвиденное исключение: %s", self._name, e)
            result = HookResult.FATAL

        if result == HookResult.SUCCESS:
            self._state = LifeState.NEW
            logger.info("Хук '%s' сброшен, состояние NEW", self._name)
        elif result == HookResult.FATAL:
            self._state = LifeState.ERROR
            logger.error("Хук '%s' перешёл в ERROR при сбросе", self._name)
        else:  # FAILURE
            self._state = LifeState.NEW
            logger.warning("Хук '%s' сброшен с результатом FAILURE", self._name)
        return result

    def _error(self) -> HookResult:
        if self._state == LifeState.ERROR:
            logger.debug("Хук '%s' уже в состоянии ERROR", self._name)
            return HookResult.SUCCESS
        logger.warning(
            "Хук '%s' переходит в ERROR из состояния %s",
            self._name,
            self._state.name,
        )
        self._state = LifeState.ERROR
        try:
            result = self._do_error()
        except LifeCycleError as e:
            logger.warning("Хук '%s' выбросил LifeCycleError: %s", self._name, e)
            if self.requirement == HookRequirement.REQUIRED:
                result = HookResult.FATAL
            else:
                result = HookResult.FAILURE
        except Exception as e:
            logger.exception("Хук '%s' выбросил непредвиденное исключение: %s", self._name, e)
            result = HookResult.FATAL
        return result

    def _do_init(self) -> HookResult:
        return HookResult.SUCCESS

    def _do_quit(self) -> HookResult:
        return HookResult.SUCCESS

    def _do_reset(self) -> HookResult:
        return HookResult.SUCCESS

    def _do_error(self) -> HookResult:
        return HookResult.SUCCESS

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> LifeState:
        return self._state


class _HookAdapter(BaseExecutableHook):
    __slots__ = ("_error_func", "_init_func", "_quit_func", "_reset_func")

    @typechecked
    def __init__(self, name: str, callbacks: HookCallbacks) -> None:
        super().__init__(name)
        self._init_func = callbacks.init
        self._quit_func = callbacks.quit
        self._error_func = callbacks.error
        self._reset_func = callbacks.reset
        logger.debug("Создан адаптер для хука '%s' с колбэками", name)

    def _do_init(self) -> HookResult:
        if self._init_func is not None:
            logger.debug("Вызов колбэка init для хука '%s'", self.name)
            return self._init_func()
        return super()._do_init()

    def _do_quit(self) -> HookResult:
        if self._quit_func is not None:
            logger.debug("Вызов колбэка quit для хука '%s'", self.name)
            return self._quit_func()
        return super()._do_quit()

    def _do_error(self) -> HookResult:
        if self._error_func is not None:
            logger.debug("Вызов колбэка error для хука '%s'", self.name)
            return self._error_func()
        return super()._do_error()

    def _do_reset(self) -> HookResult:
        if self._reset_func is not None:
            logger.debug("Вызов колбэка reset для хука '%s'", self.name)
            return self._reset_func()
        return super()._do_reset()


@typechecked
def create_adapter(
    name: str,
    callbacks: HookCallbacks,
    requirement: HookRequirement = HookRequirement.OPTIONAL,
    dependencies: Iterable[HookDependency] = (),
) -> ExecutableHook:
    logger.debug("Создание адаптера для хука '%s' с requirement=%s", name, requirement)
    adapter_class = type(
        "_DynamicHookAdapter",
        (_HookAdapter,),
        {
            "__annotations__": {
                "requirement": ClassVar[HookRequirement],
                "dependencies": ClassVar[tuple[HookDependency]],
            },
            "requirement": requirement,
            "dependencies": tuple(dependencies),
            "__slots__": (),
        },
    )
    logger.debug(
        "Создан динамический адаптер для хука '%s' с requirement=%s и зависимостями=%s",
        name,
        requirement,
        dependencies,
    )
    return adapter_class(name, callbacks)  # type: ignore[no-any-return]
