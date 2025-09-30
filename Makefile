# Transfer Bot Makefile
# Удобные команды для разработки проекта

# Переменные
PYTHON := python
PIP := pip
PYTEST := pytest
VENV_DIR := .venv
PROJECT_NAME := transfer-bot

# Цвета для вывода
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
WHITE := \033[0;37m
RESET := \033[0m

.PHONY: help install install-dev install-test clean test test-unit test-integration test-cov lint format check-format check-imports run db-init build docs clean-pyc clean-build clean-test clean-all deploy deploy-check deploy-status deploy-logs deploy-restart

# Помощь (по умолчанию)
help:
	@echo "$(CYAN)Transfer Bot - Makefile команды$(RESET)"
	@echo ""
	@echo "$(YELLOW)Установка:$(RESET)"
	@echo "  $(GREEN)install$(RESET)          - Установить проект"
	@echo "  $(GREEN)install-dev$(RESET)      - Установить проект с dev зависимостями"
	@echo "  $(GREEN)install-test$(RESET)     - Установить проект с test зависимостями"
	@echo ""
	@echo "$(YELLOW)Тестирование:$(RESET)"
	@echo "  $(GREEN)test$(RESET)             - Запустить все тесты"
	@echo "  $(GREEN)test-unit$(RESET)        - Запустить только unit тесты"
	@echo "  $(GREEN)test-integration$(RESET) - Запустить только integration тесты"
	@echo "  $(GREEN)test-cov$(RESET)         - Запустить тесты с покрытием"
	@echo "  $(GREEN)test-html$(RESET)        - Запустить тесты с HTML отчетом"
	@echo ""
	@echo "$(YELLOW)Качество кода:$(RESET)"
	@echo "  $(GREEN)lint$(RESET)             - Проверить код линтерами"
	@echo "  $(GREEN)format$(RESET)           - Отформатировать код"
	@echo "  $(GREEN)check-format$(RESET)     - Проверить форматирование"
	@echo "  $(GREEN)check-imports$(RESET)    - Проверить сортировку импортов"
	@echo "  $(GREEN)check-types$(RESET)      - Проверить типы с mypy"
	@echo ""
	@echo "$(YELLOW)Запуск и база данных:$(RESET)"
	@echo "  $(GREEN)run$(RESET)              - Запустить бота"
	@echo "  $(GREEN)db-init$(RESET)          - Инициализировать базу данных"
	@echo ""
	@echo "$(YELLOW)Сборка и очистка:$(RESET)"
	@echo "  $(GREEN)build$(RESET)            - Собрать пакет"
	@echo "  $(GREEN)clean$(RESET)            - Очистить временные файлы"
	@echo "  $(GREEN)clean-all$(RESET)        - Полная очистка"
	@echo ""
	@echo "$(YELLOW)Разработка:$(RESET)"
	@echo "  $(GREEN)dev-setup$(RESET)        - Полная настройка среды разработки"
	@echo "  $(GREEN)check-all$(RESET)        - Запустить все проверки"
	@echo ""
	@echo "$(YELLOW)Развертывание:$(RESET)"
	@echo "  $(GREEN)deploy$(RESET)           - Развернуть бота на продакшене"
	@echo "  $(GREEN)deploy-check$(RESET)     - Проверить подключение к серверу"
	@echo "  $(GREEN)deploy-status$(RESET)    - Проверить статус бота на сервере"
	@echo "  $(GREEN)deploy-logs$(RESET)      - Показать логи бота с сервера"
	@echo "  $(GREEN)deploy-restart$(RESET)   - Перезапустить бота на сервере"

# Установка
install:
	@echo "$(BLUE)Установка проекта...$(RESET)"
	$(PIP) install -e .

install-dev:
	@echo "$(BLUE)Установка проекта с dev зависимостями...$(RESET)"
	$(PIP) install -e ".[dev]"

install-test:
	@echo "$(BLUE)Установка проекта с test зависимостями...$(RESET)"
	$(PIP) install -e ".[test]"

# Полная настройка среды разработки
dev-setup: install-dev db-init
	@echo "$(GREEN)✅ Среда разработки настроена!$(RESET)"
	@echo "$(YELLOW)Теперь можно запускать:$(RESET)"
	@echo "  make test    - для запуска тестов"
	@echo "  make run     - для запуска бота"
	@echo "  make help    - для просмотра всех команд"

# Тестирование
test:
	@echo "$(BLUE)Запуск всех тестов...$(RESET)"
	$(PYTEST) -v

test-unit:
	@echo "$(BLUE)Запуск unit тестов...$(RESET)"
	$(PYTEST) -v -m unit

test-integration:
	@echo "$(BLUE)Запуск integration тестов...$(RESET)"
	$(PYTEST) -v -m integration

test-cov:
	@echo "$(BLUE)Запуск тестов с покрытием...$(RESET)"
	$(PYTEST) --cov --cov-report=term-missing

test-html:
	@echo "$(BLUE)Запуск тестов с HTML отчетом...$(RESET)"
	$(PYTEST) --cov --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)HTML отчет создан в htmlcov/index.html$(RESET)"

test-fast:
	@echo "$(BLUE)Быстрый запуск тестов (без покрытия)...$(RESET)"
	$(PYTEST) -q --tb=line --no-cov

# Качество кода
lint:
	@echo "$(BLUE)Проверка кода линтерами...$(RESET)"
	@echo "$(YELLOW)Flake8...$(RESET)"
	-flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	@echo "$(YELLOW)Flake8 (все предупреждения)...$(RESET)"
	-flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics

format:
	@echo "$(BLUE)Форматирование кода...$(RESET)"
	@echo "$(YELLOW)Black...$(RESET)"
	black .
	@echo "$(YELLOW)isort...$(RESET)"
	isort .
	@echo "$(GREEN)✅ Код отформатирован!$(RESET)"

check-format:
	@echo "$(BLUE)Проверка форматирования...$(RESET)"
	black --check --diff .

check-imports:
	@echo "$(BLUE)Проверка сортировки импортов...$(RESET)"
	isort --check-only --diff .

check-types:
	@echo "$(BLUE)Проверка типов с mypy...$(RESET)"
	-mypy .

# Запуск всех проверок
check-all: check-format check-imports lint check-types test
	@echo "$(GREEN)✅ Все проверки завершены!$(RESET)"

# Запуск и база данных
run:
	@echo "$(BLUE)Запуск Transfer Bot...$(RESET)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ Файл .env не найден!$(RESET)"; \
		echo "$(YELLOW)Создайте файл .env с настройками:$(RESET)"; \
		echo "TELEGRAM_TOKEN=your_bot_token_here"; \
		echo "ADMIN_USERNAMES=admin1,admin2"; \
		echo "DB_PATH=transfer_bot.db"; \
		echo "WAITING_LIST_CHECK_INTERVAL=300"; \
		exit 1; \
	fi
	$(PYTHON) app.py

db-init:
	@echo "$(BLUE)Инициализация базы данных...$(RESET)"
	$(PYTHON) -c "from database.init_db import init_database; init_database()"
	@echo "$(GREEN)✅ База данных инициализирована!$(RESET)"

# Сборка
build:
	@echo "$(BLUE)Сборка пакета...$(RESET)"
	$(PYTHON) -m build
	@echo "$(GREEN)✅ Пакет собран в dist/$(RESET)"

# Очистка
clean-pyc:
	@echo "$(BLUE)Очистка .pyc файлов...$(RESET)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

clean-build:
	@echo "$(BLUE)Очистка build файлов...$(RESET)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

clean-test:
	@echo "$(BLUE)Очистка тестовых файлов...$(RESET)"
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -f temp_export_*.xlsx

clean-docs:
	@echo "$(BLUE)Очистка документации...$(RESET)"
	rm -rf docs/_build/

clean: clean-pyc clean-test
	@echo "$(GREEN)✅ Временные файлы очищены!$(RESET)"

clean-all: clean clean-build clean-docs
	@echo "$(GREEN)✅ Полная очистка завершена!$(RESET)"

# Информация о проекте
info:
	@echo "$(CYAN)Transfer Bot - Информация о проекте$(RESET)"
	@echo "$(YELLOW)Python версия:$(RESET) $$(python --version)"
	@echo "$(YELLOW)Pip версия:$(RESET) $$(pip --version)"
	@echo "$(YELLOW)Pytest версия:$(RESET) $$(pytest --version)"
	@echo "$(YELLOW)Установленные пакеты:$(RESET)"
	@pip list | grep -E "(transfer-bot|pytest|black|isort|flake8|mypy)"

# Быстрые команды для разработки
dev: format test-fast
	@echo "$(GREEN)✅ Быстрая проверка завершена!$(RESET)"

ci: check-all
	@echo "$(GREEN)✅ CI проверки завершены!$(RESET)"

# Команды для работы с git
git-hooks:
	@echo "$(BLUE)Установка git hooks...$(RESET)"
	@echo "#!/bin/sh" > .git/hooks/pre-commit
	@echo "make check-format check-imports lint" >> .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "$(GREEN)✅ Git hooks установлены!$(RESET)"

# Генерация requirements файлов
requirements:
	@echo "$(BLUE)Генерация requirements.txt...$(RESET)"
	pip freeze > requirements-freeze.txt
	@echo "$(GREEN)✅ requirements-freeze.txt создан!$(RESET)"

# Обновление зависимостей
update-deps:
	@echo "$(BLUE)Обновление зависимостей...$(RESET)"
	pip install --upgrade pip
	pip install --upgrade -e ".[dev]"
	@echo "$(GREEN)✅ Зависимости обновлены!$(RESET)"

# ===== КОМАНДЫ РАЗВЕРТЫВАНИЯ =====

# Проверка наличия ansible
check-ansible:
	@which ansible-playbook > /dev/null || (echo "$(RED)❌ Ansible не установлен! Установите: pip install ansible$(RESET)" && exit 1)

# Проверка подключения к серверу
deploy-check: check-ansible
	@echo "$(BLUE)Проверка подключения к серверу...$(RESET)"
	@if [ ! -f inventory.ini ]; then \
		echo "$(RED)❌ Файл inventory.ini не найден!$(RESET)"; \
		echo "$(YELLOW)Создайте inventory.ini с настройками сервера$(RESET)"; \
		exit 1; \
	fi
	ansible production -m ping
	@echo "$(GREEN)✅ Подключение к серверу работает!$(RESET)"

# Развертывание бота
deploy: check-ansible
	@echo "$(BLUE)Развертывание Transfer Bot на продакшене...$(RESET)"
	@if [ ! -f inventory.ini ]; then \
		echo "$(RED)❌ Файл inventory.ini не найден!$(RESET)"; \
		echo "$(YELLOW)Создайте inventory.ini с настройками сервера$(RESET)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)⚠️  Убедитесь, что в inventory.ini указан правильный telegram_token!$(RESET)"
	@read -p "Продолжить развертывание? (y/N): " confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]
	ansible-playbook deploy.yml
	@echo "$(GREEN)✅ Развертывание завершено!$(RESET)"
	@echo "$(YELLOW)Проверьте статус: make deploy-status$(RESET)"

