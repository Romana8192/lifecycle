"""
Модуль групп хуков.

Определяет базовую группу BaseGroup, а также группы AllGroup (выполняет все хуки)
и OneGroup (выполняет только один успешный хук). Содержит фабричную функцию create_group.

Группа управляет набором хуков, их порядком выполнения (топологическая сортировка),
состояниями и обработкой контекстов. AllGroup выполняет все хуки, OneGroup — только
первый успешный (или обязательный) и поддерживает переключение при отказах.

Пример:
    >>> from lifecycle import BaseExecutableHook, HookDependency, DependenceOrder, HookContext
    >>> class A(BaseExecutableHook):
    ...     name = "A"
    ...     def _do_init(self): return HookResult.SUCCESS
    >>> class B(BaseExecutableHook):
    ...     name = "B"
    ...     dependencies = (HookDependency("A", init_order=DependenceOrder.AFTER),)
    ...     def _do_init(self): return HookResult.SUCCESS
    >>> group = AllGroup("test", [A("A"), B("B")])
    >>> group.process(HookContext.INIT) == HookResult.SUCCESS
    True
"""

import heapq
import logging
from collections.abc import Callable, Iterable
from typing import ClassVar

from typeguard import typechecked

from .exceptions import (
    CircularDependencyError,
    GroupConfigurationError,
    HookExistsError,
    HookNameExistsError,
    InvalidStateError,
    LifeCycleError,
    LifeStateError,
    UnknownContextError,
    UnknownDependencyError,
    UnknownSelectionModeError,
)
from .hooks import ExecutableHook
from .lifecycle_types import (
    DependenceOrder,
    HookContext,
    HookDependency,
    HookRequirement,
    HookResult,
    LifeState,
    SelectionMode,
)

__all__ = ["AllGroup", "BaseGroup", "OneGroup", "create_group"]

logger = logging.getLogger(__name__)


class _OrderCache:
    """
    Кэш порядка выполнения хуков для различных контекстов.

    Предотвращает повторное вычисление топологической сортировки.
    Используется внутри BaseGroup для ускорения повторных вызовов process.
    """

    __slots__ = ("_error_order", "_init_order", "_quit_order", "_reset_order")

    def __init__(self) -> None:
        self._init_order: list[ExecutableHook] | None = None
        self._quit_order: list[ExecutableHook] | None = None
        self._error_order: list[ExecutableHook] | None = None
        self._reset_order: list[ExecutableHook] | None = None
        logger.debug("Инициализирован кэш порядка выполнения")

    @typechecked
    def get(
        self,
        context: HookContext,
        resolver: Callable[[HookContext, list[ExecutableHook]], list[ExecutableHook]],
        full_hooks: list[ExecutableHook],
    ) -> list[ExecutableHook]:
        """
        Возвращает упорядоченный список хуков для контекста, используя кэш.

        Args:
            context: Контекст выполнения.
            resolver: Функция для вычисления порядка, если нет в кэше.
            full_hooks: Список всех хуков.

        Returns:
            Упорядоченный список хуков.

        Raises:
            UnknownContextError: Если контекст неизвестен.
        """
        attr_map = {
            HookContext.INIT: "_init_order",
            HookContext.QUIT: "_quit_order",
            HookContext.ERROR: "_error_order",
            HookContext.RESET: "_reset_order",
        }
        attr = attr_map.get(context)
        if attr is None:
            raise UnknownContextError(f"Неизвестный контекст: {context}")

        cached = getattr(self, attr)
        if cached is None:
            logger.debug("Кэш для контекста %s не найден, вычисляем порядок", context.name)
            cached = resolver(context, full_hooks)
            setattr(self, attr, cached)
            logger.debug("Порядок для контекста %s: %s", context.name, [h.name for h in cached])
        else:
            logger.debug("Используем кэш для контекста %s", context.name)
        return cached  # type: ignore[no-any-return]

    def invalidate(self) -> None:
        """Сбрасывает кэш (вызывается при изменении состава хуков)."""
        self._init_order = None
        self._quit_order = None
        self._error_order = None
        self._reset_order = None
        logger.debug("Кэш порядка выполнения сброшен")


