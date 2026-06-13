Участие в разработке
====================

Благодарим за интерес к развитию ``lifecycle``!

Установка для разработки
------------------------

1. Клонируйте репозиторий:

   .. code-block:: bash

      git clone https://github.com/Romana8192/lifecycle.git
      cd lifecycle

2. Создайте виртуальное окружение и установите зависимости:

   .. code-block:: bash

      uv venv
      source .venv/bin/activate  # или .venv\Scripts\activate на Windows
      uv sync

3. Установите библиотеку в режиме редактирования:

   .. code-block:: bash

      uv pip install -e .

Запуск тестов
-------------

.. code-block:: bash

   uv run pytest

Запуск линтеров и проверки типов
--------------------------------

.. code-block:: bash

   uv run ruff check .
   uv run mypy src

Сборка документации
-------------------

.. code-block:: bash

   cd docs
   uv run sphinx-build -b html source build/html

Проверка примеров в документации
---------------------------------

Мы используем `doctest` Sphinx, чтобы убедиться, что примеры кода в документации работают:

.. code-block:: bash

   cd docs
   uv run sphinx-build -b doctest source build/doctest

Если какой-то пример не проходит, Sphinx выдаст ошибку с указанием файла и строки.

Проверка стиля кода
-------------------

Следуйте рекомендациям PEP 8, используйте ``ruff`` для автоматического форматирования.

Как предложить изменения
------------------------

1. Создайте форк репозитория.
2. Создайте ветку для вашей фичи: ``git checkout -b feature/amazing-feature``.
3. Внесите изменения, напишите тесты.
4. Обновите документацию.
5. Отправьте pull request в основную ветку ``main``.

Лицензия
--------

Проект распространяется под лицензией MIT.