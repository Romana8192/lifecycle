Иерархия исключений
===================

Все исключения библиотеки наследуются от :exc:`~lifecycle.exceptions.LifeCycleError` и содержат сообщения на русском языке.

.. graphviz::

   digraph exceptions {
       rankdir=LR;
       node [shape=box, style="rounded"];
       "LifeCycleError" [color=red];
       "LifeCycleError" -> "LifeCycleConfigurationError";
       "LifeCycleError" -> "LifeCycleDependencyError";
       "LifeCycleError" -> "LifeCycleStateError";
       "LifeCycleError" -> "LifeCycleRuntimeError";

       "LifeCycleConfigurationError" -> "GroupConfigurationError";
       "LifeCycleConfigurationError" -> "HookExistsError";
       "LifeCycleConfigurationError" -> "HookNameExistsError";
       "LifeCycleConfigurationError" -> "UnknownSelectionModeError";

       "LifeCycleDependencyError" -> "CircularDependencyError";
       "LifeCycleDependencyError" -> "UnknownDependencyError";

       "LifeCycleStateError" -> "InvalidStateError";
       "LifeCycleStateError" -> "LifeStateError";

       "LifeCycleRuntimeError" -> "UnknownContextError";
   }

Полный список и описание каждого исключения см. в разделе :doc:`exceptions`.