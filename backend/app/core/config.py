from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 공공 API
    MOLIT_API_KEY: str = ""
    APPLYHOME_API_KEY: str = ""
    LH_API_KEY: str = ""

    # 네이버 API
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""

    # AI
    ANTHROPIC_API_KEY: str = ""

    # 카카오
    KAKAO_ACCESS_TOKEN: str = ""

    # 이메일
    GMAIL_USER: str = ""
    GMAIL_APP_PASSWORD: str = ""

    # DB
    DATABASE_URL: str = "sqlite+aiosqlite:///./dashboard.db"

    # 앱 설정
    TZ: str = "Asia/Seoul"
    USE_MOCK: bool = True

    # 보안
    ADMIN_TOKEN: str = "change-me"
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