class BaseGroup:
    """
    Базовая группа хуков.

    Управляет набором хуков, поддерживает добавление/удаление,
    определяет порядок выполнения на основе зависимостей и требований.
    Для группы можно задать собственные зависимости и требование
    через атрибуты класса `dependencies` и `requirement`.

    Attributes:
        dependencies: Кортеж зависимостей группы (классовый атрибут).
        requirement: Требование группы (классовый атрибут).

    Example:
        >>> group = BaseGroup("my_group")
        >>> group.name
        'my_group'
        >>> len(group)
        0
    """

    dependencies: ClassVar[tuple[HookDependency, ...]] = ()
    requirement: ClassVar[HookRequirement] = HookRequirement.OPTIONAL

    _name: str
    _hooks: list[ExecutableHook]
    _hook_names: set[str]
    _state: LifeState
    _order_cache: _OrderCache

    __slots__ = ("_hook_names", "_hooks", "_name", "_order_cache", "_state")

    @typechecked
    def __init__(self, name: str, hooks: Iterable[ExecutableHook] = ()) -> None:
        """
        Инициализирует группу с именем и начальным набором хуков.

        Args:
            name: Уникальное имя группы.
            hooks: Итерируемый объект хуков для добавления.
        """
        self._name = name
        self._hooks = []
        self._hook_names = set()
        self._state = LifeState.NEW
        self._order_cache = _OrderCache()

        self.extend(*hooks)
        logger.info("Создана группа '%s' с %d хуками", name, len(self._hooks))

    @typechecked
    def extend(self, *hooks: ExecutableHook) -> None:
        """
        Добавляет один или несколько хуков в группу.

        Args:
            *hooks: Хуки для добавления.

        Raises:
            HookNameExistsError: Если хук с таким именем уже есть.
            HookExistsError: Если такой же хук уже добавлен.
            LifeStateError: Если группа не в состоянии NEW или STOPPED.
        """
        logger.debug("Добавление %d хуков в группу '%s'", len(hooks), self._name)
        for hook in hooks:
            self._add_hook(hook)
        self._order_cache.invalidate()
        logger.debug(
            "В группу '%s' добавлено %d хуков, всего хуков: %d",
            self._name,
            len(hooks),
            len(self._hooks),
        )

    def _add_hook(self, hook: ExecutableHook) -> None:
        """Внутренний метод добавления одного хука с проверками."""
        if self._state not in (LifeState.NEW, LifeState.STOPPED):
            raise LifeStateError(f"Невозможно добавить хук в состоянии {self._state}")

        if hook in self._hooks:
            raise HookExistsError(
                f"Хук {hook} уже существует в группе {self._name}",
            )

        if hook.name in self._hook_names:
            raise HookNameExistsError(
                f"Хук с именем '{hook.name}' уже существует в группе '{self._name}'",
            )

        self._hooks.append(hook)
        self._hook_names.add(hook.name)
        logger.debug("Хук '%s' добавлен в группу '%s'", hook.name, self._name)

    @typechecked
    def remove(self, hook: str | ExecutableHook) -> None:
        """
        Удаляет хук из группы по имени или по объекту.

        Args:
            hook: Имя хука или сам объект хука.

        Raises:
            ValueError: Если хук не найден.
            LifeStateError: Если группа не в состоянии NEW или STOPPED.
        """
        if self._state not in (LifeState.NEW, LifeState.STOPPED):
            raise LifeStateError(f"Невозможно удалить хук в состоянии {self._state}")

        if isinstance(hook, str):
            hook_name = hook
            target_hook = next((h for h in self._hooks if h.name == hook_name), None)
            if target_hook is None:
                raise ValueError(f"Хук с именем '{hook_name}' не найден в группе '{self._name}'")
        else:
            target_hook = hook
            hook_name = target_hook.name
            if target_hook not in self._hooks:
                raise ValueError(f"Хук {target_hook} не найден в группе '{self._name}'")

        self._hooks.remove(target_hook)
        self._hook_names.remove(hook_name)

        self._order_cache.invalidate()
        logger.info("Из группы '%s' удалён хук '%s'", self._name, hook_name)

    def _build_internal_graph(
        self,
        context: HookContext,
        hooks: list[ExecutableHook],
        strict: bool = True,
    ) -> tuple[dict[str, set[str]], dict[str, int], dict[str, ExecutableHook]]:
        """
        Строит граф зависимостей для указанного списка хуков.

        Args:
            context: Контекст, для которого запрашиваются зависимости.
            hooks: Список хуков.
            strict: Если True, при неизвестной зависимости выбрасывается ошибка.

        Returns:
            Кортеж (граф, словарь in_degree, словарь отображения имени на хук).

        Raises:
            UnknownDependencyError: Если зависимость указывает на неизвестный хук и strict=True.
        """
        logger.debug(
            "Построение графа зависимостей для контекста %s, строгий режим=%s",
            context.name,
            strict,
        )
        hook_by_name: dict[str, ExecutableHook] = {}
        graph: dict[str, set[str]] = {}
        in_degree: dict[str, int] = {}

        for hook in hooks:
            hook_by_name[hook.name] = hook
            graph[hook.name] = set()
            in_degree[hook.name] = 0

        for hook in hooks:
            for dep in hook.dependencies:
                if dep.name not in hook_by_name:
                    if strict:
                        raise UnknownDependencyError(
                            f"Хук '{hook.name}' зависит от неизвестного хука '{dep.name}'",
                        )
                    continue
                order = dep.get_order(context)
                if order == DependenceOrder.AFTER and hook.name not in graph[dep.name]:
                    graph[dep.name].add(hook.name)
                    in_degree[hook.name] += 1
                elif order == DependenceOrder.BEFORE and dep.name not in graph[hook.name]:
                    graph[hook.name].add(dep.name)
                    in_degree[dep.name] += 1
        return graph, in_degree, hook_by_name

    def _topological_sort_with_priority(
        self,
        graph: dict[str, set[str]],
        in_degree: dict[str, int],
        hook_by_name: dict[str, ExecutableHook],
    ) -> list[str]:
        """
        Топологическая сортировка с приоритетом для REQUIRED хуков.

        Args:
            graph: Граф зависимостей.
            in_degree: Словарь входящих степеней.
            hook_by_name: Отображение имени на хук.

        Returns:
            Список имён хуков в порядке выполнения.
        """
        heap: list[tuple[int, str]] = []
        for name, deg in in_degree.items():
            if deg == 0:
                priority = 0 if hook_by_name[name].requirement == HookRequirement.REQUIRED else 1
                heapq.heappush(heap, (priority, name))

        sorted_names: list[str] = []
        while heap:
            priority, name = heapq.heappop(heap)
            sorted_names.append(name)
            for neighbor in graph[name]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    neighbor_priority = (
                        0 if hook_by_name[neighbor].requirement == HookRequirement.REQUIRED else 1
                    )
                    heapq.heappush(heap, (neighbor_priority, neighbor))
        return sorted_names

    def _compute_order(
        self,
        context: HookContext,
        hooks: list[ExecutableHook],
        strict: bool = True,
    ) -> list[ExecutableHook]:
        """
        Вычисляет порядок выполнения хуков на основе зависимостей.

        Args:
            context: Контекст выполнения.
            hooks: Список хуков.
            strict: Флаг строгой проверки неизвестных зависимостей.

        Returns:
            Упорядоченный список хуков.

        Raises:
            CircularDependencyError: При обнаружении циклической зависимости.
        """
        logger.debug(
            "Вычисление порядка для контекста %s, количество хуков: %d",
            context.name,
            len(hooks),
        )
        if not hooks:
            return []
        graph, in_degree, hook_by_name = self._build_internal_graph(context, hooks, strict)
        sorted_names = self._topological_sort_with_priority(graph, in_degree, hook_by_name)
        if len(sorted_names) != len(hooks):
            raise CircularDependencyError(f"Циклическая зависимость в группе '{self.name}'")
        ordered = [hook_by_name[name] for name in sorted_names]
        logger.debug(
            "Порядок выполнения для контекста %s: %s",
            context.name,
            [h.name for h in ordered],
        )
        return ordered

    def _get_ordered_hooks(
        self,
        context: HookContext,
        *,
        hooks: list[ExecutableHook] | None = None,
    ) -> list[ExecutableHook]:
        """
        Возвращает упорядоченный список хуков, используя кэш при необходимости.

        Args:
            context: Контекст выполнения.
            hooks: Если указан, игнорирует кэш и вычисляет порядок для указанного подмножества.

        Returns:
            Упорядоченный список хуков.
        """
        target = hooks or self._hooks
        if hooks is None:
            return self._order_cache.get(context, self._compute_order, target)
        return self._compute_order(context, target, strict=False)

    def _process_hook_safe(self, hook: ExecutableHook, context: HookContext) -> HookResult:
        """
        Безопасно выполняет хук, перехватывая исключения.

        Args:
            hook: Хук для выполнения.
            context: Контекст.

        Returns:
            Результат выполнения с учётом требования хука.
        """
        try:
            result = hook.process(context)
            logger.debug(
                "Хук '%s' вернул %s для контекста %s",
                hook.name,
                result.name,
                context.name,
            )
        except LifeCycleError as e:
            logger.warning(
                "Хук '%s' выбросил LifeCycleError при обработке %s: %s",
                hook.name,
                context.name,
                e,
            )
            if hook.requirement == HookRequirement.REQUIRED:
                return HookResult.FATAL
            return HookResult.FAILURE
        except Exception as e:
            logger.exception(
                "Хук '%s' выбросил непредвиденное исключение при обработке %s: %s",
                hook.name,
                context.name,
                e,
            )
            return HookResult.FATAL

        if hook.requirement == HookRequirement.REQUIRED and result != HookResult.SUCCESS:
            logger.warning(
                "Обязательный хук '%s' вернул %s, что считается FATAL",
                hook.name,
                result.name,
            )
            return HookResult.FATAL
        return result

    @typechecked
    def process(self, context: HookContext) -> HookResult:
        """
        Обрабатывает контекст, запуская соответствующий жизненный цикл группы.

        Args:
            context: Контекст (INIT, QUIT, ERROR, RESET).

        Returns:
            Результат обработки.

        Raises:
            UnknownContextError: Если контекст неизвестен.
        """
        logger.info(
            "Группа '%s' обрабатывает контекст %s (состояние %s)",
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
        raise UnknownContextError(f"Неизвестный контекст: {context}")

    def _init(self) -> HookResult:
        """Внутренний обработчик INIT."""
        if self._state not in (LifeState.NEW, LifeState.STOPPED):
            raise InvalidStateError(f"Недопустимое состояние для инициализации: {self._state}")

        logger.info("Группа '%s' переходит в INITIALIZING", self._name)
        self._state = LifeState.INITIALIZING
        try:
            result = self._do_init()
        except CircularDependencyError as e:
            logger.error("Группа '%s' обнаружила циклическую зависимость: %s", self._name, e)
            raise
        except Exception as e:
            logger.exception("Группа '%s' выбросила исключение в _do_init: %s", self._name, e)
            self._state = LifeState.ERROR
            return HookResult.FATAL

        if result == HookResult.FATAL:
            self._state = LifeState.ERROR
            logger.error("Группа '%s' перешла в ERROR после INIT", self._name)
        else:
            self._state = LifeState.RUNNING
            logger.info("Группа '%s' перешла в RUNNING", self._name)
        return result

    def _quit(self) -> HookResult:
        """Внутренний обработчик QUIT."""
        if self._state != LifeState.RUNNING:
            raise InvalidStateError(f"Недопустимое состояние для завершения: {self._state}")

        logger.info("Группа '%s' переходит в STOPPING", self._name)
        self._state = LifeState.STOPPING
        try:
            result = self._do_quit()
        except CircularDependencyError as e:
            logger.error("Группа '%s' обнаружила циклическую зависимость в QUIT: %s", self._name, e)
            raise
        except Exception as e:
            logger.exception("Группа '%s' выбросила исключение в _do_quit: %s", self._name, e)
            self._state = LifeState.ERROR
            return HookResult.FATAL

        if result == HookResult.FATAL:
            self._state = LifeState.ERROR
            logger.error("Группа '%s' перешла в ERROR после QUIT", self._name)
        else:
            self._state = LifeState.STOPPED
            logger.info("Группа '%s' перешла в STOPPED", self._name)
        return result

    def _reset(self) -> HookResult:
        """Внутренний обработчик RESET."""
        if self._state not in (LifeState.RUNNING, LifeState.STOPPED, LifeState.ERROR):
            raise InvalidStateError(f"Недопустимое состояние для сброса: {self._state}")

        logger.info("Группа '%s' переходит в RESETTING", self._name)
        self._state = LifeState.RESETTING
        try:
            result = self._do_reset()
        except CircularDependencyError as e:
            logger.error(
                "Группа '%s' обнаружила циклическую зависимость в RESET: %s",
                self._name,
                e,
            )
            raise
        except Exception as e:
            logger.exception("Группа '%s' выбросила исключение в _do_reset: %s", self._name, e)
            self._state = LifeState.ERROR
            return HookResult.FATAL

        if result == HookResult.FATAL:
            self._state = LifeState.ERROR
            logger.error("Группа '%s' перешла в ERROR после RESET", self._name)
        else:
            self._state = LifeState.RUNNING
            logger.info("Группа '%s' вернулась в RUNNING после RESET", self._name)
        return result

    def _error(self) -> HookResult:
        """Внутренний обработчик ERROR."""
        if self._state not in (
            LifeState.INITIALIZING,
            LifeState.RUNNING,
            LifeState.STOPPING,
            LifeState.RESETTING,
        ):
            raise InvalidStateError(f"Недопустимое состояние для обработки ошибки: {self._state}")

        logger.warning(
            "Группа '%s' переходит в ERROR из состояния %s",
            self._name,
            self._state.name,
        )
        self._state = LifeState.ERROR
        try:
            return self._do_error()
        except CircularDependencyError as e:
            logger.error(
                "Группа '%s' обнаружила циклическую зависимость в ERROR: %s",
                self._name,
                e,
            )
            raise
        except Exception as e:
            logger.exception("Группа '%s' выбросила исключение в _do_error: %s", self._name, e)
            return HookResult.FATAL

    def _do_init(self) -> HookResult:
        """
        Реализация инициализации: выполняет хуки в порядке, определённом для INIT.

        Returns:
            HookResult.SUCCESS, если все хуки успешны;
            HookResult.FAILURE, если хотя бы один опциональный хук провалился;
            HookResult.FATAL, если обязательный хук провалился или возникло исключение.
        """
        ordered = self._get_ordered_hooks(HookContext.INIT)
        final_result = HookResult.SUCCESS
        initialized: list[ExecutableHook] = []

        for hook in ordered:
            res = self._process_hook_safe(hook, HookContext.INIT)
            if res == HookResult.SUCCESS:
                initialized.append(hook)
            elif res == HookResult.FAILURE:
                if final_result == HookResult.SUCCESS:
                    final_result = HookResult.FAILURE
                continue
            else:
                final_result = HookResult.FATAL
                break

        if final_result == HookResult.FATAL:
            logger.error(
                "Инициализация группы '%s' прервана из-за FATAL, выполняем "
                "QUIT для инициализированных хуков",
                self._name,
            )
            ordered_quit = self._get_ordered_hooks(HookContext.QUIT, hooks=initialized)
            for hook in ordered_quit:
                try:
                    hook.process(HookContext.QUIT)
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "При откате хука '%s' после FATAL произошла ошибка: %s",
                        hook.name,
                        e,
                    )
        return final_result

    def _do_quit(self) -> HookResult:
        """
        Реализация остановки: выполняет хуки в порядке, определённом для QUIT.

        Returns:
            HookResult.SUCCESS, если все хуки успешны;
            HookResult.FAILURE, если хотя бы один опциональный хук провалился;
            HookResult.FATAL, если обязательный хук провалился или возникло исключение.
        """
        ordered = self._get_ordered_hooks(HookContext.QUIT)
        final_result = HookResult.SUCCESS

        for hook in ordered:
            res = self._process_hook_safe(hook, HookContext.QUIT)
            if res == HookResult.FATAL:
                return HookResult.FATAL
            if res == HookResult.FAILURE and final_result == HookResult.SUCCESS:
                final_result = HookResult.FAILURE
        return final_result

    def _do_reset(self) -> HookResult:
        """
        Реализация сброса: выполняет хуки в порядке, определённом для RESET.

        Returns:
            HookResult.SUCCESS, если все хуки успешны;
            HookResult.FAILURE, если хотя бы один опциональный хук провалился;
            HookResult.FATAL, если обязательный хук провалился или возникло исключение.
        """
        ordered = self._get_ordered_hooks(HookContext.RESET)
        final_result = HookResult.SUCCESS
        processed: list[ExecutableHook] = []

        for hook in ordered:
            res = self._process_hook_safe(hook, HookContext.RESET)
            if res == HookResult.SUCCESS:
                processed.append(hook)
            elif res == HookResult.FAILURE:
                if final_result == HookResult.SUCCESS:
                    final_result = HookResult.FAILURE
                continue
            else:
                final_result = HookResult.FATAL
                break

        if final_result == HookResult.FATAL:
            logger.error(
                "Сброс группы '%s' прерван из-за FATAL, выполняем QUIT для обработанных хуков",
                self._name,
            )
            ordered_quit = self._get_ordered_hooks(HookContext.QUIT, hooks=processed)
            for hook in ordered_quit:
                try:
                    hook.process(HookContext.QUIT)
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "При откате хука '%s' после FATAL при сбросе произошла ошибка: %s",
                        hook.name,
                        e,
                    )
        return final_result

    def _do_error(self) -> HookResult:
        """
        Реализация обработки ошибки: выполняет хуки в порядке, определённом для ERROR.

        Returns:
            HookResult.SUCCESS, если все хуки успешны;
            HookResult.FAILURE, если хотя бы один опциональный хук провалился;
            HookResult.FATAL, если обязательный хук провалился или возникло исключение.
        """
        ordered = self._get_ordered_hooks(HookContext.ERROR)
        final_result = HookResult.SUCCESS

        for hook in ordered:
            res = self._process_hook_safe(hook, HookContext.ERROR)
            if res == HookResult.FATAL:
                return HookResult.FATAL
            if res == HookResult.FAILURE and final_result == HookResult.SUCCESS:
                final_result = HookResult.FAILURE
        return final_result

    @property
    def hooks(self) -> list[ExecutableHook]:
        """Возвращает копию списка хуков группы."""
        return self._hooks.copy()

    @typechecked
    def __contains__(self, hook: ExecutableHook) -> bool:
        return hook in self._hooks

    def __len__(self) -> int:
        return len(self._hooks)

    @property
    def state(self) -> LifeState:
        """Текущее состояние группы."""
        return self._state

    @property
    def name(self) -> str:
        """Имя группы."""
        return self._name


