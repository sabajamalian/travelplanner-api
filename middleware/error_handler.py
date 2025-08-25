from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import logging
from typing import Union, Dict, Any
import traceback

logger = logging.getLogger(__name__)

class CustomHTTPException(HTTPException):
    """Custom HTTP exception with additional context"""
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = None,
        context: Dict[str, Any] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.context = context or {}

def add_error_handlers(app: FastAPI):
    """Add custom error handlers to the FastAPI app"""
    
    @app.exception_handler(CustomHTTPException)
    async def custom_http_exception_handler(request: Request, exc: CustomHTTPException):
        """Handle custom HTTP exceptions"""
        error_response = {
            "error": {
                "type": "http_error",
                "code": exc.error_code or f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url),
                "method": request.method
            }
        }
        
        if exc.context:
            error_response["error"]["context"] = exc.context
        
        logger.warning(
            f"Custom HTTP Exception: {exc.status_code} - {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": str(request.url),
                "method": request.method,
                "error_code": exc.error_code,
                "context": exc.context
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle standard HTTP exceptions"""
        error_response = {
            "error": {
                "type": "http_error",
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url),
                "method": request.method
            }
        }
        
        logger.warning(
            f"HTTP Exception: {exc.status_code} - {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": str(request.url),
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle ValueError exceptions"""
        error_response = {
            "error": {
                "type": "validation_error",
                "code": "VALUE_ERROR",
                "message": str(exc),
                "status_code": 400,
                "path": str(request.url),
                "method": request.method
            }
        }
        
        logger.error(
            f"ValueError: {str(exc)}",
            extra={
                "path": str(request.url),
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )
        
        return JSONResponse(
            status_code=400,
            content=error_response
        )
    
    @app.exception_handler(TypeError)
    async def type_error_handler(request: Request, exc: TypeError):
        """Handle TypeError exceptions"""
        error_response = {
            "error": {
                "type": "validation_error",
                "code": "TYPE_ERROR",
                "message": str(exc),
                "status_code": 400,
                "path": str(request.url),
                "method": request.method
            }
        }
        
        logger.error(
            f"TypeError: {str(exc)}",
            extra={
                "path": str(request.url),
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )
        
        return JSONResponse(
            status_code=400,
            content=error_response
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions"""
        error_response = {
            "error": {
                "type": "internal_error",
                "code": "INTERNAL_ERROR",
                "message": "An internal server error occurred",
                "status_code": 500,
                "path": str(request.url),
                "method": request.method
            }
        }
        
        # Log the full error for debugging
        logger.error(
            f"Unhandled Exception: {type(exc).__name__}: {str(exc)}",
            extra={
                "path": str(request.url),
                "method": request.method,
                "traceback": traceback.format_exc(),
                "exception_type": type(exc).__name__
            }
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )

def create_error_response(
    status_code: int,
    message: str,
    error_code: str = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Create a standardized error response"""
    return {
        "error": {
            "type": "error",
            "code": error_code or f"ERROR_{status_code}",
            "message": message,
            "status_code": status_code,
            "context": context or {}
        }
    }

def log_error(
    error: Exception,
    request: Request = None,
    context: Dict[str, Any] = None
):
    """Log an error with context"""
    extra = context or {}
    
    if request:
        extra.update({
            "path": str(request.url),
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent")
        })
    
    logger.error(
        f"Error: {type(error).__name__}: {str(error)}",
        extra=extra,
        exc_info=True
    )
