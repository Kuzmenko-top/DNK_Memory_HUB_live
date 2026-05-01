# DNK Git Research — Сервіс Пошуку та Аналізу

## Опис проєкту

Сервіс для автоматизованого пошуку, аналізу та фільтрації GitHub-репозиторіїв, що відповідають філософії VibeCoding та потребам бізнесу DNK OS.

## Стек технологій

- **Language**: Python 3.12+
- **GitHub API**: PyGithub
- **AI Engine**: Google Gemini (gemini-2.0-flash)
- **Vector DB**: Qdrant
- **CLI Framework**: Typer, Rich

## Структура папок

- `src/`: Основний код (analyzer, orchestrator, search, ranker).
- `data/`: База проаналізованих репозиторіїв та звіти.
- `scripts/`: Утиліти для синхронізації та бекапу.
- `core/`: Фундаментальна логіка та промпти.

## Конвенції коду

- **Naming**: `snake_case` для функцій та змінних, `PascalCase` для класів.
- **Type Hinting**: Обов'язкове використання типів для всіх функцій.
- **Logging**: Використовувати `loguru` замість `print`.
- **JSON**: AI аналізатор повинен повертати тільки чистий JSON.

## Команди

- `python main.py search "topic" --save`: Пошук та збереження в бібліотеку.
- `python main.py analyze --topic "topic"`: Повний AI-аналіз.
- `python main.py library --stats`: Перегляд статистики бібліотеки.
- `python main.py harmonize`: Запуск гігієни даних (IDs, MD format).
- `python main.py decompose "task"`: Декомпозиція задачі на кроки на основі репозиторіїв.

---
**Status: PROTOCOLS ACTIVE. 🔱🚀**
