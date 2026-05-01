---
name: knowledge-capture
description: >
  Зберігає знання, факти і посилання в базу знань.
  Записує в Obsidian vault + індексує в Qdrant для семантичного пошуку
  + зберігає як Mem0 fact для швидкого доступу агента.
tags: [knowledge, obsidian, qdrant, mem0]
---

# Knowledge Capture Skill

## Коли використовувати

- Повідомлення містить посилання (http/https)

- Є слова "запам'ятай", "факт", "стаття", "дослідження"

- Це корисна інформація яку треба зберегти для майбутнього пошуку

## Алгоритм

### 1. Визнач категорію

- **tech** — технології, код, інструменти, API

- **business** — бізнес, ринок, клієнти, продукт

- **people** — люди, контакти, компанії

- **processes** — SOP, процеси, чеклисти

### 2. Визнач тему

Коротка назва (1-3 слова) для назви файлу і розділу.
Приклад: "qdrant-tips", "pricing-strategy", "competitor-analysis"

### 3. Збережи в Obsidian (через obsidian MCP)

```

Файл: knowledge/{категорія}/{тема}.md

Якщо файл не існує — створити з заголовком:

# {Тема}

Дописати в кінець:

## {YYYY-MM-DD HH:MM}

{Текст знання}
> Джерело: {посилання або "telegram"}

```

### 4. Індексуй в Qdrant (через mcp-server-qdrant)

```

store_memory(
  content="{текст знання}",
  metadata={
    "source": "telegram",
    "category": "{категорія}",
    "topic": "{тема}",
    "date": "{дата}"
  }
)

```

### 5. Збережи в Mem0 як atomic fact

```

mem0_add: "{ключовий факт у одному реченні}"

```

### 6. Відповідь у Telegram

```

📚 Збережено в базі знань

📂 knowledge/{категорія}/{тема}
🔍 Доступно через семантичний пошук

Запитай: "Що ти знаєш про {тема}?"

```

## Приклади

**Вхід:** "https://qdrant.tech/blog/sparse-vectors — про sparse vectors в qdrant"

- Категорія: tech

- Тема: qdrant-vectors

- Файл: knowledge/tech/qdrant-vectors.md

**Вхід:** "Запам'ятай: competitor X підняв ціни на 20% цього місяця"

- Категорія: business

- Тема: competitor-pricing

- Файл: knowledge/business/competitor-pricing.md

**Вхід:** "Олег Петренко — CTO в компанії Y, експерт з ML"

- Категорія: people

- Тема: oleg-petrenko

- Файл: knowledge/people/oleg-petrenko.md
