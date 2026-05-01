# 🔱 DNK Git Research — Standalone Service

Цей проєкт налаштований як **автономний сервіс**, який може працювати незалежно від основного коду DNK OS.

## 🚀 Швидкий запуск

Найпростіший спосіб запустити сервіс — скористатися інтерактивним скриптом:

```bash
chmod +x start_service.sh
./start_service.sh

```

Цей скрипт автоматично:

1. Перевірить віртуальне середовище (.venv).

2. Встановить необхідні залежності.

3. Відкриє меню з основними функціями (Пошук, Аналіз, Декомпозиція, MCP).

## 🛠️ Використання як окремої програми (CLI)

Ви можете використовувати `main.py` напряму:

- **Пошук та аналіз:** `python main.py search "ai agents" --save`

- **Глибокий AI-аналіз:** `python main.py analyze --topic "rag systems"`

- **Декомпозиція задачі:** `python main.py decompose "build a shopify app with python"`

- **Статистика бази:** `python main.py library --stats`

## 🤖 Режим MCP сервера

Для інтеграції з іншими AI-агентами (Claude, Cursor, Antigravity) запустіть:

```bash
python main.py mcp

```

Це активує FastMCP сервер через stdio.

## 🐳 Запуск через Docker

Якщо ви хочете повної ізоляції:

```bash
docker build -t dnk-git-research .
docker run --env-file .env dnk-git-research search "vibe coding"

```

## 📂 Структура автономного сервісу

- `main.py`: Єдина точка входу для всіх команд.

- `config.yaml`: Глобальні налаштування (моделі, ваги, домени).

- `data/`: Локальна база даних (JSON бібліотека, звіти, плани).

- `mcp_server/`: Окремий інтерфейс для AI-кооперації.

---
**Status: STANDALONE SERVICE ACTIVE. 🔱🦾**
