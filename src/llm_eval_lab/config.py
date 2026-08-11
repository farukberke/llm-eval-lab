from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = (
        "postgresql+psycopg://llm_eval:llm_eval@localhost:5433/llm_eval_lab"
    )
    ollama_host: str = "http://localhost:11434"
    ollama_default_model: str = "qwen2.5:7b"


settings = Settings()