class AllGroup(BaseGroup):
    """
    Группа, выполняющая все содержащиеся хуки.

    Поведение полностью идентично BaseGroup. Используется как алиас для
    группы со стратегией ALL.

    Example:
        >>> group = AllGroup("all", [])
        >>> isinstance(group, BaseGroup)
        True
    """


class OneGroup(BaseGroup):
    """
    Группа, выполняющая только один хук (первый успешный или обязательный).

    Отличается от AllGroup тем, что в любой момент времени активен не более
    одного хука. При INIT/RESET/ERROR группа пытается найти работающий хук
    и активирует его. При QUIT останавливает активный хук, если он есть.

    Особенности:
        - Не может содержать более одного REQUIRED хука.
        - Внутригрупповые зависимости запрещены.

    Example:
        >>> from lifecycle import BaseExecutableHook, HookResult
        >>> class GoodHook(BaseExecutableHook):
        ...     def _do_init(self): return HookResult.SUCCESS
        >>> class BadHook(BaseExecutableHook):
        ...     def _do_init(self): return HookResult.FAILURE
        >>> group = OneGroup("one", [BadHook("bad"), GoodHook("good")])
        >>> group.process(HookContext.INIT) == HookResult.SUCCESS
        True
    """

    __slots__ = ("_active_hook", "_failed_hooks", "_validated")

    @typechecked
    def __init__(self, name: str, hooks: Iterable[ExecutableHook] = ()) -> None:
        super().__init__(name, hooks)
        self._failed_hooks: set[ExecutableHook] = set()
        self._active_hook: ExecutableHook | None = None
        self._validated = False
        logger.debug("Создана группа OneGroup '%s'", name)

    def _add_hook(self, hook: ExecutableHook) -> None:
        super()._add_hook(hook)
        self._validated = False
        logger.debug("OneGroup '%s': хук '%s' добавлен, валидация сброшена", self.name, hook.name)

    @typechecked
    def remove(self, hook: str | ExecutableHook) -> None:
        super().remove(hook)
        self._validated = False
        hook_name = hook if isinstance(hook, str) else hook.name
        logger.debug("OneGroup '%s': хук '%s' удалён, валидация сброшена", self.name, hook_name)

    def _validate_group(self) -> None:
        """Проверяет корректность конфигурации OneGroup."""
        if self._validated:
            return
        required = [h for h in self._hooks if h.requirement == HookRequirement.REQUIRED]
        if len(required) > 1:
            raise GroupConfigurationError(
                f"Группа '{self.name}' не может содержать более одного REQUIRED хука в OneGroup",
            )
        local_names = set(self._hook_names)
        for hook in self._hooks:
            for dep in hook.dependencies:
                if dep.name in local_names:
                    raise GroupConfigurationError(
                        f"Хук '{hook.name}' имеет внутригрупповую зависимость от '{dep.name}', "
                        f"что запрещено в OneGroup",
                    )
        self._validated = True
        logger.debug("Группа '%s' прошла валидацию OneGroup", self.name)

    def _try_hook(self, hook: ExecutableHook, context: HookContext) -> HookResult:
        """Пытается выполнить хук и при неудаче добавляет в _failed_hooks."""
        result = self._process_hook_safe(hook, context)
        if result != HookResult.SUCCESS:
            self._failed_hooks.add(hook)
            if hook is self._active_hook:
                self._active_hook = None
                logger.debug("Активный хук '%s' сброшен из-за неудачного выполнения", hook.name)
        return result

    def _find_working_hook(self) -> ExecutableHook | None:
        """Находит следующий подходящий хук для активации."""
        for hook in self._hooks:
            if hook.requirement == HookRequirement.REQUIRED and hook not in self._failed_hooks:
                return hook
        for hook in self._hooks:
            if hook.requirement == HookRequirement.OPTIONAL and hook not in self._failed_hooks:
                return hook
        return None

    def _handle_quit(self) -> HookResult:
        """Обработка QUIT: останавливает активный хук, если он есть."""
        if self._active_hook is None:
            return HookResult.SUCCESS
        logger.debug(
            "OneGroup '%s' останавливает активный хук '%s'",
            self.name,
            self._active_hook.name,
        )
        result = self._try_hook(self._active_hook, HookContext.QUIT)
        if result != HookResult.FATAL:
            self._active_hook = None
        return result

    def _handle_non_quit_result(self, res: HookResult) -> HookResult | None:
        """Обрабатывает результат выполнения не QUIT контекста."""
        if res == HookResult.SUCCESS:
            return HookResult.SUCCESS
        if res == HookResult.FATAL:
            return HookResult.FATAL
        self._active_hook = None
        return None

    def _try_active_hook(self, context: HookContext) -> HookResult | None:
        """Пытается выполнить текущий активный хук."""
        if self._active_hook is None or self._active_hook in self._failed_hooks:
            return None

        if context == HookContext.QUIT:
            return self._handle_quit()

        if self._active_hook.requirement == HookRequirement.OPTIONAL:
            required_alive = any(
                h.requirement == HookRequirement.REQUIRED and h not in self._failed_hooks
                for h in self._hooks
            )
            if required_alive:
                logger.debug(
                    "Деактивация OPTIONAL хука '%s' из-за наличия живого REQUIRED",
                    self._active_hook.name,
                )
                quit_result = self._try_hook(self._active_hook, HookContext.QUIT)
                self._active_hook = None
                if quit_result == HookResult.FATAL:
                    return HookResult.FATAL
                return None

        res = self._try_hook(self._active_hook, context)
        return self._handle_non_quit_result(res)

    def _try_candidate(self, candidate: ExecutableHook, context: HookContext) -> HookResult | None:
        """Пробует выполнить кандидата и при успехе делает его активным."""
        res = self._try_hook(candidate, context)
        if res == HookResult.SUCCESS:
            self._active_hook = candidate
            logger.info("OneGroup '%s' активировала хук '%s'", self.name, candidate.name)
            return HookResult.SUCCESS
        if res == HookResult.FATAL:
            return HookResult.FATAL
        return None

    def _execute_context(self, context: HookContext) -> HookResult:
        """Основная логика выполнения для OneGroup."""
        self._validate_group()
        if context == HookContext.QUIT:
            return self._handle_quit()

        for hook in self._hooks:
            if hook.requirement == HookRequirement.REQUIRED and hook not in self._failed_hooks:
                res = self._try_candidate(hook, context)
                if res is not None:
                    return res
                break

        if self._active_hook is not None:
            return HookResult.SUCCESS

        result = self._try_active_hook(context)
        if result is not None:
            return result

        while True:
            candidate = self._find_working_hook()
            if candidate is None:
                logger.error(
                    "В группе '%s' нет работающего хука для контекста %s",
                    self.name,
                    context.name,
                )
                raise GroupConfigurationError(
                    f"В группе '{self.name}' нет работающего хука для контекста {context.name}",
                )
            result = self._try_candidate(candidate, context)
            if result is not None:
                return result

    def _do_init(self) -> HookResult:
        """Реализация INIT для OneGroup."""
        if self._state == LifeState.STOPPED:
            self._active_hook = None
            self._failed_hooks.clear()
            logger.debug("OneGroup '%s' сбросила состояние при повторном INIT", self.name)

        try:
            result = self._execute_context(HookContext.INIT)
        except Exception as e:
            logger.exception("OneGroup '%s' выбросила исключение в _do_init: %s", self.name, e)
            return HookResult.FATAL

        if result == HookResult.FATAL and self._active_hook is not None:
            logger.warning(
                "OneGroup '%s' получила FATAL, останавливаем активный хук '%s'",
                self.name,
                self._active_hook.name,
            )
            self._try_hook(self._active_hook, HookContext.QUIT)
            self._active_hook = None
        return result

    def _do_quit(self) -> HookResult:
        """Реализация QUIT для OneGroup."""
        try:
            return self._execute_context(HookContext.QUIT)
        except Exception as e:
            logger.exception("OneGroup '%s' выбросила исключение в _do_quit: %s", self.name, e)
            return HookResult.FATAL

    def _do_reset(self) -> HookResult:
        """Реализация RESET для OneGroup."""
        old_active = self._active_hook
        if old_active is not None and old_active not in self._failed_hooks:
            logger.debug(
                "OneGroup '%s' перед сбросом останавливает хук '%s'",
                self.name,
                old_active.name,
            )
            quit_res = self._try_hook(old_active, HookContext.QUIT)
            if quit_res == HookResult.FATAL:
                return HookResult.FATAL

        self._active_hook = None
        self._failed_hooks.clear()
        logger.debug("OneGroup '%s' сбросила внутреннее состояние", self.name)

        try:
            result = self._execute_context(HookContext.RESET)
        except Exception as e:
            logger.exception("OneGroup '%s' выбросила исключение в _do_reset: %s", self.name, e)
            return HookResult.FATAL

        if result == HookResult.FATAL and self._active_hook is not None:
            logger.warning(
                "OneGroup '%s' получила FATAL при сбросе, останавливаем хук '%s'",
                self.name,
                self._active_hook.name,
            )
            self._try_hook(self._active_hook, HookContext.QUIT)
            self._active_hook = None
        return result

    def _do_error(self) -> HookResult:
        """Реализация ERROR для OneGroup."""
        try:
            return self._execute_context(HookContext.ERROR)
        except Exception as e:
            logger.exception("OneGroup '%s' выбросила исключение в _do_error: %s", self.name, e)
            return HookResult.FATAL


