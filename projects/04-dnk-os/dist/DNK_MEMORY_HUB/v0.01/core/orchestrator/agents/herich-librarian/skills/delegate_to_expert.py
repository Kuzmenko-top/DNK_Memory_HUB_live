"""
Skill: delegate_to_expert
Description: Дозволяє передати завдання спеціалізованому агенту (наприклад, shopify-pro, reburn-engineer, git-researcher) та отримати від нього результат.
"""
import sys
import os

# Додаємо шлях до нашого MultiAgentManager
HUB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "DNK_Vibe", "DNK_Projects", "DNK_Memory_HUB"))
if HUB_ROOT not in sys.path:
    sys.path.append(HUB_ROOT)

from core.agent_runner.multi_agent import multi_agent_manager
import asyncio

def run_delegate(agent_name: str, task: str, context: str = "") -> str:
    """
    Передає завдання спеціалізованому агенту.
    
    Args:
        agent_name: ID агента (наприклад: shopify-pro, reburn-engineer, git-researcher)
        task: Опис завдання або питання, яке потрібно вирішити.
        context: Додатковий контекст або попередні дані.
    """
    print(f"🔄 Делегування завдання до {agent_name}...")
    
    prompt = f"Завдання від Головного Бібліотекаря:\n{task}\n\nКонтекст:\n{context}\n\nБудь ласка, виріши цю задачу і дай чітку відповідь для користувача."
    
    # Виконуємо синхронно, оскільки skill запускається в окремому процесі/потоці
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    result = loop.run_until_complete(multi_agent_manager.process_with_agent(agent_name, prompt))
    
    print(f"✅ Відповідь від {agent_name} отримана.")
    return result

# Точка входу для Hermes Agent
def main():
    import fire
    fire.Fire(run_delegate)

if __name__ == "__main__":
    main()
