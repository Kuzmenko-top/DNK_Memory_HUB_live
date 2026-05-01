# Two-Layer Agent Architecture

DNK_HUB operates two parallel agent systems. This is by design, not duplication.

## Layer 1: Hermes Team (core/orchestrator/agents/)

- **Access:** Telegram (via Герич), Hermes CLI

- **Runtime:** core/hermes-agent/ (Python, runs as background process)

- **Agents:** Герич (librarian), Шеф (shopify-pro), Реберн (reburn-engineer),
  Скаут (git-researcher), **Інженер (dnk-core-engineer)**

- **Config format:** SOUL.md + config.yaml + tools.yaml + memories/

- **When to use:** When Maks is on the factory floor, needs async work,
  Telegram-based control, or workspace maintenance (automation).

## Layer 2: Claude Code Subagents (plugin/agents/)

- **Access:** Antigravity IDE, Claude Code Desktop, Claude Code Web

- **Runtime:** Claude Code native (Anthropic infrastructure)

- **Config format:** Markdown AGENT.md with YAML frontmatter

- **When to use:** When Maks is at the desk, doing code/design/content work
  in IDE

## How they interact

- Герич can trigger Claude Code sessions via `claude --remote`

- Plugin agents share knowledge-base with Hermes agents (same vault)

- Both layers use same Qdrant collections for search

- SOUL.md (Hermes) ≠ AGENT.md (Claude Code) — different formats,
  different purposes

## Adding a new agent

- If it works through Telegram/async → add to core/orchestrator/agents/

- If it works through IDE/Claude Code → add to plugin/agents/

- If both → create in both places with shared knowledge references
