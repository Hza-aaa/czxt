import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Settings:
    _instance: Optional["Settings"] = None

    def __new__(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_tokens: int = int(os.getenv("MAX_TOKENS", "2000"))
        self.temperature: float = float(os.getenv("TEMPERATURE", "0.2"))
        self.max_memory_size: int = 20
        self.max_retry_attempts: int = 3
        self.retry_delay_seconds: float = 2.0
        self._initialized = True

    def validate(self) -> tuple[bool, str]:
        if not self.openai_api_key or self.openai_api_key == "your-api-key-here":
            return False, "OPENAI_API_KEY 未配置，请在 .env 文件中设置有效的 API Key"
        return True, "配置验证通过"


def get_settings() -> Settings:
    return Settings()
