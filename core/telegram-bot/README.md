# DNK_Memory_HUB

Оркестратор для об'єднання AI-агентів, інструментів дослідження та бази знань.

## Основні компоненти

- **Telegram Bot**: Єдиний інтерфейс взаємодії.

- **Hermes Agent (Гєрич)**: Розумний помічник для керування базою знань.

- **Git Research**: Система пошуку та аналізу GitHub проектів.

- **Memory Manager**: Фоновий воркер для автоматичної обробки сирих даних.

## Як запустити

Для запуску на macOS використовуйте **uv**:

```bash
/opt/homebrew/bin/uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
python main.py

```

Детальніше дивіться у [INSTRUCTIONS.md](./INSTRUCTIONS.md).

## Структура

- `core/`: Логіка системи.

- `config/`: Конфігураційні файли та інструкції для агентів.

- `data/`: Дані (raw, wiki, storage).

- `main.py`: Точка входу.
