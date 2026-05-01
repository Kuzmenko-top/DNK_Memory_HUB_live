import logging
import os
import sys
import asyncio
import yaml
from typing import Optional, Dict

logger = logging.getLogger("MultiAgentManager")

# Визначаємо шляхи відносно кореня Хаба (який тепер буде в DNK_HUB)
HUB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# Визначаємо корінь всього проекту DNK_HUB (піднімаємось на 2 рівні від core/telegram-bot)
DNK_HUB_ROOT = os.path.abspath(os.path.join(HUB_ROOT, "..", ".."))

# Шлях до папки з агентами оркестратора
ORCHESTRATOR_AGENTS_PATH = os.path.join(DNK_HUB_ROOT, "core", "orchestrator", "agents")

# Шлях до ядра Hermes Agent
HERMES_AGENT_PATH = os.path.join(DNK_HUB_ROOT, "core", "hermes-agent", "hermes-agent")


if HERMES_AGENT_PATH not in sys.path:
    sys.path.append(HERMES_AGENT_PATH)

try:
    from run_agent import AIAgent
except ImportError as e:
    logger.error(f"Не вдалося імпортувати AIAgent з {HERMES_AGENT_PATH}: {e}")
    AIAgent = None

class MultiAgentManager:
    def __init__(self):
        self.agents_cache: Dict[str, AIAgent] = {}

    def get_agent(self, agent_id: str, chat_id: str = "-1003987879866") -> Optional['AIAgent']:
        """Повертає ініціалізованого агента за його ID, використовуючи кеш."""
        if not AIAgent:
            logger.error("AIAgent class not available.")
            return None

        if agent_id in self.agents_cache:
            return self.agents_cache[agent_id]

        agent_home = os.path.join(ORCHESTRATOR_AGENTS_PATH, agent_id)
        if not os.path.exists(agent_home):
            logger.error(f"Папка агента не знайдена: {agent_home}")
            return None

        # Тимчасово змінюємо HERMES_HOME для ініціалізації конкретного агента
        original_home = os.environ.get("HERMES_HOME")
        os.environ["HERMES_HOME"] = agent_home

        try:
            config_path = os.path.join(agent_home, "config.yaml")
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            model_name = config.get("model", {}).get("model", "gemini-2.5-flash")
            provider = config.get("model", {}).get("provider", "google-genai")
            
            base_url = config.get("providers", {}).get(provider, {}).get("api")
            key_env = config.get("providers", {}).get(provider, {}).get("key_env", "GEMINI_API_KEY")
            api_key = os.environ.get(key_env, "")

            logger.info(f"Ініціалізація агента {agent_id} (Model: {model_name}, Provider: {provider})...")
            
            # Тільки якщо base_url існує, передаємо його
            agent_kwargs = {
                "quiet_mode": True,
                "skip_context_files": False,
                "model": model_name,
                "provider": provider,
                "api_key": api_key,
                "platform": "telegram",
                "chat_id": chat_id
            }
            if base_url:
                agent_kwargs["base_url"] = base_url

            agent_instance = AIAgent(**agent_kwargs)
            
            self.agents_cache[agent_id] = agent_instance
            logger.info(f"Агент {agent_id} успішно ініціалізований.")
            
            return agent_instance
        except Exception as e:
            logger.error(f"Помилка ініціалізації агента {agent_id}: {e}")
            return None
        finally:
            # Повертаємо попередній шлях (або видаляємо, якщо не було)
            if original_home:
                os.environ["HERMES_HOME"] = original_home
            else:
                del os.environ["HERMES_HOME"]

    async def process_with_agent(self, agent_id: str, prompt: str, chat_id: str = "-1003987879866") -> str:
        """Запускає виконання промпту на вказаному агенті."""
        agent = self.get_agent(agent_id, chat_id)
        if not agent:
            return f"Помилка: Агент {agent_id} недоступний."

        logger.info(f"[{agent_id}] Отримав завдання. Виконую...")
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, agent.run_conversation, prompt)
            return result
        except Exception as e:
            logger.error(f"[{agent_id}] Помилка виконання: {e}")
            return f"Помилка роботи агента {agent_id}: {e}"

# Глобальний екземпляр менеджера
multi_agent_manager = MultiAgentManager()
