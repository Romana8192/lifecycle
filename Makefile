.PHONY: help install install-dev sync upgrade test coverage docs docs-open clean clean-all lint format typecheck check pre-commit

GREEN  := \033[0;32m
RESET  := \033[0m

help:
	@echo "$(GREEN)Доступные команды:$(RESET)"
	@echo "  make install     - установка проекта через uv sync (создание .venv и установка зависимостей)"
	@echo "  make install-dev - установка проекта с зависимостями для разработки"
	@echo "  make sync        - синхронизация зависимостей (обновление .venv по pyproject.toml)"
	@echo "  make upgrade     - обновление всех зависимостей до последних версий"
	@echo "  make test        - запуск pytest с покрытием"
	@echo "  make coverage    - запустить тесты и открыть отчёт о покрытии в браузере"
	@echo "  make docs        - сборка HTML документации Sphinx"
	@echo "  make docs-open   - собрать документацию и открыть в браузере"
	@echo "  make lint        - проверить код через ruff"
	@echo "  make format      - автоформатирование кода через ruff"
	@echo "  make typecheck   - проверка типов через mypy"
	@echo "  make check       - запустить все проверки (lint, typecheck, test)"
	@echo "  make clean       - удаление временных файлов (__pycache__, .pytest_cache, .coverage и др.)"
	@echo "  make clean-all   - полная очистка (включая .venv, docs/build, htmlcov)"

install:
	uv sync --frozen --no-dev

install-dev: sync

sync:
	uv sync

upgrade:
	uv sync --upgrade

test:
	uv run pytest -v --cov=lifecycle --cov-report=term --cov-report=html

coverage: test
	@echo "$(GREEN)Открываю отчёт о покрытии...$(RESET)"
	start htmlcov/index.html   # Windows
	# для Linux/macOS используйте: xdg-open htmlcov/index.html

docs:
	@echo "$(GREEN)Сборка документации Sphinx...$(RESET)"
	cd docs && uv run sphinx-build -b html source build/html

docs-open: docs
	@echo "$(GREEN)Открываю документацию...$(RESET)"
	start docs/build/html/index.html   # Windows
	# для Linux/macOS: xdg-open docs/build/html/index.html

lint:
	uv run ruff check src/lifecycle tests

format:
	uv run ruff format src/lifecycle tests

typecheck:
	uv run mypy src/lifecycle

check: lint typecheck test
	@echo "$(GREEN)Все проверки пройдены успешно!$(RESET)"

pre-commit: check
	@echo "$(GREEN)Предварительная проверка перед коммитом завершена$(RESET)"

clean:
	@echo "$(GREEN)Очистка временных файлов...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/
	rm -rf .pytest_cache/
	@echo "$(GREEN)Готово.$(RESET)"

clean-all: clean
	@echo "$(GREEN)Полная очистка (удаление .venv, сборок документации, egg-info)...$(RESET)"
	rm -rf .venv/
	rm -rf docs/build/
	rm -rf src/lifecycle.egg-info/
	rm -rf src/lifecycle/__pycache__/
	rm -rf tests/__pycache__/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	@echo "$(GREEN)Готово.$(RESET)"