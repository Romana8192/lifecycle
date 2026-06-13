Документация lifecycle
======================

.. raw:: html

   <div style="float: right; margin-top: -20px;">
     <a href="https://github.com/Romana8192/lifecycle">
       <img src="https://img.shields.io/badge/GitHub-Repository-black?logo=github" alt="GitHub">
     </a>
   </div>

Библиотека для управления жизненным циклом приложения.

.. code-block:: python

   from lifecycle import LifeCycle, create_adapter, HookCallbacks, HookResult

   callbacks = HookCallbacks(init=lambda: HookResult.SUCCESS)
   hook = create_adapter("my_hook", callbacks)
   lc = LifeCycle(hooks=[hook])
   lc.initialize()
   lc.finalize()

.. toctree::
   :maxdepth: 2
   :caption: Руководство пользователя

   installation
   quickstart
   concepts
   exceptions_diagram
   faq

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api

.. toctree::
   :maxdepth: 2
   :caption: Для разработчиков

   extending
   contributing

Индексы
=======

* :ref:`genindex`
* :ref:`search`