# Быстрое развертывание без подтверждения
deploy-force: check-ansible
	@echo "$(BLUE)Быстрое развертывание без подтверждения...$(RESET)"
	ansible-playbook deploy.yml
	@echo "$(GREEN)✅ Развертывание завершено!$(RESET)"

# Проверка статуса бота на сервере
deploy-status: check-ansible
	@echo "$(BLUE)Проверка статуса Transfer Bot...$(RESET)"
	ansible production -m shell -a "systemctl status transfer-bot --no-pager -l"

# Просмотр логов бота
deploy-logs: check-ansible
	@echo "$(BLUE)Логи Transfer Bot (последние 50 строк)...$(RESET)"
	ansible production -m shell -a "journalctl -u transfer-bot --no-pager -n 50"

# Просмотр логов в реальном времени
deploy-logs-follow: check-ansible
	@echo "$(BLUE)Логи Transfer Bot в реальном времени...$(RESET)"
	@echo "$(YELLOW)Нажмите Ctrl+C для выхода$(RESET)"
	ansible production -m shell -a "journalctl -u transfer-bot -f"

# Перезапуск бота на сервере
deploy-restart: check-ansible
	@echo "$(BLUE)Перезапуск Transfer Bot...$(RESET)"
	ansible production -m shell -a "sudo systemctl restart transfer-bot"
	@echo "$(GREEN)✅ Бот перезапущен!$(RESET)"
	@sleep 2
	@make deploy-status

