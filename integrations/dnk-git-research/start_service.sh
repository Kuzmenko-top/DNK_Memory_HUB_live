#!/bin/bash

# DNK Git Research Service Launcher
# Цей скрипт запускає сервіс як автономну програму

# Кольори
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}🔱 DNK Git Research — Ініціалізація сервісу...${NC}"

# Перевірка віртуального середовища
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️ Віртуальне середовище .venv не знайдено. Створюю...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Перевірка .env
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Файл .env не знайдено!${NC}"
    echo -e "Будь ласка, створіть .env на основі прикладу та додайте GITHUB_TOKEN та GEMINI_API_KEY."
    exit 1
fi

# Головне меню
show_menu() {
    echo -e "\n${GREEN}=== DNK Git Research Service ===${NC}"
    echo -e "1) 🔍 Пошук репозиторіїв (Search)"
    echo -e "2) 🤖 Глибокий аналіз теми (Analyze)"
    echo -e "3) 📚 Огляд бібліотеки (Library Stats)"
    echo -e "4) 🔎 Пошук у локальній базі (Find)"
    echo -e "5) 🧩 Декомпозиція задачі (Decompose)"
    echo -e "6) 🚀 Запуск MCP сервера (для AI-агентів)"
    echo -e "7) 🧬 Гігієна даних (Harmonize)"
    echo -e "q) Вихід"
    echo -n "Виберіть опцію: "
}

while true; do
    show_menu
    read opt
    case $opt in
        1)
            echo -n "Введіть запит для пошуку: "
            read query
            python3 main.py search "$query" --save
            ;;
        2)
            echo -n "Введіть тему для AI-аналізу: "
            read topic
            python3 main.py analyze --topic "$topic"
            ;;
        3)
            python3 main.py library --stats
            ;;
        4)
            echo -n "Що шукаємо в локальній базі? "
            read query
            python3 main.py find "$query"
            ;;
        5)
            echo -n "Опишіть задачу для декомпозиції: "
            read task
            python3 main.py decompose "$task"
            ;;
        6)
            echo -e "${YELLOW}Запуск MCP сервера (Stdio mode)...${NC}"
            python3 main.py mcp
            ;;
        7)
            python3 main.py harmonize
            ;;
        q)
            echo -e "${GREEN}До побачення! 🔱${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Невірна опція${NC}"
            ;;
    esac
done
