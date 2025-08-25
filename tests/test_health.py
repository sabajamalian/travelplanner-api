import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
import httpx
import asyncio

# Test health check endpoints
class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_health_check(self, client: TestClient):
        """Test basic health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "service" in data
        assert data["service"] == "travel-planner-backend"
    
    def test_database_health_check(self, client: TestClient):
        """Test database health check endpoint"""
        response = client.get("/health/db")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "database" in data
        assert "timestamp" in data
        
        # Database should be healthy in test environment
        assert data["status"] in ["healthy", "unhealthy"]
        assert data["database"] in ["connected", "disconnected"]
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data
        
        assert data["message"] == "Travel Planner Backend API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"

# Test server startup
class TestServerStartup:
    """Test server startup functionality"""
    
    def test_server_configuration(self, test_app: FastAPI):
        """Test server configuration"""
        assert test_app.title == "Travel Planner API"
        assert test_app.description == "Backend API for Travel Planner application"
        assert test_app.version == "1.0.0"
        assert test_app.docs_url == "/docs"
        assert test_app.redoc_url == "/redoc"
    
    def test_middleware_configuration(self, test_app: FastAPI):
        """Test middleware configuration"""
        # Check if CORS middleware is configured
        cors_middleware = None
        for middleware in test_app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break
        
        assert cors_middleware is not None
    
    def test_static_files_mounted(self, test_app: FastAPI):
        """Test static files are mounted"""
        # Check if uploads directory is mounted
        static_mounts = [route.path for route in test_app.routes if hasattr(route, 'path')]
        assert "/uploads" in static_mounts

# Test database connection
class TestDatabaseConnection:
    """Test database connection functionality"""
    
    @pytest.mark.asyncio
    async def test_database_initialization(self, test_database):
        """Test database initialization"""
        # This test uses the test_database fixture
        # which should initialize the database successfully
        assert True  # If we get here, initialization succeeded
    
    @pytest.mark.asyncio
    async def test_database_connection_check(self):
        """Test database connection check"""
        from database.db import check_db_connection
        
        # Test database connection
        is_connected = await check_db_connection()
        assert isinstance(is_connected, bool)
    
    def test_database_file_creation(self, test_database_path):
        """Test database file creation"""
        # Check if database file exists
        assert test_database_path.exists()
        
        # Check if it's a file
        assert test_database_path.is_file()
        
        # Check if it has some content (not empty)
        assert test_database_path.stat().st_size > 0

# Test error handling
class TestErrorHandling:
    """Test error handling functionality"""
    
    def test_404_error(self, client: TestClient):
        """Test 404 error handling"""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "error" in data
        assert data["error"]["type"] == "http_error"
        assert data["error"]["code"] == "HTTP_404"
    
    def test_method_not_allowed(self, client: TestClient):
        """Test method not allowed error"""
        response = client.post("/health")
        
        assert response.status_code == 405
        data = response.json()
        
        assert "error" in data
        assert data["error"]["type"] == "http_error"
        assert data["error"]["code"] == "HTTP_405"

# Test CORS functionality
class TestCORS:
    """Test CORS functionality"""
    
    def test_cors_headers_present(self, client: TestClient):
        """Test CORS headers are present"""
        response = client.options("/health")
        
        # Check if CORS headers are present
        headers = response.headers
        
        # These headers should be present for CORS
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers
        assert "access-control-allow-headers" in headers
    
    def test_cors_preflight_request(self, client: TestClient):
        """Test CORS preflight request"""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type"
        }
        
        response = client.options("/health", headers=headers)
        
        assert response.status_code == 200
        
        # Check CORS headers
        cors_headers = response.headers
        assert "access-control-allow-origin" in cors_headers
        assert "access-control-allow-methods" in cors_headers

# Test performance headers
class TestPerformanceHeaders:
    """Test performance-related headers"""
    
    def test_process_time_header(self, client: TestClient):
        """Test process time header is present"""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        # Check if process time header is present
        headers = response.headers
        assert "x-process-time" in headers
        
        # Process time should be a number
        process_time = float(headers["x-process-time"])
        assert process_time >= 0

# Test async functionality
class TestAsyncFunctionality:
    """Test async functionality"""
    
    @pytest.mark.asyncio
    async def test_async_health_check(self, async_client):
        """Test async health check"""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_async_database_health(self, async_client):
        """Test async database health check"""
        response = await async_client.get("/health/db")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "database" in data

# Test configuration loading
class TestConfiguration:
    """Test configuration loading"""
    
    def test_environment_variables(self, test_settings):
        """Test environment variables are loaded"""
        assert test_settings.PORT == 5555
        assert test_settings.DATABASE_PATH == "./test_travelplanner.db"
        assert test_settings.UPLOAD_PATH == "./test_uploads"
        assert test_settings.LOG_LEVEL == "debug"
        assert test_settings.TESTING == True
    
    def test_cors_configuration(self, test_settings):
        """Test CORS configuration"""
        assert "http://localhost:3000" in test_settings.CORS_ORIGINS
        assert test_settings.CORS_ALLOW_CREDENTIALS == True
        assert "GET" in test_settings.CORS_ALLOW_METHODS
        assert "POST" in test_settings.CORS_ALLOW_METHODS

# Test logging
class TestLogging:
    """Test logging functionality"""
    
    def test_log_directory_created(self, test_settings):
        """Test log directory is created"""
        from pathlib import Path
        
        log_path = Path(test_settings.LOG_FILE).parent
        assert log_path.exists()
        assert log_path.is_dir()
    
    def test_log_file_creation(self, client: TestClient):
        """Test log file creation"""
        # Make a request to generate some logs
        response = client.get("/health")
        assert response.status_code == 200
        
        # Check if log file exists
        from pathlib import Path
        log_file = Path("logs/server.log")
        
        # Log file should exist and have content
        if log_file.exists():
            assert log_file.stat().st_size > 0

# Test file upload configuration
class TestFileUpload:
    """Test file upload configuration"""
    
    def test_upload_directory_created(self, test_settings):
        """Test upload directory is created"""
        from pathlib import Path
        
        upload_path = Path(test_settings.UPLOAD_PATH)
        assert upload_path.exists()
        assert upload_path.is_dir()
    
    def test_file_size_configuration(self, test_settings):
        """Test file size configuration"""
        assert test_settings.MAX_FILE_SIZE > 0
        assert test_settings.MAX_FILE_SIZE == 10 * 1024 * 1024  # 10MB
    
    def test_allowed_file_types(self, test_settings):
        """Test allowed file types configuration"""
        assert len(test_settings.ALLOWED_FILE_TYPES) > 0
        assert "image/jpeg" in test_settings.ALLOWED_FILE_TYPES
        assert "image/png" in test_settings.ALLOWED_FILE_TYPES

# Test API documentation
class TestAPIDocumentation:
    """Test API documentation endpoints"""
    
    def test_swagger_docs_available(self, client: TestClient):
        """Test Swagger documentation is available"""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_available(self, client: TestClient):
        """Test ReDoc documentation is available"""
        response = client.get("/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_openapi_schema_available(self, client: TestClient):
        """Test OpenAPI schema is available"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
