import logging
import os
import sys
import asyncio
from typing import Optional

logger = logging.getLogger("HermesWrapper")

# Визначаємо шляхи відносно кореня Хаба (динамічно)
HUB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# DNK_Agent знаходиться поруч з папкою Хаба
AGENT_ROOT = os.path.abspath(os.path.join(HUB_ROOT, "..", "DNK_Agent"))

HERMES_AGENT_PATH = os.path.join(AGENT_ROOT, "hermes-agent")
HERMES_HOME_PATH = os.path.join(AGENT_ROOT, "Hermes")

# Налаштовуємо середовище для Hermes
os.environ["HERMES_HOME"] = HERMES_HOME_PATH
if HERMES_AGENT_PATH not in sys.path:
    sys.path.append(HERMES_AGENT_PATH)

# Імпортуємо реальний AIAgent
try:
    from run_agent import AIAgent
except ImportError as e:
    logger.error(f"Не вдалося імпортувати AIAgent з {HERMES_AGENT_PATH}: {e}")
    AIAgent = None

class HermesAgentWrapper:
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.agent: Optional[AIAgent] = None
        
        import yaml
        if AIAgent:
            try:
                # Завантажуємо налаштування з оригінального config.yaml Гєрича v1
                config_path = os.path.join(HERMES_HOME_PATH, "config.yaml")
                with open(config_path, "r", encoding="utf-8") as f:
                    v1_config = yaml.safe_load(f)
                
                v1_model_name = v1_config.get("model", {}).get("model", "google/gemini-2.5-flash")
                v1_provider = v1_config.get("model", {}).get("provider", "vertex-gemini")
                
                # Отримуємо специфічний URL для Vertex AI з конфігурації провайдерів
                v1_base_url = v1_config.get("providers", {}).get(v1_provider, {}).get("api")
                # Беремо токен Vertex AI з середовища
                v1_api_key = os.environ.get("VERTEX_GEMINI_TOKEN")

                # Ініціалізуємо агента з ПОВНИМИ параметрами (ключ, url, модель)
                self.agent = AIAgent(
                    quiet_mode=True,
                    skip_context_files=False,
                    model=v1_model_name,
                    provider=v1_provider,
                    base_url=v1_base_url,
                    api_key=v1_api_key,
                    platform="telegram",
                    chat_id="-1003987879866"
                )
                logger.info(f"Гєрич v1 успішно інтегрований з Vertex AI (Model: {v1_model_name}).")
            except Exception as e:
                logger.error(f"Помилка ініціалізації AIAgent: {e}")
        else:
            logger.warning("Працюємо в режимі Mock-агента через відсутність AIAgent.")

    async def process_injest(self, file_path: str) -> str:
        """
        Використовує реального агента для команди Injest.
        """
        logger.info(f"Agent starting Injest for {file_path}")
        
        if not self.agent:
            return "Помилка: AIAgent не ініціалізований. Перевірте шляхи та залежності."

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Формуємо промпт для Гєрича згідно з Schema.md
            prompt = (
                f"Команда: Injest\n"
                f"Файл: {file_path}\n"
                f"Контент:\n---\n{content}\n---\n"
                f"Будь ласка, оброби цей файл згідно з нашою Schema.md. "
                f"Визнач куди його занести в wiki/ та які cross-links додати. "
                f"Дай коротке резюме виконаної роботи."
            )
            
            # AIAgent.run_conversation може бути блокуючим, тому запускаємо в thread
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.agent.run_conversation, prompt)
            
            return result
        except Exception as e:
            logger.error(f"Error processing Injest: {e}")
            return f"Помилка роботи агента: {e}"
