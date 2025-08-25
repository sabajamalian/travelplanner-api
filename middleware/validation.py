import re
import html
from typing import Any, Dict, List, Optional, Union
from fastapi import Request, HTTPException
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, field: str, message: str, error_code: str = "VALIDATION_ERROR"):
        self.field = field
        self.message = message
        self.error_code = error_code
        super().__init__(message)

class InputValidator:
    """Input validation and sanitization class"""
    
    def __init__(self):
        # Common validation patterns
        self.patterns = {
            "email": re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            "phone": re.compile(r'^\+?[\d\s\-\(\)]{10,}$'),
            "date": re.compile(r'^\d{4}-\d{2}-\d{2}$'),
            "time": re.compile(r'^\d{2}:\d{2}(:\d{2})?$'),
            "url": re.compile(r'^https?://[^\s/$.?#].[^\s]*$'),
            "username": re.compile(r'^[a-zA-Z0-9_-]{3,20}$'),
            "password": re.compile(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*?&]{8,}$')
        }
        
        # Maximum lengths for different field types
        self.max_lengths = {
            "title": 200,
            "description": 2000,
            "location": 500,
            "name": 100,
            "email": 254,
            "username": 50,
            "url": 2048
        }
    
    def sanitize_string(self, value: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            raise ValidationError("input", "Value must be a string")
        
        # Remove HTML tags and entities
        sanitized = html.unescape(value)
        sanitized = re.sub(r'<[^>]*>', '', sanitized)
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        # Check length
        if max_length and len(sanitized) > max_length:
            raise ValidationError("input", f"Value exceeds maximum length of {max_length} characters")
        
        return sanitized
    
    def validate_required(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate that required fields are present and not empty"""
        missing_fields = []
        
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
            elif isinstance(data[field], str) and not data[field].strip():
                missing_fields.append(field)
            elif isinstance(data[field], (list, dict)) and not data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationError(
                "required_fields",
                f"Missing required fields: {', '.join(missing_fields)}",
                "MISSING_REQUIRED_FIELDS"
            )
    
    def validate_email(self, email: str) -> str:
        """Validate and sanitize email address"""
        if not email:
            raise ValidationError("email", "Email is required")
        
        email = self.sanitize_string(email, self.max_lengths["email"])
        
        if not self.patterns["email"].match(email):
            raise ValidationError("email", "Invalid email format")
        
        return email.lower()
    
    def validate_date(self, date_str: str) -> str:
        """Validate date format (YYYY-MM-DD)"""
        if not date_str:
            raise ValidationError("date", "Date is required")
        
        date_str = self.sanitize_string(date_str)
        
        if not self.patterns["date"].match(date_str):
            raise ValidationError("date", "Invalid date format. Use YYYY-MM-DD")
        
        # Additional date validation
        try:
            from datetime import datetime
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValidationError("date", "Invalid date value")
        
        return date_str
    
    def validate_time(self, time_str: str) -> str:
        """Validate time format (HH:MM or HH:MM:SS)"""
        if not time_str:
            raise ValidationError("time", "Time is required")
        
        time_str = self.sanitize_string(time_str)
        
        if not self.patterns["time"].match(time_str):
            raise ValidationError("time", "Invalid time format. Use HH:MM or HH:MM:SS")
        
        # Additional time validation
        try:
            from datetime import datetime
            if len(time_str) == 5:  # HH:MM
                datetime.strptime(time_str, "%H:%M")
            else:  # HH:MM:SS
                datetime.strptime(time_str, "%H:%M:%S")
        except ValueError:
            raise ValidationError("time", "Invalid time value")
        
        return time_str
    
    def validate_url(self, url: str) -> str:
        """Validate and sanitize URL"""
        if not url:
            return ""
        
        url = self.sanitize_string(url, self.max_lengths["url"])
        
        if url and not self.patterns["url"].match(url):
            raise ValidationError("url", "Invalid URL format")
        
        return url
    
    def validate_integer(self, value: Any, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
        """Validate integer value"""
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError("integer", "Value must be a valid integer")
        
        if min_value is not None and int_value < min_value:
            raise ValidationError("integer", f"Value must be at least {min_value}")
        
        if max_value is not None and int_value > max_value:
            raise ValidationError("integer", f"Value must be at most {max_value}")
        
        return int_value
    
    def validate_float(self, value: Any, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
        """Validate float value"""
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError("float", "Value must be a valid number")
        
        if min_value is not None and float_value < min_value:
            raise ValidationError("float", f"Value must be at least {min_value}")
        
        if max_value is not None and float_value > max_value:
            raise ValidationError("float", f"Value must be at most {max_value}")
        
        return float_value
    
    def validate_enum(self, value: Any, allowed_values: List[Any]) -> Any:
        """Validate that value is in allowed values"""
        if value not in allowed_values:
            raise ValidationError(
                "enum",
                f"Value must be one of: {', '.join(map(str, allowed_values))}",
                "INVALID_ENUM_VALUE"
            )
        return value
    
    def validate_list(self, value: Any, item_validator=None, min_length: Optional[int] = None, max_length: Optional[int] = None) -> List[Any]:
        """Validate list value"""
        if not isinstance(value, list):
            raise ValidationError("list", "Value must be a list")
        
        if min_length is not None and len(value) < min_length:
            raise ValidationError("list", f"List must have at least {min_length} items")
        
        if max_length is not None and len(value) > max_length:
            raise ValidationError("list", f"List must have at most {max_length} items")
        
        if item_validator:
            validated_items = []
            for i, item in enumerate(value):
                try:
                    validated_items.append(item_validator(item))
                except ValidationError as e:
                    raise ValidationError(f"list[{i}]", e.message, e.error_code)
            return validated_items
        
        return value
    
    def validate_file_upload(self, file_size: int, max_size: int, allowed_types: List[str] = None) -> None:
        """Validate file upload"""
        if file_size > max_size:
            raise ValidationError(
                "file_size",
                f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)",
                "FILE_TOO_LARGE"
            )
        
        if allowed_types:
            # This would typically be validated against the actual file content
            pass

# Global validator instance
validator = InputValidator()

# Validation decorator for endpoints
def validate_request_data(required_fields: List[str] = None, optional_fields: Dict[str, Any] = None):
    """Decorator to validate request data"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if request:
                try:
                    # Get request body
                    body = await request.json()
                    
                    # Validate required fields
                    if required_fields:
                        validator.validate_required(body, required_fields)
                    
                    # Validate optional fields if provided
                    if optional_fields:
                        for field, field_type in optional_fields.items():
                            if field in body:
                                if field_type == "email":
                                    body[field] = validator.validate_email(body[field])
                                elif field_type == "date":
                                    body[field] = validator.validate_date(body[field])
                                elif field_type == "time":
                                    body[field] = validator.validate_time(body[field])
                                elif field_type == "url":
                                    body[field] = validator.validate_url(body[field])
                                elif field_type == "integer":
                                    body[field] = validator.validate_integer(body[field])
                                elif field_type == "float":
                                    body[field] = validator.validate_float(body[field])
                    
                    # Add validated data to request state
                    request.state.validated_data = body
                    
                except ValidationError as e:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "validation_error",
                            "field": e.field,
                            "message": e.message,
                            "error_code": e.error_code
                        }
                    )
                except Exception as e:
                    logger.error(f"Validation error: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "validation_error",
                            "message": "Invalid request data"
                        }
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Utility functions
def sanitize_input(data: Union[str, Dict, List]) -> Union[str, Dict, List]:
    """Sanitize input data recursively"""
    if isinstance(data, str):
        return validator.sanitize_string(data)
    elif isinstance(data, dict):
        return {key: sanitize_input(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    else:
        return data

def validate_and_sanitize(data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize data according to schema"""
    validated_data = {}
    
    for field, field_config in schema.items():
        if field in data:
            value = data[field]
            
            # Apply validators based on field configuration
            if "type" in field_config:
                if field_config["type"] == "email":
                    value = validator.validate_email(value)
                elif field_config["type"] == "date":
                    value = validator.validate_date(value)
                elif field_config["type"] == "time":
                    value = validator.validate_time(value)
                elif field_config["type"] == "url":
                    value = validator.validate_url(value)
                elif field_config["type"] == "integer":
                    value = validator.validate_integer(value)
                elif field_config["type"] == "float":
                    value = validator.validate_float(value)
            
            # Apply length validation
            if "max_length" in field_config:
                if isinstance(value, str) and len(value) > field_config["max_length"]:
                    raise ValidationError(field, f"Value exceeds maximum length of {field_config['max_length']} characters")
            
            # Apply range validation
            if "min_value" in field_config or "max_value" in field_config:
                if isinstance(value, (int, float)):
                    if "min_value" in field_config and value < field_config["min_value"]:
                        raise ValidationError(field, f"Value must be at least {field_config['min_value']}")
                    if "max_value" in field_config and value > field_config["max_value"]:
                        raise ValidationError(field, f"Value must be at most {field_config['max_value']}")
            
            validated_data[field] = value
    
    return validated_data
