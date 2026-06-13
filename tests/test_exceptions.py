from lifecycle import exceptions as exc


def test_exception_hierarchy() -> None:
    assert issubclass(exc.LifeCycleConfigurationError, exc.LifeCycleError)
    assert issubclass(exc.GroupConfigurationError, exc.LifeCycleConfigurationError)
    assert issubclass(exc.HookExistsError, exc.LifeCycleConfigurationError)
    assert issubclass(exc.HookNameExistsError, exc.LifeCycleConfigurationError)
    assert issubclass(exc.UnknownSelectionModeError, exc.LifeCycleConfigurationError)
    assert issubclass(exc.LifeCycleDependencyError, exc.LifeCycleError)
    assert issubclass(exc.CircularDependencyError, exc.LifeCycleDependencyError)
    assert issubclass(exc.UnknownDependencyError, exc.LifeCycleDependencyError)
    assert issubclass(exc.LifeCycleStateError, exc.LifeCycleError)
    assert issubclass(exc.InvalidStateError, exc.LifeCycleStateError)
    assert issubclass(exc.LifeStateError, exc.LifeCycleStateError)
    assert issubclass(exc.LifeCycleRuntimeError, exc.LifeCycleError)
    assert issubclass(exc.UnknownContextError, exc.LifeCycleRuntimeError)


def test_exceptions_instantiable() -> None:
    e = exc.LifeCycleError("test")
    assert str(e) == "test"
    e2 = exc.CircularDependencyError("cycle")
    assert str(e2) == "cycle"
