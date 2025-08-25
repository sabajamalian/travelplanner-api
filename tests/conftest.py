import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from fastapi import FastAPI
import os
import sys

# Add server directory to Python path
server_dir = Path(__file__).parent.parent
sys.path.insert(0, str(server_dir))

from main import app
from config.config import get_settings, Settings
from database.db import DatabaseManager, init_db, check_db_connection

# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Get test settings"""
    # Override settings for testing
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_PATH"] = "./test_travelplanner.db"
    os.environ["UPLOAD_PATH"] = "./test_uploads"
    os.environ["LOG_LEVEL"] = "debug"
    os.environ["LOAD_TEST_DATA"] = "false"
    
    # Force reload of settings with new environment variables
    from config.config import reload_settings
    return reload_settings()

@pytest.fixture(scope="session")
def test_database_path(test_settings) -> Path:
    """Get test database path"""
    db_path = Path(test_settings.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path

@pytest.fixture(scope="session")
def test_upload_path(test_settings) -> Path:
    """Get test upload path"""
    upload_path = Path(test_settings.UPLOAD_PATH)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path

@pytest.fixture(scope="session")
async def test_database(test_database_path, test_upload_path):
    """Setup test database"""
    # Create test database
    await init_db()
    
    yield
    
    # Cleanup test database
    if test_database_path.exists():
        test_database_path.unlink()
    
    # Cleanup test uploads
    if test_upload_path.exists():
        shutil.rmtree(test_upload_path)

@pytest.fixture
def client(test_database) -> Generator[TestClient, None, None]:
    """Create test client"""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def test_app() -> FastAPI:
    """Get test FastAPI app"""
    return app

# Test utilities
class TestData:
    """Test data utilities"""
    
    @staticmethod
    def create_test_user():
        """Create test user data"""
        return {
            "username": "testuser",
            "email": "test@example.com"
        }
    
    @staticmethod
    def create_test_travel():
        """Create test travel data"""
        return {
            "title": "Test Travel",
            "description": "A test travel plan",
            "start_date": "2024-01-01",
            "end_date": "2024-01-07"
        }
    
    @staticmethod
    def create_test_event():
        """Create test event data"""
        return {
            "title": "Test Event",
            "description": "A test event",
            "event_date": "2024-01-03",
            "event_time": "14:00",
            "location": "Test Location"
        }

@pytest.fixture
def test_data():
    """Get test data utilities"""
    return TestData()

# Mock configurations
@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    class MockSettings:
        DEBUG = True
        PORT = 5555
        DATABASE_PATH = "./test.db"
        UPLOAD_PATH = "./test_uploads"
        LOG_LEVEL = "debug"
        CORS_ORIGINS = ["http://localhost:3000"]
        CORS_ALLOW_CREDENTIALS = True
        CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE"]
        CORS_ALLOW_HEADERS = ["*"]
        CORS_EXPOSE_HEADERS = ["X-Process-Time"]
        CORS_MAX_AGE = 86400
        ALLOWED_HOSTS = ["*"]
        MAX_FILE_SIZE = 10485760
        ALLOWED_FILE_TYPES = ["image/jpeg", "image/png"]
    
    return MockSettings()

@pytest.fixture
def mock_database():
    """Mock database for testing"""
    class MockDatabase:
        def __init__(self):
            self.data = {}
            self.queries = []
        
        def execute_query(self, query, params=()):
            self.queries.append((query, params))
            return 1
        
        def fetch_one(self, query, params=()):
            self.queries.append((query, params))
            return {"id": 1, "test": "data"}
        
        def fetch_all(self, query, params=()):
            self.queries.append((query, params))
            return [{"id": 1, "test": "data"}]
        
        def table_exists(self, table_name):
            return table_name in ["users", "travels", "events"]
        
        def get_table_count(self, table_name):
            return 1
        
        def close_connection(self):
            pass
    
    return MockDatabase()

# Async test utilities
@pytest.fixture
async def async_client():
    """Create async test client"""
    from httpx import AsyncClient
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# Database test utilities
@pytest.fixture
async def clean_database(test_database):
    """Clean database before each test"""
    # This fixture runs before each test
    # You can add cleanup logic here if needed
    yield

@pytest.fixture
async def sample_data(clean_database):
    """Insert sample data for testing"""
    # This fixture can be used to insert test data
    # that multiple tests might need
    yield

# Performance testing utilities
@pytest.fixture
def performance_timer():
    """Timer utility for performance testing"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()

# Configuration for pytest
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    for item in items:
        # Mark tests based on their names
        if "test_health" in item.name:
            item.add_marker(pytest.mark.unit)
        elif "test_database" in item.name:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)

# Test environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment"""
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["ENVIRONMENT"] = "test"
    
    # Create test directories
    test_dirs = ["./test_uploads", "./logs"]
    for test_dir in test_dirs:
        Path(test_dir).mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Cleanup test environment
    for test_dir in test_dirs:
        if Path(test_dir).exists():
            shutil.rmtree(test_dir)
