#!/bin/bash
# DNK_HUB Service Distribution Builder v1.1
# Використання: ./make_distro.sh [SERVICE_NAME] [VERSION]
# Наприклад: ./make_distro.sh DNK_MEMORY_HUB v0.01

SERVICE_NAME=${1:-DNK_MEMORY_HUB}
VERSION=${2:-v0.01}
DIST_ROOT="projects/04-dnk-os/dist"
DIST_DIR="$DIST_ROOT/$SERVICE_NAME/$VERSION"

echo "📦 Починаю збірку сервісу: $SERVICE_NAME ($VERSION)..."

# 1. Очищення попередньої збірки
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# 2. Список директорій для копіювання (Ядро та Інструменти)
core_dirs=("core" "infra" "integrations" "docs" "templates" "plugin")

for dir in "${core_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "📂 Копіюю $dir..."
        cp -r "$dir" "$DIST_DIR/"
    fi
done

# 3. Копіювання кореневих файлів (без .env та приватної пам'яті)
root_files=("README.md" "DNK_HUB.code-workspace" "package.json" "LICENSE" "VERSION")
for file in "${root_files[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$DIST_DIR/"
    fi
done

# 4. Копіювання Showcase Project (04-dnk-os)
if [ -d "projects/04-dnk-os" ]; then
    echo "🌟 Копіюю Showcase Project: 04-dnk-os..."
    mkdir -p "$DIST_DIR/projects/04-dnk-os"
    cp -r projects/04-dnk-os/* "$DIST_DIR/projects/04-dnk-os/"
fi

# 5. Створення порожніх структур для Користувача
echo "🏗 Створення чистих структур для користувача..."
mkdir -p "$DIST_DIR/projects"
mkdir -p "$DIST_DIR/memory/vault/00_Global"
mkdir -p "$DIST_DIR/memory/vault/01_Projects"
mkdir -p "$DIST_DIR/data/reports"

# 5. Копіювання прикладу .env
if [ -f ".env.example" ]; then
    cp ".env.example" "$DIST_DIR/.env.example"
fi

# 6. Очищення від сміття (node_modules, pycache, dev-folders тощо в дистрибутиві)
echo "🧹 Очищення дистрибутиву від тимчасових та внутрішніх файлів..."
find "$DIST_DIR" -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null
find "$DIST_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find "$DIST_DIR" -name "dev" -type d -exec rm -rf {} + 2>/dev/null
find "$DIST_DIR" -name ".DS_Store" -type f -delete 2>/dev/null
# Видаляємо всі .env файли з секретами (залишаємо тільки .env.example)
find "$DIST_DIR" -name ".env" -type f -delete 2>/dev/null
find "$DIST_DIR" -name ".env.local" -type f -delete 2>/dev/null
find "$DIST_DIR" -name ".env.production" -type f -delete 2>/dev/null

echo ""
echo "=================================================="
echo "🎉 ЗБІРКА ЗАВЕРШЕНА!"
echo "📍 Шлях: $DIST_DIR"
echo "=================================================="
echo "Тепер ти можеш зазипувати цю папку і віддавати її."
echo ""
