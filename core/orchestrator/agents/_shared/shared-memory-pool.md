# Shared Memory Pool

Інсайти, промовіщені з агентів у спільний пул. Доступні для читання всіма агентами.

## Що сюди потрапляє

Тільки те, що підтвердив Герич-Бібліотекар через `promote_to_shared()`:

- Крос-проєктні патерни (корисні > 1 проєкту)

- Технологічні рішення з обґрунтуванням

- Уроки з помилок (знеособлені)

## Що сюди НЕ потрапляє

- Клієнтські дані (залишаються у project-scope колекції)

- Тимчасові нотатки

- Недоперевірені інсайти

## Формат запису

```yaml
id: <uuid>
date: YYYY-MM-DD
source_agent: <agent_id>
confirmed_by: herich-librarian
scope_origin: <reburn|shopify|dnk-e|dnk-os|craft-os>
insight: |
  <текст інсайту>
tags: [<tag1>, <tag2>]
agent_version: 0.1.0

```

## Qdrant колекція: `shared_memory_pool`
