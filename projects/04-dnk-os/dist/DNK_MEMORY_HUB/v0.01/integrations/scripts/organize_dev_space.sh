#!/bin/bash

# Шлях до нового простору
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECTS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEV_SPACE="$PROJECTS_ROOT/DEV_Pack_Space"
HOME_DIR="$HOME"

echo "🚀 Починаємо організацію DEV_Pack_Space..."

# Створення підпапок
mkdir -p "$DEV_SPACE/npm_cache"
mkdir -p "$DEV_SPACE/bun_cache"
mkdir -p "$DEV_SPACE/python_pip"
mkdir -p "$DEV_SPACE/ai_models"
mkdir -p "$DEV_SPACE/tool_configs"

# Функція для безпечного переносу та створення лінку
move_and_link() {
    local src="$1"
    local dest="$2"
    local name="$3"

    if [ -d "$src" ] && [ ! -L "$src" ]; then
        echo "📦 Переносимо $name..."
        cp -R "$src/." "$dest/"
        rm -rf "$src"
        ln -s "$dest" "$src"
        echo "✅ $name перенесено та підключено через symlink."
    elif [ -L "$src" ]; then
        echo "ℹ️ $name вже є символічним посиланням. Пропускаємо."
    else
        echo "❓ $name не знайдено за шляхом $src. Створюємо лінк на майбутнє."
        ln -s "$dest" "$src"
    fi
}

# 1. NPM Cache
move_and_link "$HOME_DIR/.npm" "$DEV_SPACE/npm_cache" "NPM Cache"

# 2. Bun Cache
move_and_link "$HOME_DIR/.bun" "$DEV_SPACE/bun_cache" "Bun Cache"

# 3. AI Models (u2net)
move_and_link "$HOME_DIR/.u2net" "$DEV_SPACE/ai_models" "U2Net Models"

# 4. Pip Cache (якщо є в .cache/pip)
if [ -d "$HOME_DIR/.cache/pip" ]; then
    move_and_link "$HOME_DIR/.cache/pip" "$DEV_SPACE/python_pip" "Pip Cache"
fi

echo "✨ Організація завершена! Тепер ваші бібліотеки живуть у DEV_Pack_Space."
