# Audit Log

Логи делегувань: Maks → Герич → агенти.

## Формат файлів

Один файл на день: `YYYY-MM-DD.md`

## Формат запису

```markdown

## HH:MM — [event_type]

- from: <maks|herich-librarian|...>

- to: <agent_id>

- task: <короткий опис>

- result: <pending|done|escalated>

- duration: <секунди, якщо відомо>

```

## Приклад

```markdown

## 14:32 — delegation

- from: maks

- to: herich-librarian

- task: "Зроби аудит теми serdenko-store"

- result: done

## 14:32 — delegation

- from: herich-librarian

- to: shopify-pro

- task: "audit serdenko-store theme — performance + UX"

- result: done

```
