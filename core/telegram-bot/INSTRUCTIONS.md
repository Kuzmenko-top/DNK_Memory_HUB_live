# DNK_Memory_HUB: Робочі інструкції

## Технічне середовище (Environment)

### Python & Package Management

На macOS використовується **uv** для управління середовищем, що дозволяє уникнути системних запитів Xcode:

- **Шлях до uv:** `/opt/homebrew/bin/uv`

- **Створення середовища:** `/opt/homebrew/bin/uv venv .venv`

- **Активація:** `source .venv/bin/activate`

- **Встановлення залежностей:** `/opt/homebrew/bin/uv pip install -r requirements.txt`

Для прямого запуску без venv (якщо потрібно):

- **Шлях до Python 3.13:** `/opt/homebrew/bin/python3.13`

### Змінні середовища

Всі ключі мають бути у файлі `config/.env`.

---

## Процедури (SOP)

1. **Додавання нових модулів:**
   - Код сторонніх проектів копіюється в `core/<module_name>/`.
   - Всі `import` всередині модуля мають бути перевірені на сумісність з кореневою структурою HUB.
   - Залежності додаються в загальний `requirements.txt`.

2. **Інтеграція Hermes Agent:**
   - Використовувати `core/agent_runner/hermes_wrapper.py`.
   - Обов'язково вказувати `HERMES_HOME` перед ініціалізацією.

3. **Git Research:**
   - Команда `/search` у боті використовує `core/research_tools/git_core/`.
