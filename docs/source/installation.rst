Установка
=========

Библиотека ``lifecycle`` доступна в PyPI. Для установки используйте pip:

.. code-block:: bash

   pip install lifecycle

Или через uv (если вы используете uv):

.. code-block:: bash

   uv add lifecycle

Требования
----------

- Python 3.9 или выше
- typeguard (устанавливается автоматически)

Проверка установки
------------------

.. code-block:: python

   import lifecycle
   print(lifecycle.__version__)