# Развертывание Transfer Bot с помощью Ansible

Этот документ описывает процесс автоматического развертывания Telegram бота на удаленном сервере с использованием Ansible.

## Предварительные требования

1. **Ansible** установлен на локальной машине:
   ```bash
   pip install ansible
   ```

2. **SSH доступ** к удаленному серверу с правами sudo

3. **Telegram Bot Token** от @BotFather

## Настройка

### 1. Настройка inventory

Отредактируйте файл `inventory.ini`:

```ini
[production]
# Замените на реальный IP или домен вашего сервера
192.168.1.100 ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/id_rsa

[production:vars]
ansible_python_interpreter=/usr/bin/python3
telegram_token=1234567890:AAABBBCCCDDDEEEFFFGGGHHHIIIJJJKKK
```

### 2. Настройка переменных окружения

В `inventory.ini` в секции `[production:vars]` можно задать дополнительные переменные:

- `telegram_token` - токен Telegram бота (обязательно)
- `database_url` - URL базы данных (по умолчанию SQLite)
- `waiting_list_check_interval` - интервал проверки листа ожидания в секундах (по умолчанию 300)
- `log_level` - уровень логирования (по умолчанию INFO)

## Развертывание

### Запуск развертывания

```bash
ansible-playbook deploy.yml
```

### Проверка статуса сервиса

После развертывания проверьте статус:

```bash
ansible production -m shell -a "systemctl status transfer-bot"
```

### Просмотр логов

```bash
ansible production -m shell -a "journalctl -u transfer-bot -f"
```

## Управление сервисом

На удаленном сервере можно управлять ботом через systemd:

```bash
# Запуск
sudo systemctl start transfer-bot

# Остановка
sudo systemctl stop transfer-bot

# Перезапуск
sudo systemctl restart transfer-bot

# Статус
sudo systemctl status transfer-bot

# Просмотр логов
sudo journalctl -u transfer-bot -f
```

## Структура развертывания

После развертывания на сервере будет создана следующая структура:

```
/opt/transfer-bot/
├── app.py                 # Главный файл приложения
├── venv/                  # Виртуальное окружение Python
├── requirements.txt       # Зависимости Python
├── .env                   # Переменные окружения
├── config/               # Конфигурация
├── database/             # База данных и миграции
├── handlers/             # Обработчики команд
├── models/               # Модели данных
├── services/             # Бизнес-логика
├── utils/                # Утилиты
└── transfer_bot.db       # База данных SQLite
```

Systemd unit файл располагается в `/etc/systemd/system/transfer-bot.service`.

## Безопасность

- Бот запускается от отдельного пользователя `transfer-bot`
- Применены ограничения безопасности systemd
- Файл `.env` имеет ограниченные права доступа (600)
- Используется виртуальное окружение Python

## Обновление

Для обновления бота просто запустите плейбук повторно:

```bash
ansible-playbook deploy.yml
```

Ansible автоматически:
- Синхронизирует новые файлы
- Обновит зависимости при необходимости
- Перезапустит сервис

## Отладка

### Проблемы с подключением

```bash
# Тест подключения
ansible production -m ping

# Проверка Python
ansible production -m setup -a "filter=ansible_python*"
```

### Проблемы с ботом

```bash
# Проверка процесса
ansible production -m shell -a "ps aux | grep python"

# Проверка портов (если используются)
ansible production -m shell -a "netstat -tlnp | grep python"

# Детальные логи
ansible production -m shell -a "journalctl -u transfer-bot --no-pager -n 50"
```
