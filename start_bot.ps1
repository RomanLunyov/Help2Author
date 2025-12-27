# Скрипт запуска бота Help2Author

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Help2Author Bot - Starting..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Переход в директорию проекта
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Проверка наличия .env файла
if (-not (Test-Path ".env")) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host ""
    Write-Host "Please edit .env file and add your configuration:" -ForegroundColor Red
    Write-Host "   - BOT_TOKEN" -ForegroundColor Red
    Write-Host "   - ADMIN_ID" -ForegroundColor Red
    Write-Host "   - Other settings" -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter after editing .env file to continue"
}

# Проверка виртуального окружения
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & ".\venv\Scripts\Activate.ps1"
} else {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host ""
Write-Host "Starting bot..." -ForegroundColor Green
Write-Host ""

# Запуск бота
python main.py

Write-Host ""
Write-Host "Bot stopped." -ForegroundColor Yellow
