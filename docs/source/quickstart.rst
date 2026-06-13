Быстрый старт
=============

.. contents:: Содержание
   :local:
   :depth: 2

Создание простого хука
----------------------

Хук — это компонент, который может выполнять действия при событиях жизненного цикла.
Самый простой способ создать хук — использовать адаптер:

.. code-block:: python

   from lifecycle import LifeCycle, create_adapter, HookCallbacks, HookResult

   def on_init():
       print("Инициализация")
       return HookResult.SUCCESS

   def on_quit():
       print("Завершение")
       return HookResult.SUCCESS

   callbacks = HookCallbacks(init=on_init, quit=on_quit)
   hook = create_adapter("my_hook", callbacks)
   lc = LifeCycle(hooks=[hook])

   lc.initialize()   # вызовет init-колбэк
   lc.finalize()     # вызовет quit-колбэк

Создание хука через наследование
--------------------------------

Для более сложной логики наследуйтесь от :class:`~lifecycle.hooks.BaseExecutableHook`:

.. code-block:: python

   from lifecycle import BaseExecutableHook, HookResult

   class DatabaseHook(BaseExecutableHook):
       def __init__(self):
           super().__init__("db")
           self.connected = False

       def _do_init(self) -> HookResult:
           print("Подключаюсь к БД...")
           self.connected = True
           return HookResult.SUCCESS

       def _do_quit(self) -> HookResult:
           if self.connected:
               print("Отключаюсь от БД...")
               self.connected = False
           return HookResult.SUCCESS

   lc = LifeCycle(hooks=[DatabaseHook()])
   lc.initialize()
   lc.finalize()

Использование зависимостей
--------------------------

Зависимости управляют порядком выполнения:

.. code-block:: python

   from lifecycle import BaseExecutableHook, HookDependency, DependenceOrder, HookResult, LifeCycle

   class LoggerHook(BaseExecutableHook):
       def __init__(self, name: str):
           super().__init__(name)

       def _do_init(self) -> HookResult:
           print(f"{self.name}: init")
           return HookResult.SUCCESS

   class ApplicationHook(BaseExecutableHook):
       dependencies = (HookDependency("Logger", init_order=DependenceOrder.AFTER),)

       def __init__(self, name: str):
           super().__init__(name)

       def _do_init(self) -> HookResult:
           print(f"{self.name}: init after Logger")
           return HookResult.SUCCESS

   lc = LifeCycle(hooks=[LoggerHook("Logger"), ApplicationHook("App")])
   lc.initialize()  # Logger → App

Использование группы ONE
------------------------

Группа :class:`~lifecycle.groups.OneGroup` активирует только один хук (первый успешный или обязательный). Это удобно для fallback-механизмов:

.. code-block:: python

   from lifecycle import create_group, SelectionMode, BaseExecutableHook, HookResult, HookContext

   class PrimaryHook(BaseExecutableHook):
       def __init__(self):
           super().__init__("primary")
       def _do_init(self):
           print("Попытка основного подключения")
           return HookResult.FAILURE

   class BackupHook(BaseExecutableHook):
       def __init__(self):
           super().__init__("backup")
       def _do_init(self):
           print("Резервное подключение")
           return HookResult.SUCCESS

   group = create_group(SelectionMode.ONE, "connector", [PrimaryHook(), BackupHook()])
   group.process(HookContext.INIT)

Использование кастомных зависимостей в разных контекстах
--------------------------------------------------------

Зависимости можно задавать отдельно для каждого контекста:

.. code-block:: python

   from lifecycle import BaseExecutableHook, HookDependency, DependenceOrder, HookResult, LifeCycle

   class A(BaseExecutableHook):
       def __init__(self, name: str):
           super().__init__(name)
       def _do_init(self):
           print("A init")
           return HookResult.SUCCESS
       def _do_quit(self):
           print("A quit")
           return HookResult.SUCCESS

   class B(BaseExecutableHook):
       dependencies = (
           HookDependency(
               "A",
               init_order=DependenceOrder.AFTER,   # B после A при INIT
               quit_order=DependenceOrder.BEFORE,  # B до A при QUIT
           ),
       )
       def __init__(self, name: str):
           super().__init__(name)
       def _do_init(self):
           print("B init (after A)")
           return HookResult.SUCCESS
       def _do_quit(self):
           print("B quit (before A)")
           return HookResult.SUCCESS

   lc = LifeCycle(hooks=[A("A"), B("B")])
   lc.initialize()  # A init → B init
   lc.finalize()    # B quit → A quit

Обработка ошибок с ``FAILURE`` и ``FATAL``
-------------------------------------------

.. code-block:: python

   from lifecycle import LifeCycle, BaseExecutableHook, HookResult, HookRequirement

   class OptionalHook(BaseExecutableHook):
       requirement = HookRequirement.OPTIONAL
       def __init__(self, name: str):
           super().__init__(name)
       def _do_init(self):
           print("Опциональный хук, который падает")
           return HookResult.FAILURE

   class RequiredHook(BaseExecutableHook):
       requirement = HookRequirement.REQUIRED
       def __init__(self, name: str):
           super().__init__(name)
       def _do_init(self):
           print("Обязательный хук")
           return HookResult.SUCCESS

   lc = LifeCycle(hooks=[OptionalHook("opt"), RequiredHook("req")])
   success = lc.initialize()
   print(success)  # True (FAILURE не останавливает)
   print(lc.state.name)  # RUNNING

   # А если RequiredHook вернёт FATAL – состояние станет ERROR
   class FatalRequiredHook(BaseExecutableHook):
       requirement = HookRequirement.REQUIRED
       def __init__(self, name: str):
           super().__init__(name)
       def _do_init(self):
           print("Обязательный хук возвращает FATAL")
           return HookResult.FATAL

   lc2 = LifeCycle(hooks=[FatalRequiredHook("fatal")])
   success2 = lc2.initialize()
   print(success2)  # False
   print(lc2.state.name)  # ERROR