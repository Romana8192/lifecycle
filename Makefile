.PHONY: help install install-editable sync upgrade test coverage docs docs-open clean clean-all lint format typecheck check pre-commit

help:
	@echo "Доступные команды:"
	@echo "  make install          - обычная установка проекта через uv sync"
	@echo "  make install-editable - установка проекта в редактируемом режиме (editable)"
	@echo "  make sync             - синоним для install"
	@echo "  make upgrade          - обновление всех зависимостей"
	@echo "  make test             - запуск pytest с покрытием"
	@echo "  make coverage         - тесты + открыть отчёт о покрытии"
	@echo "  make docs             - сборка HTML документации Sphinx"
	@echo "  make docs-open        - собрать документацию и открыть в браузере"
	@echo "  make lint             - проверить код через ruff"
	@echo "  make format           - автоформатирование кода через ruff"
	@echo "  make typecheck        - проверка типов через mypy"
	@echo "  make check            - запустить все проверки (lint, typecheck, test)"
	@echo "  make clean            - удаление временных файлов"
	@echo "  make clean-all        - полная очистка (включая .venv, docs/build, htmlcov)"

install:
	uv sync

install-editable:
	uv sync --editable

upgrade:
	uv sync --upgrade

test:
	uv run pytest -v --cov=lifecycle --cov-report=term --cov-report=html

coverage: test
	@echo "Открываю отчёт о покрытии..."
	start htmlcov/index.html

docs:
	@echo "Сборка документации Sphinx..."
	cd docs && uv run sphinx-build -b html source build/html

docs-open: docs
	@echo "Открываю документацию..."
	start docs/build/html/index.html

lint:
	uv run ruff check src/lifecycle tests

format:
	uv run ruff format src/lifecycle tests

typecheck:
	uv run mypy src/lifecycle

check: lint typecheck test
	@echo "Все проверки пройдены успешно!"

clean:
	@echo "Очистка временных файлов..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/
	@echo "Готово."

clean-all: clean
	@echo "Полная очистка (удаление .venv, сборок документации, egg-info)..."
	rm -rf .venv/ docs/build/ src/lifecycle.egg-info/ src/lifecycle/__pycache__/ tests/__pycache__/ .mypy_cache/ .ruff_cache/
	@echo "Готово."