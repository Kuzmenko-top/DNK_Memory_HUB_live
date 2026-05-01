# 📖 Інструкції: DNK_MEMORY_HUB v0.01

## 🏁 Швидкий Старт (5 хвилин)

### 1. Клонувати репозиторій
```bash
git clone https://github.com/YOUR_USERNAME/DNK_MEMORY_HUB.git
cd DNK_MEMORY_HUB
```

### 2. Запустити Setup Wizard
```bash
./infra/wizard.sh
```
Wizard задасть тобі одне питання: "Як називається твій перший проект?" — і автоматично підготує всю структуру.

### 3. Налаштувати змінні середовища
```bash
cp .env.example .env
# Відкрий .env та заповни свої API-ключі
```

### 4. Перевірити систему
```bash
./infra/scripts/self_check.sh
```
Якщо всі чекбокси зелені — система готова до роботи.

---

## ⚙️ Налаштування Агентів

### Hermes (Головний Оркестратор)
Конфігурація знаходиться в `core/orchestrator/`. Відкрий `TEAM_REGISTRY.md`, щоб побачити всю команду агентів та їхні ролі.

### Підключення Obsidian
1. Встанови Obsidian MCP сервер (інструкції в `integrations/obsidian-mcp/README.md`).
2. Вкажи шлях до свого vault у `.env`.

### Підключення Qdrant
1. Запусти Qdrant локально: `docker run -p 6333:6333 qdrant/qdrant`
2. Або використовуй Qdrant Cloud (вкажи URL та ключ у `.env`).

---

## 📦 Збірка Комерційної Версії
Коли ти готовий до релізу нового сервісу:
```bash
./infra/make_distro.sh DNK_MEMORY_HUB v0.01
```
Готовий продукт буде у `projects/04-dnk-os/dist/DNK_MEMORY_HUB/v0.01/`.

---

## 🆘 Пошук Несправностей

| Проблема | Рішення |
|----------|---------|
| `self_check.sh` не запускається | `chmod +x infra/scripts/self_check.sh` |
| AgentSeal не знайдено | `npm install agentseal` |
| Qdrant не підключається | Перевір, чи запущений Docker |
