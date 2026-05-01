# 🛠 Технічна інструкція (Installation & Setup)

Цей документ описує процес розгортання `dnk-git-research` у вашому робочому середовищі.

## 1. Системні вимоги

- **Python**: 3.12 або новіша версія.
- **Git**: Встановлений у системі.
- **OS**: macOS (рекомендовано) або Linux.

## 2. Розгортання оточення

1. Перейдіть у папку інтеграції:

   ```bash
   cd integrations/dnk-git-research
   ```
2. Створіть та активуйте віртуальне середовище:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Встановіть залежності:

   ```bash
   pip install -r requirements.txt
   ```

## 3. Налаштування змінних оточення

Створіть файл `.env` у корені папки інтеграції на основі `.env.example`:

```ini
GITHUB_TOKEN=ваш_токен_github
GEMINI_API_KEY=ваш_ключ_google_gemini
QDRANT_URL=http://localhost:6333
GOOGLE_CLOUD_PROJECT=dnk-ai-agent
```

- **GITHUB_TOKEN**: Потрібен для доступу до API GitHub (створіть Fine-grained PAT з доступом до читання репозиторіїв).
- **GEMINI_API_KEY**: Потрібен для AI-аналізу (використовується модель gemini-2.0-flash).
- **QDRANT_URL**: Адреса вашої векторної бази даних (за замовчуванням локальна).

## 4. Запуск інфраструктури (Qdrant)

Система використовує Qdrant для семантичного пошуку. Якщо він не запущений, ви можете запустити його через Docker:

```bash
docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
```

## 5. Перевірка працездатності

Запустіть команду перевірки статистики:

```bash
python main.py library --stats
```
Якщо ви бачите таблицю з кількістю репозиторіїв — система налаштована вірно.
