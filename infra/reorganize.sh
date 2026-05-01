#!/bin/bash

# WARNING: ONE-TIME migration script. Do not re-run.
# This script was used for the initial refactoring of DNK_HUB structure.
# Running it again may cause data loss or broken paths.


# Переходимо в директорію DNK_HUB
cd "/Users/kuzmenko.top/Kuzmenko/MY LIFE WORK/DNK_HUB" || exit

echo "🚀 Починаємо реорганізацію DNK_HUB..."

# 1. Створюємо ядро системи
echo "📁 Створюємо структуру /core..."
mkdir -p core

# Переміщуємо існуючі компоненти в core
if [ -d "DNK_Agent" ]; then
    mv DNK_Agent core/hermes-agent
    echo "✅ DNK_Agent перенесено в core/hermes-agent"
fi

if [ -d "DNK_Memory_HUB" ]; then
    mv DNK_Memory_HUB core/telegram-bot
    echo "✅ DNK_Memory_HUB перенесено в core/telegram-bot"
fi

if [ -d "orchestrator" ]; then
    mv orchestrator core/orchestrator
    echo "✅ orchestrator перенесено в core/orchestrator"
fi

# 2. Об'єднуємо Пам'ять та Базу Знань
echo "📁 Об'єднуємо пам'ять..."
mkdir -p memory/vault

# Переносимо дані з knowledge-base
if [ -d "knowledge-base/DNK_Memory" ]; then
    cp -r "knowledge-base/DNK_Memory/"* memory/vault/ 2>/dev/null
    echo "✅ DNK_Memory перенесено в memory/vault"
fi

if [ -d "knowledge-base/DNK_Memory OS" ]; then
    cp -r "knowledge-base/DNK_Memory OS/"* memory/vault/ 2>/dev/null
    echo "✅ DNK_Memory OS перенесено в memory/vault"
fi

# Переносимо інші папки в vault
for folder in "client-cases" "shopify" "liquid-patterns" "repos-scanned"; do
    if [ -d "knowledge-base/$folder" ]; then
        mv "knowledge-base/$folder" memory/vault/
        echo "✅ $folder перенесено в memory/vault"
    fi
done

# Видаляємо стару knowledge-base
if [ -d "knowledge-base" ]; then
    rm -rf knowledge-base
    echo "🗑️ Стару knowledge-base видалено"
fi

# 3. Прибираємо дублікати в інтеграціях
echo "📁 Очищаємо інтеграції..."
if [ -d "integrations/dnk-git-research" ]; then
    rm -rf integrations/dnk-git-research
    echo "🗑️ Порожню папку dnk-git-research видалено"
fi

if [ -d "integrations/DNK_Git_Research" ]; then
    mv integrations/DNK_Git_Research integrations/git-research-mcp
    echo "✅ DNK_Git_Research перейменовано на git-research-mcp"
fi

echo "🎉 Реорганізація завершена! Все лежить по своїх логічних полицях."
