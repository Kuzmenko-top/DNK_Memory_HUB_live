# Telegram Bridge

Bridge між Telegram-Геричем і Claude Code.

## Концепт

Maks надсилає повідомлення в Telegram → bot передає Геричу → Герич делегує → відповідь назад у Telegram.

## TODO

- Вибрати підхід: Telegram Bot API + webhook або MCP

- Налаштувати bot token у `.env`

- Визначити формат команд (/ask, /delegate, /status)
