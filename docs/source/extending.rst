Расширение библиотеки
=====================

.. contents:: Содержание
   :local:
   :depth: 2

Создание собственных хуков
--------------------------

Унаследуйтесь от :class:`~lifecycle.hooks.BaseExecutableHook` и переопределите нужные методы:

.. code-block:: python

   from lifecycle import BaseExecutableHook, HookResult, HookContext

   class MyCustomHook(BaseExecutableHook):
       requirement = HookRequirement.REQUIRED

       def _do_init(self) -> HookResult:
           # ваша логика
           return HookResult.SUCCESS

       def _do_quit(self) -> HookResult:
           # очистка
           return HookResult.SUCCESS

Создание собственной группы
---------------------------

Если стандартных групп (:class:`~lifecycle.groups.AllGroup`, :class:`~lifecycle.groups.OneGroup`) недостаточно, вы можете создать свою, унаследовавшись от :class:`~lifecycle.groups.BaseGroup`. Переопределите методы ``_do_init``, ``_do_quit``, ``_do_error``, ``_do_reset``. Учтите, что группа должна вызывать ``process`` у своих хуков с нужным контекстом.

Пример группы, которая выполняет хуки в случайном порядке:

.. code-block:: python

   import random
   from lifecycle import BaseGroup, HookResult, HookContext

   class RandomGroup(BaseGroup):
       def _do_init(self) -> HookResult:
           hooks = self._get_ordered_hooks(HookContext.INIT)
           random.shuffle(hooks)
           for hook in hooks:
               res = hook.process(HookContext.INIT)
               if res == HookResult.FATAL:
                   return HookResult.FATAL
           return HookResult.SUCCESS

       # аналогично для _do_quit и др.

Регистрация зависимостей
------------------------

Зависимости задаются как атрибут класса ``dependencies``. Используйте :class:`~lifecycle.lifecycle_types.HookDependency` для описания отношений в разных контекстах.

.. code-block:: python

   from lifecycle import BaseExecutableHook, HookDependency, DependenceOrder

   class ConfigHook(BaseExecutableHook):
       ...

   class AppHook(BaseExecutableHook):
       dependencies = (
           HookDependency("Config", init_order=DependenceOrder.AFTER,
                                    quit_order=DependenceOrder.BEFORE),
       )