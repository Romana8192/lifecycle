"""
Модуль исключений для системы жизненного цикла.

Определяет иерархию исключений, используемых в пакете lifecycle.
Базовым является LifeCycleError, от которого наследуются все остальные.

Иерархия:

::

    LifeCycleError
    ├── LifeCycleConfigurationError
    │   ├── GroupConfigurationError
    │   ├── HookExistsError
    │   ├── HookNameExistsError
    │   └── UnknownSelectionModeError
    ├── LifeCycleDependencyError
    │   ├── CircularDependencyError
    │   └── UnknownDependencyError
    ├── LifeCycleStateError
    │   ├── InvalidStateError
    │   └── LifeStateError
    └── LifeCycleRuntimeError
        └── UnknownContextError
"""

__all__ = [
    "CircularDependencyError",
    "GroupConfigurationError",
    "HookExistsError",
    "HookNameExistsError",
    "InvalidStateError",
    "LifeCycleConfigurationError",
    "LifeCycleDependencyError",
    "LifeCycleError",
    "LifeCycleRuntimeError",
    "LifeCycleStateError",
    "LifeStateError",
    "UnknownContextError",
    "UnknownDependencyError",
    "UnknownSelectionModeError",
]


class LifeCycleError(Exception):
    """Базовое исключение для всех ошибок системы жизненного цикла."""


class LifeCycleConfigurationError(LifeCycleError):
    """
    Исключение для ошибок конфигурации (неверные параметры, конфликты).

    Example:
        >>> raise LifeCycleConfigurationError("Неверная конфигурация")
        Traceback (most recent call last):
        ...
        lifecycle.exceptions.LifeCycleConfigurationError: Неверная конфигурация
    """


class LifeCycleDependencyError(LifeCycleError):
    """
    Исключение для ошибок, связанных с зависимостями между хуками.

    Example:
        >>> raise LifeCycleDependencyError("Обнаружена циклическая зависимость")
        Traceback (most recent call last):
        ...
        lifecycle.exceptions.LifeCycleDependencyError: Обнаружена циклическая зависимость
    """


class LifeCycleStateError(LifeCycleError):
    """
    Исключение для ошибок, связанных с некорректным состоянием.

    Example:
        >>> raise LifeCycleStateError("Недопустимый переход состояния")
        Traceback (most recent call last):
        ...
        lifecycle.exceptions.LifeCycleStateError: Недопустимый переход состояния
    """


class LifeCycleRuntimeError(LifeCycleError):
    """
    Исключение для прочих ошибок времени выполнения.

    Example:
        >>> raise LifeCycleRuntimeError("Ошибка времени выполнения")
        Traceback (most recent call last):
        ...
        lifecycle.exceptions.LifeCycleRuntimeError: Ошибка времени выполнения
    """


class GroupConfigurationError(LifeCycleConfigurationError):
    """Ошибка конфигурации группы хуков."""


class HookExistsError(LifeCycleConfigurationError):
    """Попытка добавить уже существующий хук."""


class HookNameExistsError(LifeCycleConfigurationError):
    """Попытка добавить хук с именем, которое уже используется."""


class UnknownSelectionModeError(LifeCycleConfigurationError):
    """Неизвестный режим выбора (SelectionMode) при создании группы."""


class CircularDependencyError(LifeCycleDependencyError):
    """Обнаружена циклическая зависимость между хуками."""


class UnknownDependencyError(LifeCycleDependencyError):
    """Зависимость указывает на несуществующий хук."""


class InvalidStateError(LifeCycleStateError):
    """Операция вызвана в неподходящем состоянии."""


class LifeStateError(LifeCycleStateError):
    """Ошибка, связанная с состоянием жизненного цикла."""


class UnknownContextError(LifeCycleRuntimeError):
    """Использован неизвестный контекст (HookContext)."""
