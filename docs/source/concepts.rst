Основные понятия
================

.. contents:: Содержание
   :local:
   :depth: 2

Хук (Hook)
----------

Базовый строительный блок. Имеет:

- Имя (уникальное)
- Состояние (``NEW``, ``INITIALIZING``, ``RUNNING``, ``STOPPING``, ``STOPPED``, ``ERROR``, ``RESETTING``)
- Требование (``REQUIRED`` или ``OPTIONAL``)
- Зависимости (определяют порядок выполнения)
- Методы ``_do_init``, ``_do_quit``, ``_do_error``, ``_do_reset``, которые переопределяются для пользовательской логики.

Группа (Group)
--------------

Контейнер для хуков. Бывает двух типов:

- ``AllGroup`` – выполняет **все** хуки (порядок определяется зависимостями).
- ``OneGroup`` – выполняет **один** хук (первый успешный или обязательный).

Группа сама является исполняемым хуком, поэтому группы можно вкладывать.

Жизненный цикл (LifeCycle)
--------------------------

Корневой объект, управляющий группой хуков. Поддерживает три основные операции:

- ``initialize()`` – переход из ``NEW`` в ``RUNNING``, выполнение хуков с контекстом ``INIT``.
- ``finalize()`` – переход из ``RUNNING`` в ``STOPPED``, выполнение хуков с контекстом ``QUIT``.
- ``reset()`` – сброс ошибок, повторная инициализация, контекст ``RESET``.

Состояния
---------

.. graphviz::

  digraph states {
      NEW -> INITIALIZING [label="initialize()"];
      INITIALIZING -> RUNNING [label="успех"];
      INITIALIZING -> ERROR [label="FATAL"];
      RUNNING -> STOPPING [label="finalize()"];
      STOPPING -> STOPPED [label="успех"];
      STOPPING -> ERROR [label="FATAL"];
      RUNNING -> RESETTING [label="reset()"];
      RESETTING -> RUNNING [label="успех"];
      RESETTING -> ERROR [label="FATAL"];
      ERROR -> RESETTING [label="reset()"];
      STOPPED -> RESETTING [label="reset()"];
  }

Переходы состояний
------------------

.. list-table::
   :header-rows: 1

   * - Текущее состояние
     - Операция
     - Новое состояние
   * - NEW
     - ``initialize()``
     - RUNNING (после INIT)
   * - NEW, STOPPED
     - ``reset()``
     - RUNNING (после RESET)
   * - RUNNING
     - ``finalize()``
     - STOPPED
   * - любой (кроме NEW)
     - ``reset()``
     - RUNNING
   * - INITIALIZING, RUNNING, STOPPING, RESETTING
     - (ошибка FATAL)
     - ERROR

Требования (Requirement)
------------------------

- ``REQUIRED`` – хук должен выполниться успешно; при ошибке весь жизненный цикл переходит в ``ERROR``.
- ``OPTIONAL`` – ошибка хука не прерывает выполнение, фиксируется как ``FAILURE``, но состояние остаётся ``RUNNING``.

Зависимости (Dependency)
------------------------

Описание отношения между двумя хуками для каждого контекста (``INIT``, ``QUIT``, ``ERROR``, ``RESET``). Возможные порядки:

- ``UNORDERED`` – порядок не важен.
- ``BEFORE`` – текущий хук выполняется **до** указанного.
- ``AFTER`` – текущий хук выполняется **после** указанного.