from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    model: str = "claude-sonnet-5-5"
    max_tokens: int = 4096
    slice_height: int = 1500        # tall webtoon strips are cut into tiles of this height
    max_width: int = 1000           # images are downscaled to this width before inference
    max_upload_mb: int = 15
    concurrency: int = 3            # parallel tile requests per page


settings = Settings()