# Остановка бота на сервере
deploy-stop: check-ansible
	@echo "$(BLUE)Остановка Transfer Bot...$(RESET)"
	ansible production -m shell -a "sudo systemctl stop transfer-bot"
	@echo "$(YELLOW)⚠️  Бот остановлен$(RESET)"

# Запуск бота на сервере
deploy-start: check-ansible
	@echo "$(BLUE)Запуск Transfer Bot...$(RESET)"
	ansible production -m shell -a "sudo systemctl start transfer-bot"
	@echo "$(GREEN)✅ Бот запущен!$(RESET)"
	@sleep 2
	@make deploy-status

# Информация о развертывании
deploy-info: check-ansible
	@echo "$(CYAN)Transfer Bot - Информация о развертывании$(RESET)"
	@echo "$(YELLOW)Сервер:$(RESET)"
	ansible production -m setup -a "filter=ansible_fqdn,ansible_distribution*,ansible_python_version"
	@echo ""
	@echo "$(YELLOW)Процессы Python:$(RESET)"
	ansible production -m shell -a "ps aux | grep python | grep -v grep"
	@echo ""
	@echo "$(YELLOW)Место на диске:$(RESET)"
	ansible production -m shell -a "df -h /opt/transfer-bot"

# Полная диагностика
deploy-debug: deploy-info deploy-status deploy-logs

# Обновление только кода (без установки зависимостей)
deploy-code-only: check-ansible
	@echo "$(BLUE)Обновление только кода...$(RESET)"
	ansible-playbook deploy.yml --tags="sync,restart"
	@echo "$(GREEN)✅ Код обновлен!$(RESET)"

# Синхронизация файлов .env
deploy-sync-env: check-ansible
	@echo "$(BLUE)Синхронизация переменных окружения...$(RESET)"
	ansible-playbook deploy.yml --tags="env"
	@make deploy-restart
	@echo "$(GREEN)✅ Переменные окружения обновлены!$(RESET)"
