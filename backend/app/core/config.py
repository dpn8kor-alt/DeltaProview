from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "ProcessCompass"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_ORIGIN: str = "http://127.0.0.1:5173"

    CONFLUENCE_BASE_URL: str = "https://kms.wam-sso.bosch.com"
    CONFLUENCE_USERNAME: str = ""
    CONFLUENCE_PASSWORD: str = ""
    CONFLUENCE_API_TOKEN: str = ""
    CONFLUENCE_AUTH_MODE: str = "basic"
    CONFLUENCE_TIMEOUT_SECONDS: int = 30

    PROCESS_LANDSCAPE_ROOT_PAGE_ID: str = "293504307"
    REVISION_HISTORY_BASE_URL: str = ""
    REVISION_HISTORY_LANGUAGE_QUERY: str = "/and/language/en"
    CHROME_HEADLESS: bool = True
    OUTPUT_DIR: str = "../output"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
