"""Tests for config module."""

from ceramicraft_notification_mservice.config import Settings, get_settings


def test_settings_defaults():
    """Test that Settings loads with sensible defaults."""
    settings = Settings(
        POSTGRES_USER="testuser",
        POSTGRES_PASSWORD="testpass",
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5432,
        NOTIFICATION_DB_NAME="test_db",
    )
    assert settings.POSTGRES_USER == "testuser"
    assert settings.POSTGRES_PASSWORD == "testpass"
    assert settings.POSTGRES_HOST == "localhost"
    assert settings.POSTGRES_PORT == 5432
    assert settings.NOTIFICATION_DB_NAME == "test_db"
    assert settings.NOTIFICATION_MSERVICE_HTTP_HOST == "0.0.0.0"
    assert settings.NOTIFICATION_MSERVICE_HTTP_PORT == 8080
    assert settings.NOTIFICATION_MSERVICE_GRPC_HOST == "[::]"
    assert settings.NOTIFICATION_MSERVICE_GRPC_PORT == 50051
    assert settings.FIREBASE_CREDENTIALS_JSON == ""


def test_database_url_property():
    """Test that DATABASE_URL is correctly constructed."""
    settings = Settings(
        POSTGRES_USER="myuser",
        POSTGRES_PASSWORD="mypass",
        POSTGRES_HOST="dbhost",
        POSTGRES_PORT=5433,
        NOTIFICATION_DB_NAME="mydb",
    )
    expected = "postgresql+asyncpg://myuser:mypass@dbhost:5433/mydb"
    assert settings.DATABASE_URL == expected


def test_get_settings_returns_settings():
    """Test that get_settings returns a Settings instance."""
    # Clear the cache to avoid state from other tests
    get_settings.cache_clear()
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_get_settings_is_cached():
    """Test that get_settings returns the same instance (cached)."""
    get_settings.cache_clear()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
