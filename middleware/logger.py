import logging
import time
import json
from typing import Dict, Any, Optional
from fastapi import Request, Response
from fastapi.logger import logger
import uuid

# Configure logging
def setup_logging():
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)
    
    # Configure logging format
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/server.log'),
            logging.StreamHandler()
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

class RequestLogger:
    """Request logging middleware"""
    
    def __init__(self):
        self.logger = logging.getLogger("request_logger")
    
    async def log_request(self, request: Request, request_id: str):
        """Log incoming request details"""
        try:
            # Extract request information
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            content_type = request.headers.get("content-type", "unknown")
            
            # Log request details
            self.logger.info(
                f"Request started - ID: {request_id}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "content_type": content_type,
                    "headers": dict(request.headers),
                    "query_params": dict(request.query_params)
                }
            )
            
            # Log request body for POST/PUT requests (if not too large)
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.body()
                    if len(body) < 10000:  # Only log if body is reasonable size
                        try:
                            body_text = body.decode('utf-8')
                            self.logger.debug(
                                f"Request body - ID: {request_id}",
                                extra={
                                    "request_id": request_id,
                                    "body": body_text
                                }
                            )
                        except UnicodeDecodeError:
                            self.logger.debug(
                                f"Request body (binary) - ID: {request_id}",
                                extra={
                                    "request_id": request_id,
                                    "body_size": len(body)
                                }
                            )
                except Exception as e:
                    self.logger.warning(f"Could not read request body: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error logging request: {e}")
    
    async def log_response(self, request: Request, response: Response, request_id: str, process_time: float):
        """Log response details"""
        try:
            # Extract response information
            status_code = response.status_code
            content_type = response.headers.get("content-type", "unknown")
            content_length = response.headers.get("content-length", "unknown")
            
            # Determine log level based on status code
            log_level = logging.INFO if status_code < 400 else logging.WARNING
            
            self.logger.log(
                log_level,
                f"Request completed - ID: {request_id}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": status_code,
                    "content_type": content_type,
                    "content_length": content_length,
                    "process_time_ms": round(process_time * 1000, 2),
                    "response_headers": dict(response.headers)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error logging response: {e}")
    
    def log_error(self, request: Request, error: Exception, request_id: str, process_time: float):
        """Log error details"""
        try:
            self.logger.error(
                f"Request failed - ID: {request_id}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "process_time_ms": round(process_time * 1000, 2),
                    "client_ip": request.client.host if request.client else "unknown"
                },
                exc_info=True
            )
            
        except Exception as e:
            self.logger.error(f"Error logging error: {e}")

# Global request logger instance
request_logger = RequestLogger()

def get_request_id() -> str:
    """Generate a unique request ID"""
    return str(uuid.uuid4())

def log_performance_metrics(operation: str, duration: float, context: Optional[Dict[str, Any]] = None):
    """Log performance metrics for operations"""
    logger.info(
        f"Performance metric - {operation}",
        extra={
            "operation": operation,
            "duration_ms": round(duration * 1000, 2),
            "context": context or {}
        }
    )

def log_database_operation(operation: str, table: str, duration: float, rows_affected: int = 0):
    """Log database operation metrics"""
    logger.info(
        f"Database operation - {operation}",
        extra={
            "operation": operation,
            "table": table,
            "duration_ms": round(duration * 1000, 2),
            "rows_affected": rows_affected
        }
    )

def log_external_api_call(api_name: str, endpoint: str, duration: float, status_code: int = None):
    """Log external API call metrics"""
    logger.info(
        f"External API call - {api_name}",
        extra={
            "api_name": api_name,
            "endpoint": endpoint,
            "duration_ms": round(duration * 1000, 2),
            "status_code": status_code
        }
    )

# Structured logging helpers
def log_user_action(user_id: str, action: str, resource: str, details: Optional[Dict[str, Any]] = None):
    """Log user actions for audit purposes"""
    logger.info(
        f"User action - {action}",
        extra={
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details or {},
            "log_type": "user_action"
        }
    )

def log_security_event(event_type: str, user_id: str = None, ip_address: str = None, details: Optional[Dict[str, Any]] = None):
    """Log security-related events"""
    logger.warning(
        f"Security event - {event_type}",
        extra={
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details or {},
            "log_type": "security"
        }
    )

def log_business_event(event_type: str, entity_type: str, entity_id: str, details: Optional[Dict[str, Any]] = None):
    """Log business logic events"""
    logger.info(
        f"Business event - {event_type}",
        extra={
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {},
            "log_type": "business"
        }
    )
