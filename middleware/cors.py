from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from config.config import get_settings

def setup_cors(app: FastAPI):
    """Setup CORS middleware for the FastAPI application"""
    
    settings = get_settings()
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        expose_headers=settings.CORS_EXPOSE_HEADERS,
        max_age=settings.CORS_MAX_AGE
    )

def get_cors_config() -> dict:
    """Get CORS configuration dictionary"""
    settings = get_settings()
    
    return {
        "allow_origins": settings.CORS_ORIGINS,
        "allow_credentials": settings.CORS_ALLOW_CREDENTIALS,
        "allow_methods": settings.CORS_ALLOW_METHODS,
        "allow_headers": settings.CORS_ALLOW_HEADERS,
        "expose_headers": settings.CORS_EXPOSE_HEADERS,
        "max_age": settings.CORS_MAX_AGE
    }

def is_origin_allowed(origin: str) -> bool:
    """Check if an origin is allowed"""
    settings = get_settings()
    
    # Check if origin is in allowed origins
    if origin in settings.CORS_ORIGINS:
        return True
    
    # Check if wildcard is allowed
    if "*" in settings.CORS_ORIGINS:
        return True
    
    # Check if origin matches any pattern
    for allowed_origin in settings.CORS_ORIGINS:
        if allowed_origin.startswith("*."):
            # Handle wildcard subdomains
            domain = allowed_origin[2:]  # Remove "*."
            if origin.endswith(domain):
                return True
        elif allowed_origin.startswith("http://") or allowed_origin.startswith("https://"):
            # Handle protocol-specific origins
            if origin == allowed_origin:
                return True
    
    return False

def get_cors_headers(origin: str) -> dict:
    """Get CORS headers for a specific origin"""
    if not is_origin_allowed(origin):
        return {}
    
    settings = get_settings()
    
    headers = {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": str(settings.CORS_ALLOW_CREDENTIALS).lower(),
        "Access-Control-Allow-Methods": ", ".join(settings.CORS_ALLOW_METHODS),
        "Access-Control-Allow-Headers": ", ".join(settings.CORS_ALLOW_HEADERS),
        "Access-Control-Max-Age": str(settings.CORS_MAX_AGE)
    }
    
    if settings.CORS_EXPOSE_HEADERS:
        headers["Access-Control-Expose-Headers"] = ", ".join(settings.CORS_EXPOSE_HEADERS)
    
    return headers

def validate_cors_config():
    """Validate CORS configuration"""
    settings = get_settings()
    
    # Validate origins
    if not settings.CORS_ORIGINS:
        raise ValueError("CORS_ORIGINS cannot be empty")
    
    # Validate methods
    valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
    invalid_methods = set(settings.CORS_ALLOW_METHODS) - valid_methods
    if invalid_methods:
        raise ValueError(f"Invalid CORS methods: {invalid_methods}")
    
    # Validate max age
    if settings.CORS_MAX_AGE < 0:
        raise ValueError("CORS_MAX_AGE must be non-negative")
    
    return True

# CORS preflight handler
async def handle_cors_preflight(request):
    """Handle CORS preflight request"""
    origin = request.headers.get("origin")
    
    if not origin or not is_origin_allowed(origin):
        return None
    
    # Get CORS headers
    cors_headers = get_cors_headers(origin)
    
    # Check if the actual request method is allowed
    request_method = request.headers.get("access-control-request-method")
    if request_method and request_method not in get_settings().CORS_ALLOW_METHODS:
        return None
    
    # Check if the actual request headers are allowed
    request_headers = request.headers.get("access-control-request-headers")
    if request_headers:
        requested_headers = [h.strip() for h in request_headers.split(",")]
        allowed_headers = get_settings().CORS_ALLOW_HEADERS
        if not all(header.lower() in [h.lower() for h in allowed_headers] for header in requested_headers):
            return None
    
    return cors_headers

# CORS utility functions
def add_cors_headers_to_response(response, origin: str):
    """Add CORS headers to a response"""
    if origin and is_origin_allowed(origin):
        cors_headers = get_cors_headers(origin)
        for header, value in cors_headers.items():
            response.headers[header] = value

def create_cors_response(data: dict, origin: str, status_code: int = 200):
    """Create a response with CORS headers"""
    from fastapi.responses import JSONResponse
    
    response = JSONResponse(content=data, status_code=status_code)
    add_cors_headers_to_response(response, origin)
    return response

# CORS middleware class for custom implementations
class CustomCORSMiddleware:
    """Custom CORS middleware for advanced use cases"""
    
    def __init__(self, app, **kwargs):
        self.app = app
        self.cors_config = kwargs
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Handle CORS for HTTP requests
            await self.handle_cors(scope, receive, send)
        else:
            await self.app(scope, receive, send)
    
    async def handle_cors(self, scope, receive, send):
        """Handle CORS logic"""
        # This is a simplified implementation
        # In practice, you'd want to use the built-in CORSMiddleware
        await self.app(scope, receive, send)
