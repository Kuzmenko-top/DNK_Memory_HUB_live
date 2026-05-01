#!/bin/bash
# DNK_HUB Self-Diagnostic Tool v0.1

echo "🔍 Запуск самодіагностики DNK_HUB..."

# 1. Перевірка структури
dirs=(".antigravity" "core" "infra" "integrations" "memory" "plugin" "docs")
for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ Директорія $dir на місці."
    else
        echo "❌ Помилка: Директорія $dir відсутня!"
    fi
done

# 2. Перевірка на абсолютні шляхи
echo "🔍 Перевірка на абсолютні шляхи (Portability Check)..."
# Exclude current script and known files that might contain paths for documentation purposes
if grep -r "/Users/" . --exclude-dir=".git" --exclude-dir=".venv" --exclude-dir=".antigravity" --exclude="DIRECTORY_MAP.md" --exclude="self_check.sh" | grep -v "Binary file"; then
    echo "⚠️ Попередження: Знайдено потенційні абсолютні шляхи!"
else
    echo "✅ Абсолютних шляхів не знайдено."
fi

# 3. Перевірка на витоки секретів (Local Leak Detection)
echo "🔍 Перевірка на наявність секретів у коді..."
# Шукаємо типові патерни API ключів, але ігноруємо .env та документацію
leak_patterns=("sk-ant-" "sk-" "AIzaSy" "ghp_" "github_pat_" "SG.")
leaks_found=0
for pattern in "${leak_patterns[@]}"; do
    if grep -r "$pattern" . --exclude-dir=".git" --exclude-dir=".venv" --exclude-dir=".antigravity" --exclude=".env" --exclude=".env.example" --exclude="README.md" --exclude="self_check.sh" | grep -v "Binary file"; then
        echo "⚠️ УВАГА: Знайдено потенційний витік секрету для паттерна: $pattern"
        leaks_found=1
    fi
done

if [ $leaks_found -eq 0 ]; then
    echo "✅ Жодних підозрілих ключів не знайдено."
fi

# 5. Перевірка безпеки AI-агентів (AgentSeal)
if [ -d "node_modules/agentseal" ] || command -v agentseal &> /dev/null; then
    echo "🔍 Запуск AgentSeal Guard (Security Scan)..."
    npx agentseal guard
    echo "✅ Перевірка безпеки AI завершена."
else
    echo "⚠️ AgentSeal не знайдено. Пропускаю перевірку безпеки AI."
fi

echo "🏁 Діагностика завершена."
