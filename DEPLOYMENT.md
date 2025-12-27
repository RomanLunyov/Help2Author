# 🚀 Развёртывание и эксплуатация бота Help2Author

## 📦 Системные требования

### Минимальные:
- **OS**: Windows 10/11, Linux, macOS
- **Python**: 3.10 или выше
- **RAM**: 256 MB
- **Disk**: 100 MB свободного места
- **Интернет**: стабильное подключение

### Рекомендуемые:
- **RAM**: 512 MB
- **Disk**: 500 MB (для логов и резервных копий)

## 🖥️ Локальное развёртывание (Windows)

### Вариант 1: Быстрый старт (рекомендуется)

```powershell
# 1. Клонируйте или скачайте проект
cd "c:\My telegram Bots\Help2Author"

# 2. Отредактируйте .env (скопируйте из .env.example)
notepad .env

# 3. Запустите скрипт
.\start_bot.ps1
```

### Вариант 2: Ручная установка

```powershell
# 1. Создайте виртуальное окружение
python -m venv venv

# 2. Активируйте
.\venv\Scripts\Activate.ps1

# 3. Установите зависимости
pip install -r requirements.txt

# 4. Настройте .env
Copy-Item .env.example .env
notepad .env

# 5. Запустите
python main.py
```

## 🔄 Автозапуск Windows

### Метод 1: Task Scheduler (планировщик задач)

1. Откройте "Планировщик заданий Windows"
2. Создайте базовую задачу:
   - **Имя**: Help2Author Bot
   - **Триггер**: При запуске компьютера
   - **Действие**: Запустить программу
   - **Программа**: `powershell.exe`
   - **Аргументы**: `-ExecutionPolicy Bypass -File "c:\My telegram Bots\Help2Author\start_bot.ps1"`
   - **Рабочая папка**: `c:\My telegram Bots\Help2Author`

3. Дополнительные настройки:
   - ✅ Запускать с наивысшими правами
   - ✅ Запускать для всех пользователей
   - ✅ Перезапускать при сбое (3 попытки, интервал 1 минута)

### Метод 2: Служба Windows (NSSM)

```powershell
# 1. Скачайте NSSM: https://nssm.cc/download
# 2. Распакуйте и откройте командную строку от администратора

cd "c:\path\to\nssm\win64"

# 3. Установите службу
.\nssm.exe install Help2AuthorBot

# 4. В открывшемся окне укажите:
# Path: C:\Python310\python.exe
# Startup directory: c:\My telegram Bots\Help2Author
# Arguments: main.py

# 5. Запустите службу
.\nssm.exe start Help2AuthorBot
```

## 🐧 Развёртывание на Linux

### Ubuntu/Debian

```bash
# 1. Обновите систему
sudo apt update && sudo apt upgrade -y

# 2. Установите Python и зависимости
sudo apt install python3.10 python3.10-venv python3-pip -y

# 3. Клонируйте проект
cd /opt
sudo git clone <your-repo> Help2Author
cd Help2Author

# 4. Создайте виртуальное окружение
python3.10 -m venv venv
source venv/bin/activate

# 5. Установите зависимости
pip install -r requirements.txt

# 6. Настройте .env
sudo nano .env
```

### Создание systemd службы

```bash
# 1. Создайте файл службы
sudo nano /etc/systemd/system/help2author.service
```

Содержимое:
```ini
[Unit]
Description=Help2Author Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/opt/Help2Author
Environment="PATH=/opt/Help2Author/venv/bin"
ExecStart=/opt/Help2Author/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 2. Активируйте службу
sudo systemctl daemon-reload
sudo systemctl enable help2author
sudo systemctl start help2author

# 3. Проверьте статус
sudo systemctl status help2author

# 4. Просмотр логов
sudo journalctl -u help2author -f
```

## ☁️ Облачное развёртывание

### VPS (Digital Ocean, AWS, Hetzner и др.)

**Минимальная конфигурация**:
- 1 vCPU
- 512 MB RAM
- 10 GB SSD
- Ubuntu 22.04 LTS

**Процесс**:
1. Подключитесь по SSH
2. Следуйте инструкциям для Linux выше
3. Настройте firewall (UFW)
4. Установите автообновления