@typechecked
def create_group(
    group_type: SelectionMode,
    name: str,
    hooks: Iterable[ExecutableHook],
    requirement: HookRequirement = HookRequirement.OPTIONAL,
    dependencies: Iterable[HookDependency] = (),
) -> BaseGroup:
    """
    Фабричная функция для создания группы хуков.

    Args:
        group_type: Тип группы (ALL или ONE).
        name: Имя группы.
        hooks: Итерируемый объект хуков.
        requirement: Требование группы.
        dependencies: Зависимости группы.

    Returns:
        Экземпляр группы (AllGroup или OneGroup).

    Raises:
        UnknownSelectionModeError: Если передан неизвестный тип группы.

    Example:
        >>> from lifecycle import BaseExecutableHook
        >>> hook = BaseExecutableHook("test")
        >>> group = create_group(SelectionMode.ALL, "my_group", [hook])
        >>> group.name
        'my_group'
        >>> isinstance(group, AllGroup)
        True
    """
    logger.debug(
        "Создание группы: type=%s, name='%s', requirement=%s",
        group_type.name,
        name,
        requirement,
    )
    base_cls: type[BaseGroup]

    if group_type == SelectionMode.ALL:
        base_cls = AllGroup
    elif group_type == SelectionMode.ONE:
        base_cls = OneGroup
    else:
        raise UnknownSelectionModeError(f"Неизвестный тип группы: {group_type}")

    group_cls = type(
        f"_{group_type.name}",
        (base_cls,),
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
    logger.debug("Создана динамическая группа типа %s с именем '%s'", group_type.name, name)
    return group_cls(name, hooks)  # type: ignore[no-any-return]
