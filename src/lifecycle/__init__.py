"""
Пакет `lifecycle` предоставляет систему управления жизненным циклом
компонентов через механизм исполняемых хуков (hooks).

Основные возможности:
- Группировка хуков с выбором стратегии выполнения (все или один успешный).
- Определение зависимостей между хуками для разных контекстов (INIT, QUIT, ERROR, RESET).
- Строгий контроль состояний (NEW, RUNNING, STOPPED, ERROR и др.).
- Поддержка обязательных (REQUIRED) и опциональных (OPTIONAL) хуков.
- Автоматическая топологическая сортировка хуков по зависимостям.
- Кэширование порядка выполнения для повышения производительности.
- Адаптеры для быстрого создания хуков из callback-функций.

Пример:
    >>> from lifecycle import LifeCycle, create_adapter, HookCallbacks, HookResult
    >>> callbacks = HookCallbacks(init=lambda: HookResult.SUCCESS)
    >>> hook = create_adapter("my_hook", callbacks)
    >>> lc = LifeCycle(hooks=[hook])
    >>> lc.initialize()
    True
    >>> lc.finalize()
    True
"""

from .core import LifeCycle
from .exceptions import (
    CircularDependencyError,
    GroupConfigurationError,
    HookExistsError,
    HookNameExistsError,
    InvalidStateError,
    LifeCycleConfigurationError,
    LifeCycleDependencyError,
    LifeCycleError,
    LifeCycleRuntimeError,
    LifeCycleStateError,
    LifeStateError,
    UnknownContextError,
    UnknownDependencyError,
    UnknownSelectionModeError,
)
from .groups import AllGroup, BaseGroup, OneGroup, create_group
from .hooks import BaseExecutableHook, ExecutableHook, create_adapter
from .lifecycle_types import (
    DependenceOrder,
    HookCallbacks,
    HookContext,
    HookDependency,
    HookRequirement,
    HookResult,
    LifeState,
    SelectionMode,
)

__all__ = [
    "AllGroup",
    "BaseExecutableHook",
    "BaseGroup",
    "CircularDependencyError",
    "DependenceOrder",
    "ExecutableHook",
    "GroupConfigurationError",
    "HookCallbacks",
    "HookContext",
    "HookDependency",
    "HookExistsError",
    "HookNameExistsError",
    "HookRequirement",
    "HookResult",
    "InvalidStateError",
    "LifeCycle",
    "LifeCycleConfigurationError",
    "LifeCycleDependencyError",
    "LifeCycleError",
    "LifeCycleRuntimeError",
    "LifeCycleStateError",
    "LifeState",
    "LifeStateError",
    "OneGroup",
    "SelectionMode",
    "UnknownContextError",
    "UnknownDependencyError",
    "UnknownSelectionModeError",
    "create_adapter",
    "create_group",
]
