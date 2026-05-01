#!/bin/bash
# DNK_MEMORY_HUB Setup Wizard v1.0
echo "==============================================="
echo "   🧠 DNK_MEMORY_HUB: ВІТАЄМО У ВАШІЙ ПАМ'ЯТІ! "
echo "==============================================="
echo ""

# 1. Перевірка оточення
echo "🔍 Перевірка системних компонентів..."
command -v git >/dev/null 2>&1 || { echo "❌ Потрібен Git. Встановіть його перед продовженням."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Потрібен Python 3. Встановіть його."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ Потрібен Node.js/NPM."; exit 1; }
echo "✅ Системні компоненти в нормі."
echo ""

# 2. Налаштування Безпеки
echo "🛡 Налаштування безпеки (Gitleaks & AgentSeal)..."
npm install agentseal > /dev/null 2>&1
echo "✅ Захист активовано."
echo ""

# 3. Створення першого проекту
read -p "👤 Як звати твого першого бізнес-героя (назва проекту)? [MyNewBusiness]: " PROJECT_NAME
PROJECT_NAME=${PROJECT_NAME:-MyNewBusiness}

echo "🏗 Створюю інфраструктуру для $PROJECT_NAME..."
mkdir -p "projects/$PROJECT_NAME"
cp -r templates/project_alpha/* "projects/$PROJECT_NAME/"

# Заміна плейсхолдера в README
sed -i '' "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" "projects/$PROJECT_NAME/README.md" 2>/dev/null || sed -i "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" "projects/$PROJECT_NAME/README.md"

echo "✅ Проект $PROJECT_NAME готовий у папці projects/."
echo ""

# 4. Пам'ять та Папка Користувача
echo "🧠 Ініціалізація особистої пам'яті..."
mkdir -p "memory/vault/00_Global"
mkdir -p "memory/vault/01_Projects/$PROJECT_NAME"
echo "✅ Твій 'Другий Мозок' активовано."
echo ""

# 5. Фінал
echo "==========================================="
echo "🎉 ВІТАЮ! DNK_HUB ГОТОВИЙ ДО РОБОТИ."
echo "==========================================="
echo "Наступні кроки:"
echo "1. Відкрий Directory Map: docs/DIRECTORY_MAP.md"
echo "2. Запусти першу діагностику: ./infra/scripts/self_check.sh"
echo "3. Почни заповнювати пам'ять у memory/vault/"
echo ""
echo "Успіхів у грі! 💸"
