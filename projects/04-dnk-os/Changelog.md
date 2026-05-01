# 📝 Changelog: DNK_MEMORY_HUB

Всі значущі зміни в цьому проекті фіксуються тут за форматом [Keep a Changelog](https://keepachangelog.com/).

---

## [v0.01] — 2026-05-01 🎉 Initial Release

### ✨ Added
- **Архітектурний фундамент**: "Zero-G Root Policy" — чистота кореневої директорії як закон.
- **Directory Map** (`docs/DIRECTORY_MAP.md`): Конституція проекту для агентів та розробників.
- **Self-Diagnostic** (`infra/scripts/self_check.sh`): Автоматична перевірка цілісності системи.
- **Security Layer**:
  - Gitleaks GitHub Action для захисту від витоків секретів у CI/CD.
  - AgentSeal для локального захисту AI-агентів від небезпечних скілів.
  - RepoAudit інтеграція (`integrations/dnk-repo-audit`) для глибокого аудиту коду.
- **Distribution Pipeline** (`infra/make_distro.sh`): Автоматична збірка чистого комерційного продукту.
- **Setup Wizard** (`infra/wizard.sh`): Інтерактивний онбординг нових користувачів.
- **Documentation Standard**: Повний "Бортовий Журнал" (Plan, Task, Done_Tasks, LOG, Changelog, Docs, Instructions).
- **Community Infrastructure**: MIT License, CONTRIBUTING.md, CODE_OF_CONDUCT.md, Issue & PR Templates.
- **Hermes Agent**: Основний оркестратор (Layer 1) для управління агентивною командою.

### 🏗 Architecture
- Двійна архітектура агентів: Hermes (бізнес) + Antigravity (розробка).
- Централізована пам'ять через Qdrant + Obsidian MCP.
- Ізольована система інтеграцій у `integrations/`.

---

## [Unreleased] — Плани для v0.1
- [ ] Повноцінна інтеграція Obsidian → Qdrant pipeline.
- [ ] Публічна документація на GitHub Pages.
- [ ] Додавання сервісу DNK_SMM_Planer.