```bash
# Firewall
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable

# Автообновления
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### Heroku (бесплатный вариант)

**Подготовка**:

1. Создайте `Procfile`:
```
worker: python main.py
```

2. Создайте `runtime.txt`:
```
python-3.10.12
```

3. Обновите `requirements.txt` (добавьте gunicorn если нужен веб-интерфейс)

4. Деплой:
```bash
heroku login
heroku create your-app-name
git push heroku main
heroku ps:scale worker=1
```

### PythonAnywhere

1. Создайте аккаунт на [pythonanywhere.com](https://www.pythonanywhere.com)
2. Загрузите файлы проекта
3. Создайте виртуальное окружение
4. Настройте "Always-on Task" для запуска main.py

## 🔐 Безопасность

### Обязательно:

1. **Защита .env**:
```bash
chmod 600 .env  # Linux
```

2. **Обновления**:
```bash
pip install --upgrade pip
pip install --upgrade -r requirements.txt
```

3. **Резервные копии БД**:
```bash
# Linux (cron)
0 3 * * * cp /opt/Help2Author/books_bot.db /backup/books_bot_$(date +\%Y\%m\%d).db
```

```powershell
# Windows (Task Scheduler)
Copy-Item "c:\My telegram Bots\Help2Author\books_bot.db" "c:\Backup\books_bot_$(Get-Date -Format 'yyyyMMdd').db"
```

4. **SSL/TLS** (для webhook-режима):
```bash
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com
```

## 📊 Мониторинг

### Логи

**Windows**:
```powershell
# Перенаправление в файл
python main.py >> bot.log 2>&1
```

**Linux**:
```bash
# Systemd автоматически логирует
sudo journalctl -u help2author -f

# Или в файл
python main.py >> bot.log 2>&1
```

### Мониторинг работы

```python
# Добавьте в main.py для веб-мониторинга
from aiohttp import web

async def health_check(request):
    return web.Response(text="OK")

app = web.Application()
app.router.add_get('/health', health_check)
# Запустите веб-сервер на отдельном порту
```

### Alerting (оповещения)

Добавьте в бота уведомления администратору:
- При критических ошибках
- При остановке бота
- Ежедневная статистика

## 🔄 Обновление бота

### Windows:
```powershell
# 1. Остановите бота (Ctrl+C)
# 2. Создайте резервную копию
Copy-Item books_bot.db books_bot.db.backup

# 3. Обновите код
git pull  # или скачайте новые файлы

# 4. Обновите зависимости
.\venv\Scripts\Activate.ps1
pip install --upgrade -r requirements.txt

# 5. Запустите бота
python main.py
```

### Linux:
```bash
# 1. Остановите службу
sudo systemctl stop help2author

# 2. Резервная копия
cp books_bot.db books_bot.db.backup

# 3. Обновите код
git pull

# 4. Обновите зависимости
source venv/bin/activate
pip install --upgrade -r requirements.txt

# 5. Запустите службу
sudo systemctl start help2author
```

## 🐛 Отладка

### Включение подробных логов:

```python
# В main.py измените:
logging.basicConfig(
    level=logging.DEBUG,  # было INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Тестирование локально:

```powershell
# Запустите в интерактивном режиме
python -i main.py
```

### Проверка БД:

```bash
# Установите sqlite3
sqlite3 books_bot.db

# Выполните запросы
SELECT * FROM users;
SELECT * FROM books;
.exit
```

## 📈 Масштабирование

### При росте числа пользователей:

1. **Перейдите на PostgreSQL**:
```python
# Замените в database.py
import asyncpg
# Используйте asyncpg вместо aiosqlite
```

2. **Используйте Redis для кэша**:
```python
from aiogram.fsm.storage.redis import RedisStorage
storage = RedisStorage.from_url('redis://localhost:6379')
```

3. **Разделите на микросервисы**:
- Отдельный бот для обработки
- Отдельный сервис для БД
- Отдельный планировщик

## ✅ Чеклист развёртывания

Production-готовность:

- [ ] .env настроен и защищён
- [ ] База данных инициализирована
- [ ] Бот тестирован локально
- [ ] Настроены автозапуск/служба
- [ ] Настроены резервные копии
- [ ] Настроен мониторинг/логирование
- [ ] Установлены обновления безопасности
- [ ] Документация изучена
- [ ] План восстановления после сбоя
- [ ] Контакты для поддержки

## 🆘 Поддержка

При проблемах:
1. Проверьте логи
2. Убедитесь в правильности .env
3. Проверьте доступность Telegram API
4. Создайте Issue с подробным описанием

---

**Успешного развёртывания! 🚀**
