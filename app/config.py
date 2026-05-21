from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_password: str
    database_port: str
    database_hostname: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    cloudinary_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    cloudinary_secure: bool

    

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
print(settings.database_password)