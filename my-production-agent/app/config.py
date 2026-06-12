from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # App
    APP_NAME: str = "AI Production Agent"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"

    # LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    # Security
    AGENT_API_KEY: str = "dev-key-change-me-in-production"
    JWT_SECRET: str = "change-me-in-production"
    ALLOWED_ORIGINS: str = "*"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 10

    # Budget
    DAILY_BUDGET_USD: float = 10.0

    # Storage
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def validate(self):
        if self.ENVIRONMENT == "production":
            if self.AGENT_API_KEY == "dev-key-change-me-in-production":
                raise ValueError("AGENT_API_KEY must be changed in production")
            if self.JWT_SECRET == "change-me-in-production":
                raise ValueError("JWT_SECRET must be changed in production")


settings = Settings()
