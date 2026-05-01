#!/bin/bash
# DNK_HUB → GitHub Publisher v1.0
# Збирає чистий дистрибутив та публікує його в окремий публічний репозиторій.
#
# Використання:
#   ./infra/publish.sh                          # публікує DNK_MEMORY_HUB v0.01
#   ./infra/publish.sh DNK_SMM_PLANER v0.01    # публікує інший сервіс

SERVICE_NAME=${1:-DNK_MEMORY_HUB}
VERSION=${2:-v0.01}
DIST_DIR="projects/04-dnk-os/dist/$SERVICE_NAME/$VERSION"
GITHUB_REPO=${3:-""}  # Передай URL репо або встанови нижче
DEFAULT_REPO="https://github.com/Kuzmenko-top/DNK_Memory_HUB_live.git"
TARGET_REPO=${GITHUB_REPO:-$DEFAULT_REPO}

echo "================================================"
echo "🚀 DNK_HUB Publisher: $SERVICE_NAME ($VERSION)"
echo "================================================"
echo ""

# 1. Збираємо чистий дистрибутив
echo "📦 Крок 1: Збираємо чистий дистрибутив..."
./infra/make_distro.sh "$SERVICE_NAME" "$VERSION"
echo ""

# 2. Швидка перевірка безпеки — тільки dist, без node_modules
echo "🛡 Крок 2: Перевірка секретів у дистрибутиві..."
SECRET_FOUND=$(grep -rE "(sk-[A-Za-z0-9]{30,}|AIza[A-Za-z0-9]{35}|ghp_[A-Za-z0-9]{36})" \
    "$DIST_DIR" \
    --exclude-dir=node_modules \
    --include="*.md" --include="*.yml" --include="*.yaml" --include="*.env" --include="*.sh" \
    -l 2>/dev/null)

if [ -n "$SECRET_FOUND" ]; then
    echo "❌ УВАГА! Знайдено потенційні секрети у файлах:"
    echo "$SECRET_FOUND"
    echo "Публікацію скасовано."
    exit 1
fi
echo "✅ Секретів не знайдено. Безпечно публікувати."
echo ""

# 3. Ініціалізація git у папці дистрибутиву
echo "📁 Крок 3: Підготовка git репозиторію..."
cd "$DIST_DIR" || { echo "❌ Папка дистрибутиву не знайдена."; exit 1; }

if [ ! -d ".git" ]; then
    git init
    git branch -M main
    git remote add origin "$TARGET_REPO"
    echo "✅ Новий git репозиторій ініціалізовано."
else
    echo "✅ Git репозиторій вже існує."
fi

# 4. Коміт та пуш
echo ""
echo "📤 Крок 4: Публікація на GitHub..."
git add .
git commit -m "🚀 Release: $SERVICE_NAME $VERSION — $(date '+%Y-%m-%d')"
git push -u origin main --force

echo ""
echo "================================================"
echo "🎉 ГОТОВО! $SERVICE_NAME $VERSION опубліковано."
echo "🔗 $TARGET_REPO"
echo "================================================"
