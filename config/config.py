import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator
from pathlib import Path

class Settings(BaseSettings):
    """Application settings"""
    
    # FastAPI settings
    FASTAPI_APP: str = "main.py"
    APP_NAME: str = "Travel Planner API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 5555
    
    # Database settings
    DATABASE_PATH: str = "./travelplanner.db"
    DATABASE_URL: Optional[str] = None
    
    # File upload settings
    UPLOAD_PATH: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "application/pdf"]
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    CORS_EXPOSE_HEADERS: List[str] = ["X-Process-Time", "X-Request-ID"]
    CORS_MAX_AGE: int = 86400  # 24 hours
    
    # Security settings
    ALLOWED_HOSTS: List[str] = ["*"]
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Logging settings
    LOG_LEVEL: str = "info"
    LOG_FILE: str = "logs/server.log"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Test settings
    LOAD_TEST_DATA: bool = False
    TESTING: bool = False
    
    # Performance settings
    MAX_CONNECTIONS: int = 100
    CONNECTION_TIMEOUT: int = 30
    
    @validator('PORT')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('PORT must be between 1 and 65535')
        return v
    
    @validator('MAX_FILE_SIZE')
    def validate_max_file_size(cls, v):
        if v <= 0:
            raise ValueError('MAX_FILE_SIZE must be positive')
        return v
    
    @validator('CORS_MAX_AGE')
    def validate_cors_max_age(cls, v):
        if v < 0:
            raise ValueError('CORS_MAX_AGE must be non-negative')
        return v
    
    @validator('LOG_LEVEL')
    def validate_log_level(cls, v):
        valid_levels = ['debug', 'info', 'warning', 'error', 'critical']
        if v.lower() not in valid_levels:
            raise ValueError(f'LOG_LEVEL must be one of: {valid_levels}')
        return v.lower()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get application settings"""
    global _settings
    
    if _settings is None:
        _settings = Settings()
    
    return _settings

def reload_settings() -> Settings:
    """Reload application settings"""
    global _settings
    _settings = Settings()
    return _settings

def get_database_url() -> str:
    """Get database URL from settings"""
    settings = get_settings()
    
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    
    # Construct SQLite URL
    db_path = Path(settings.DATABASE_PATH)
    return f"sqlite:///{db_path.absolute()}"

def get_upload_path() -> Path:
    """Get upload directory path"""
    settings = get_settings()
    upload_path = Path(settings.UPLOAD_PATH)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path

def get_log_path() -> Path:
    """Get log directory path"""
    settings = get_settings()
    log_path = Path(settings.LOG_FILE).parent
    log_path.mkdir(parents=True, exist_ok=True)
    return log_path

def validate_environment() -> bool:
    """Validate environment configuration"""
    try:
        settings = get_settings()
        
        # Validate database path
        db_path = Path(settings.DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Validate upload path
        upload_path = Path(settings.UPLOAD_PATH)
        upload_path.mkdir(parents=True, exist_ok=True)
        
        # Validate log path
        log_path = Path(settings.LOG_FILE).parent
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Validate CORS configuration
        if not settings.CORS_ORIGINS:
            raise ValueError("CORS_ORIGINS cannot be empty")
        
        # Validate file size
        if settings.MAX_FILE_SIZE <= 0:
            raise ValueError("MAX_FILE_SIZE must be positive")
        
        return True
        
    except Exception as e:
        print(f"Environment validation failed: {e}")
        return False

def get_environment_info() -> dict:
    """Get environment information for debugging"""
    settings = get_settings()
    
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "host": settings.HOST,
        "port": settings.PORT,
        "database_path": settings.DATABASE_PATH,
        "upload_path": settings.UPLOAD_PATH,
        "cors_origins": settings.CORS_ORIGINS,
        "log_level": settings.LOG_LEVEL,
        "max_file_size": settings.MAX_FILE_SIZE,
        "allowed_file_types": settings.ALLOWED_FILE_TYPES
    }

# Environment-specific configurations
def get_development_config() -> Settings:
    """Get development configuration"""
    return Settings(
        DEBUG=True,
        LOG_LEVEL="debug",
        LOAD_TEST_DATA=True,
        CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000", "*"]
    )

def get_production_config() -> Settings:
    """Get production configuration"""
    return Settings(
        DEBUG=False,
        LOG_LEVEL="warning",
        LOAD_TEST_DATA=False,
        CORS_ORIGINS=["https://yourdomain.com"],  # Update with actual domain
        ALLOWED_HOSTS=["yourdomain.com"]  # Update with actual domain
    )

def get_test_config() -> Settings:
    """Get test configuration"""
    return Settings(
        DEBUG=True,
        LOG_LEVEL="debug",
        TESTING=True,
        DATABASE_PATH="./test_travelplanner.db",
        UPLOAD_PATH="./test_uploads"
    )

# Configuration presets
CONFIG_PRESETS = {
    "development": get_development_config,
    "production": get_production_config,
    "testing": get_test_config
}

def load_config_preset(preset_name: str) -> Settings:
    """Load configuration preset"""
    if preset_name not in CONFIG_PRESETS:
        raise ValueError(f"Unknown config preset: {preset_name}")
    
    preset_func = CONFIG_PRESETS[preset_name]
    return preset_func()

# Environment variable helpers
def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable"""
    value = os.getenv(key, str(default)).lower()
    return value in ("true", "1", "yes", "on")

def get_env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable"""
    try:
        return int(os.getenv(key, default))
    except (ValueError, TypeError):
        return default

def get_env_list(key: str, default: List[str] = None, separator: str = ",") -> List[str]:
    """Get list environment variable"""
    if default is None:
        default = []
    
    value = os.getenv(key, "")
    if not value:
        return default
    
    return [item.strip() for item in value.split(separator) if item.strip()]
