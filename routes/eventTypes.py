"""
Event Types Routes Module

This module contains all the event type-related API endpoints for the Travel Planner application.
Routes handle CRUD operations for event types including soft delete and restore functionality.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, date
from pydantic import BaseModel, Field
import re

# Import database connection
from database.db import fetch_all, fetch_one, execute_query, execute_insert

# Import validation middleware
from middleware.validation import validate_request_data, sanitize_input

# Import error handling utilities
from middleware.error_handler import CustomHTTPException, create_error_response, log_error

# Import logging utilities
from middleware.logger import log_user_action, log_business_event

# Setup router
router = APIRouter(
    prefix="/event-types",
    tags=["event-types"],
    responses={
        404: {"description": "Event type not found"},
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"}
    }
)

# Setup logging
logger = logging.getLogger(__name__)

# Predefined categories for event types
ALLOWED_CATEGORIES = [
    "accommodation", "transportation", "activity", "food", "shopping", 
    "entertainment", "health", "business", "education", "other"
]

# Pydantic models for request/response
class EventTypeResponse(BaseModel):
    id: int
    name: str
    category: str
    color: str
    icon: Optional[str] = None
    created_at: str
    updated_at: str

class DeletedEventTypeResponse(BaseModel):
    id: int
    name: str
    category: str
    color: str
    icon: Optional[str] = None
    is_deleted: int
    deleted_at: str
    created_at: str

class CreateEventTypeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Event type name")
    category: str = Field(..., min_length=1, max_length=50, description="Event type category")
    color: str = Field(..., description="Hex color code (#RRGGBB)")
    icon: Optional[str] = Field(None, max_length=10, description="Event type icon (emoji)")

class UpdateEventTypeRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Event type name")
    category: Optional[str] = Field(None, min_length=1, max_length=50, description="Event type category")
    color: Optional[str] = Field(None, description="Hex color code (#RRGGBB)")
    icon: Optional[str] = Field(None, max_length=10, description="Event type icon (emoji)")

class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    pages: int

class EventTypeListResponse(BaseModel):
    success: bool = True
    data: List[EventTypeResponse]
    pagination: PaginationInfo

class DeletedEventTypeListResponse(BaseModel):
    success: bool = True
    data: List[DeletedEventTypeResponse]
    pagination: PaginationInfo

class CreateEventTypeResponse(BaseModel):
    success: bool = True
    data: EventTypeResponse
    message: str = "Event type created successfully"

class UpdateEventTypeResponse(BaseModel):
    success: bool = True
    data: EventTypeResponse
    message: str = "Event type updated successfully"

class SoftDeleteEventTypeResponse(BaseModel):
    success: bool = True
    message: str = "Event type soft deleted successfully"
    deletedAt: str

class RestoreEventTypeResponse(BaseModel):
    success: bool = True
    data: EventTypeResponse
    message: str = "Event type restored successfully"

class SingleEventTypeResponse(BaseModel):
    id: int
    name: str
    category: str
    color: str
    icon: Optional[str] = None
    usage_count: int = 0
    created_at: str
    updated_at: str

class GetEventTypeResponse(BaseModel):
    success: bool = True
    data: SingleEventTypeResponse

# Validation functions
def validate_hex_color(color: str) -> bool:
    """Validate hex color format (#RRGGBB)"""
    pattern = r'^#[0-9A-Fa-f]{6}$'
    return bool(re.match(pattern, color))

def validate_category(category: str) -> bool:
    """Validate event type category"""
    return category.lower() in [cat.lower() for cat in ALLOWED_CATEGORIES]

def validate_icon(icon: Optional[str]) -> bool:
    """Validate icon (basic emoji check)"""
    if icon is None:
        return True
    # Basic emoji validation - check if it's a single character or emoji sequence
    return len(icon) <= 10 and not icon.strip() == ""

# Health check endpoint for event types module
@router.get("/health", include_in_schema=False)
async def event_types_health_check():
    """
    Health check endpoint for the event types module.
    
    Returns:
        Health status of the event types module
    """
    return {
        "status": "healthy",
        "module": "event_types",
        "endpoints": [
            "GET /",
            "GET /deleted",
            "POST /",
            "GET /{id}",
            "PUT /{id}",
            "DELETE /{id}",
            "POST /{id}/restore"
        ]
    }

# Route: GET / - List all active event types
@router.get("/", response_model=EventTypeListResponse)
async def list_event_types(
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of event types to return"),
    offset: int = Query(0, ge=0, description="Number of event types to skip"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    List all active event types.
    
    Args:
        request: FastAPI request object
        limit: Maximum number of event types to return (1-100, default: 10)
        offset: Number of event types to skip (default: 0)
        category: Filter by category
    
    Returns:
        Paginated list of active event types
    """
    try:
        # Log the request
        logger.info(f"Listing event types - limit: {limit}, offset: {offset}, category: {category}")
        
        # Build the WHERE clause for filtering
        where_conditions = ["is_deleted = 0"]
        query_params = []
        
        if category:
            # Validate category
            if not validate_category(category):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category. Allowed categories: {', '.join(ALLOWED_CATEGORIES)}"
                )
            where_conditions.append("LOWER(category) = ?")
            query_params.append(category.lower())
        
        where_clause = " AND ".join(where_conditions)
        
        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(*) as total
            FROM event_types 
            WHERE {where_clause}
        """
        count_result = fetch_one(count_query, tuple(query_params))
        total_count = count_result["total"] if count_result else 0
        
        # Calculate pagination info
        page = (offset // limit) + 1
        total_pages = (total_count + limit - 1) // limit
        
        # Get event types with pagination
        event_types_query = f"""
            SELECT id, name, category, color, icon, created_at, updated_at
            FROM event_types 
            WHERE {where_clause}
            ORDER BY category ASC, name ASC
            LIMIT ? OFFSET ?
        """
        
        # Add pagination parameters
        query_params.extend([limit, offset])
        
        # Execute query
        event_types_data = fetch_all(event_types_query, tuple(query_params))
        
        # Transform data to response format
        event_types = []
        for event_type in event_types_data:
            event_types.append(EventTypeResponse(
                id=event_type["id"],
                name=event_type["name"],
                category=event_type["category"],
                color=event_type["color"],
                icon=event_type["icon"],
                created_at=event_type["created_at"],
                updated_at=event_type["updated_at"]
            ))
        
        # Create pagination info
        pagination = PaginationInfo(
            page=page,
            limit=limit,
            total=total_count,
            pages=total_pages
        )
        
        # Create response
        response = EventTypeListResponse(
            success=True,
            data=event_types,
            pagination=pagination
        )
        
        # Log the response
        logger.info(f"Successfully listed {len(event_types)} event types out of {total_count} total")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {
            "endpoint": "list_event_types", 
            "limit": limit, 
            "offset": offset,
            "category": category
        })
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list event types"
        )

# Route: GET /deleted - List deleted event types
@router.get("/deleted", response_model=DeletedEventTypeListResponse)
async def list_deleted_event_types(
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of deleted event types to return"),
    offset: int = Query(0, ge=0, description="Number of deleted event types to skip")
):
    """
    List all deleted event types.
    
    Args:
        request: FastAPI request object
        limit: Maximum number of deleted event types to return (1-100, default: 10)
        offset: Number of deleted event types to skip (default: 0)
    
    Returns:
        Paginated list of deleted event types
    """
    try:
        # Log the request
        logger.info(f"Listing deleted event types - limit: {limit}, offset: {offset}")
        
        # Get total count for pagination
        count_query = """
            SELECT COUNT(*) as total
            FROM event_types 
            WHERE is_deleted = 1
        """
        count_result = fetch_one(count_query)
        total_count = count_result["total"] if count_result else 0
        
        # Calculate pagination info
        page = (offset // limit) + 1
        total_pages = (total_count + limit - 1) // limit
        
        # Get deleted event types with pagination
        event_types_query = """
            SELECT id, name, category, color, icon, is_deleted, deleted_at, created_at
            FROM event_types 
            WHERE is_deleted = 1
            ORDER BY deleted_at DESC
            LIMIT ? OFFSET ?
        """
        
        # Execute query
        event_types_data = fetch_all(event_types_query, (limit, offset))
        
        # Transform data to response format
        deleted_event_types = []
        for event_type in event_types_data:
            deleted_event_types.append(DeletedEventTypeResponse(
                id=event_type["id"],
                name=event_type["name"],
                category=event_type["category"],
                color=event_type["color"],
                icon=event_type["icon"],
                is_deleted=event_type["is_deleted"],
                deleted_at=event_type["deleted_at"],
                created_at=event_type["created_at"]
            ))
        
        # Create pagination info
        pagination = PaginationInfo(
            page=page,
            limit=limit,
            total=total_count,
            pages=total_pages
        )
        
        # Create response
        response = DeletedEventTypeListResponse(
            success=True,
            data=deleted_event_types,
            pagination=pagination
        )
        
        # Log the response
        logger.info(f"Successfully listed {len(deleted_event_types)} deleted event types out of {total_count} total")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {
            "endpoint": "list_deleted_event_types", 
            "limit": limit, 
            "offset": offset
        })
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list deleted event types"
        )

# Route: POST / - Create new event type
@router.post("/", response_model=CreateEventTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_event_type(
    request: Request,
    event_type_data: CreateEventTypeRequest
):
    """
    Create a new event type.
    
    Args:
        request: FastAPI request object
        event_type_data: Validated event type data from request body
    
    Returns:
        Created event type information with success message
    
    Raises:
        HTTPException: For validation errors or database failures
    """
    try:
        # Log the request
        logger.info(f"Creating event type - data: {event_type_data.dict()}")
        
        # Validate hex color format
        if not validate_hex_color(event_type_data.color):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid color format. Use hex color format (#RRGGBB)"
            )
        
        # Validate category
        if not validate_category(event_type_data.category):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Allowed categories: {', '.join(ALLOWED_CATEGORIES)}"
            )
        
        # Validate icon if provided
        if event_type_data.icon and not validate_icon(event_type_data.icon):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid icon format. Use emoji or single character (max 10 chars)"
            )
        
        # Sanitize input data
        sanitized_name = sanitize_input(event_type_data.name) if event_type_data.name else ""
        sanitized_category = sanitize_input(event_type_data.category) if event_type_data.category else ""
        sanitized_icon = sanitize_input(event_type_data.icon) if event_type_data.icon else None
        
        # Validate sanitized data
        if not sanitized_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name cannot be empty after sanitization"
            )
        
        if not sanitized_category.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be empty after sanitization"
            )
        
        # Check for duplicate name in the same category
        duplicate_query = """
            SELECT id, name, category
            FROM event_types 
            WHERE LOWER(name) = LOWER(?) AND LOWER(category) = LOWER(?) AND is_deleted = 0
        """
        
        duplicate_result = fetch_one(duplicate_query, (sanitized_name, sanitized_category))
        
        if duplicate_result:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Event type with name '{sanitized_name}' already exists in category '{sanitized_category}'"
            )
        
        # Prepare data for database insertion
        insert_data = {
            "name": sanitized_name,
            "category": sanitized_category.lower(),
            "color": event_type_data.color,
            "icon": sanitized_icon,
            "is_deleted": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Insert into database
        insert_query = """
            INSERT INTO event_types (name, category, color, icon, is_deleted, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        insert_params = (
            insert_data["name"],
            insert_data["category"],
            insert_data["color"],
            insert_data["icon"],
            insert_data["is_deleted"],
            insert_data["created_at"],
            insert_data["updated_at"]
        )
        
        # Execute insert query
        event_type_id = execute_insert(insert_query, insert_params)
        
        if not event_type_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create event type - no ID returned"
            )
        
        # Fetch the created event type to return
        fetch_query = """
            SELECT id, name, category, color, icon, created_at, updated_at
            FROM event_types 
            WHERE id = ?
        """
        
        created_event_type_data = fetch_one(fetch_query, (event_type_id,))
        
        if not created_event_type_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch created event type"
            )
        
        # Create response object
        created_event_type = EventTypeResponse(
            id=created_event_type_data["id"],
            name=created_event_type_data["name"],
            category=created_event_type_data["category"],
            color=created_event_type_data["color"],
            icon=created_event_type_data["icon"],
            created_at=created_event_type_data["created_at"],
            updated_at=created_event_type_data["updated_at"]
        )
        
        # Log the business event
        log_business_event("event_type_created", "event_type", str(event_type_id), {
            "name": sanitized_name,
            "category": sanitized_category,
            "color": event_type_data.color
        })
        
        # Log the response
        logger.info(f"Successfully created event type with ID: {event_type_id}")
        
        # Create and return response
        response = CreateEventTypeResponse(
            success=True,
            data=created_event_type,
            message="Event type created successfully"
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {
            "endpoint": "create_event_type", 
            "event_type_data": event_type_data.dict() if hasattr(event_type_data, 'dict') else str(event_type_data)
        })
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create event type"
        )

# Route: GET /:id - Get single event type
@router.get("/{event_type_id}", response_model=GetEventTypeResponse)
async def get_event_type(
    request: Request,
    event_type_id: int
):
    """
    Get a single event type by ID.
    
    Args:
        request: FastAPI request object
        event_type_id: ID of the event type to retrieve
    
    Returns:
        Event type information with usage count
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Getting event type with ID: {event_type_id}")
        
        # Validate event_type_id parameter
        if event_type_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event type ID must be a positive integer"
            )
        
        # Query database for event type
        event_type_query = """
            SELECT id, name, category, color, icon, is_deleted, created_at, updated_at
            FROM event_types 
            WHERE id = ?
        """
        
        event_type_data = fetch_one(event_type_query, (event_type_id,))
        
        # Check if event type exists
        if not event_type_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event type with ID {event_type_id} not found"
            )
        
        # Check if event type is soft deleted
        if event_type_data["is_deleted"] == 1:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Event type with ID {event_type_id} has been deleted"
            )
        
        # Get usage count (how many events use this type)
        usage_count_query = """
            SELECT COUNT(*) as count
            FROM events 
            WHERE event_type_id = ? AND is_deleted = 0
        """
        
        usage_count_result = fetch_one(usage_count_query, (event_type_id,))
        usage_count = usage_count_result["count"] if usage_count_result else 0
        
        # Create response object
        event_type = SingleEventTypeResponse(
            id=event_type_data["id"],
            name=event_type_data["name"],
            category=event_type_data["category"],
            color=event_type_data["color"],
            icon=event_type_data["icon"],
            usage_count=usage_count,
            created_at=event_type_data["created_at"],
            updated_at=event_type_data["updated_at"]
        )
        
        # Log the response
        logger.info(f"Successfully retrieved event type with ID: {event_type_id}, usage count: {usage_count}")
        
        # Create and return response
        response = GetEventTypeResponse(
            success=True,
            data=event_type
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {"endpoint": "get_event_type", "event_type_id": event_type_id})
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event type"
        )

# Route: PUT /:id - Update event type
@router.put("/{event_type_id}", response_model=UpdateEventTypeResponse)
async def update_event_type(
    request: Request,
    event_type_id: int,
    event_type_data: UpdateEventTypeRequest
):
    """
    Update an existing event type.
    
    Args:
        request: FastAPI request object
        event_type_id: ID of the event type to update
        event_type_data: Validated event type update data from request body
    
    Returns:
        Updated event type information with success message
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Updating event type with ID: {event_type_id} - data: {event_type_data.dict(exclude_unset=True)}")
        
        # Validate event_type_id parameter
        if event_type_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event type ID must be a positive integer"
            )
        
        # Check if event type exists and is not deleted
        event_type_query = """
            SELECT id, name, category, is_deleted
            FROM event_types 
            WHERE id = ?
        """
        
        existing_event_type = fetch_one(event_type_query, (event_type_id,))
        
        if not existing_event_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event type with ID {event_type_id} not found"
            )
        
        if existing_event_type["is_deleted"] == 1:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Event type with ID {event_type_id} has been deleted"
            )
        
        # Prepare update data - only include fields that were provided
        update_fields = []
        update_params = []
        
        # Handle name update
        if event_type_data.name is not None:
            sanitized_name = sanitize_input(event_type_data.name)
            if not sanitized_name.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Name cannot be empty after sanitization"
                )
            update_fields.append("name = ?")
            update_params.append(sanitized_name)
        
        # Handle category update
        if event_type_data.category is not None:
            sanitized_category = sanitize_input(event_type_data.category)
            if not sanitized_category.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category cannot be empty after sanitization"
                )
            
            # Validate category
            if not validate_category(sanitized_category):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category. Allowed categories: {', '.join(ALLOWED_CATEGORIES)}"
                )
            
            update_fields.append("category = ?")
            update_params.append(sanitized_category.lower())
        
        # Handle color update
        if event_type_data.color is not None:
            # Validate hex color format
            if not validate_hex_color(event_type_data.color):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid color format. Use hex color format (#RRGGBB)"
                )
            update_fields.append("color = ?")
            update_params.append(event_type_data.color)
        
        # Handle icon update
        if event_type_data.icon is not None:
            sanitized_icon = sanitize_input(event_type_data.icon)
            # Validate icon
            if not validate_icon(sanitized_icon):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid icon format. Use emoji or single character (max 10 chars)"
                )
            update_fields.append("icon = ?")
            update_params.append(sanitized_icon)
        
        # Check if any fields were provided for update
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update"
            )
        
        # Check for duplicate name in the same category if name or category is being updated
        if event_type_data.name is not None or event_type_data.category is not None:
            effective_name = event_type_data.name if event_type_data.name else existing_event_type["name"]
            effective_category = event_type_data.category if event_type_data.category else existing_event_type["category"]
            
            duplicate_query = """
                SELECT id, name, category
                FROM event_types 
                WHERE LOWER(name) = LOWER(?) AND LOWER(category) = LOWER(?) AND is_deleted = 0 AND id != ?
            """
            
            duplicate_result = fetch_one(duplicate_query, (effective_name, effective_category, event_type_id))
            
            if duplicate_result:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Event type with name '{effective_name}' already exists in category '{effective_category}'"
                )
        
        # Add updated_at timestamp
        update_fields.append("updated_at = ?")
        update_params.append(datetime.now().isoformat())
        
        # Add event_type_id to params for WHERE clause
        update_params.append(event_type_id)
        
        # Build and execute update query
        update_query = f"""
            UPDATE event_types 
            SET {', '.join(update_fields)}
            WHERE id = ?
        """
        
        # Execute update query
        affected_rows = execute_query(update_query, tuple(update_params))
        
        if affected_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update event type - no rows affected"
            )
        
        # Fetch the updated event type
        updated_event_type_query = """
            SELECT id, name, category, color, icon, created_at, updated_at
            FROM event_types 
            WHERE id = ?
        """
        
        updated_event_type_data = fetch_one(updated_event_type_query, (event_type_id,))
        
        if not updated_event_type_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch updated event type"
            )
        
        # Create response object
        updated_event_type = EventTypeResponse(
            id=updated_event_type_data["id"],
            name=updated_event_type_data["name"],
            category=updated_event_type_data["category"],
            color=updated_event_type_data["color"],
            icon=updated_event_type_data["icon"],
            created_at=updated_event_type_data["created_at"],
            updated_at=updated_event_type_data["updated_at"]
        )
        
        # Log the business event
        log_business_event("event_type_updated", "event_type", str(event_type_id), {
            "updated_fields": list(event_type_data.dict(exclude_unset=True).keys()),
            "name": existing_event_type["name"]
        })
        
        # Log the response
        logger.info(f"Successfully updated event type with ID: {event_type_id}")
        
        # Create and return response
        response = UpdateEventTypeResponse(
            success=True,
            data=updated_event_type,
            message="Event type updated successfully"
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {
            "endpoint": "update_event_type", 
            "event_type_id": event_type_id,
            "event_type_data": event_type_data.dict(exclude_unset=True) if hasattr(event_type_data, 'dict') else str(event_type_data)
        })
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update event type"
        )

# Route: DELETE /:id - Soft delete event type
@router.delete("/{event_type_id}", response_model=SoftDeleteEventTypeResponse)
async def delete_event_type(
    request: Request,
    event_type_id: int
):
    """
    Soft delete an event type (mark as deleted without removing from database).
    
    Args:
        request: FastAPI request object
        event_type_id: ID of the event type to delete
    
    Returns:
        Success message with deletion timestamp
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Soft deleting event type with ID: {event_type_id}")
        
        # Validate event_type_id parameter
        if event_type_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event type ID must be a positive integer"
            )
        
        # Check if event type exists and is not already deleted
        event_type_query = """
            SELECT id, name, is_deleted
            FROM event_types 
            WHERE id = ?
        """
        
        existing_event_type = fetch_one(event_type_query, (event_type_id,))
        
        if not existing_event_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event type with ID {event_type_id} not found"
            )
        
        if existing_event_type["is_deleted"] == 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Event type with ID {event_type_id} is already deleted"
            )
        
        # Check if event type is in use by any events
        usage_check_query = """
            SELECT COUNT(*) as count
            FROM events 
            WHERE event_type_id = ? AND is_deleted = 0
        """
        
        usage_check_result = fetch_one(usage_check_query, (event_type_id,))
        usage_count = usage_check_result["count"] if usage_check_result else 0
        
        if usage_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete event type '{existing_event_type['name']}' - it is used by {usage_count} active events"
            )
        
        # Get current timestamp for deletion
        current_timestamp = datetime.now().isoformat()
        
        # Soft delete the event type
        delete_query = """
            UPDATE event_types 
            SET is_deleted = 1, 
                deleted_at = ?, 
                updated_at = ?
            WHERE id = ?
        """
        
        delete_params = (current_timestamp, current_timestamp, event_type_id)
        
        # Execute soft delete query
        affected_rows = execute_query(delete_query, delete_params)
        
        if affected_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to soft delete event type - no rows affected"
            )
        
        # Log the business event
        log_business_event("event_type_deleted", "event_type", str(event_type_id), {
            "deleted_at": current_timestamp,
            "name": existing_event_type["name"],
            "usage_count": usage_count
        })
        
        # Log the response
        logger.info(f"Successfully soft deleted event type with ID: {event_type_id} at {current_timestamp}")
        
        # Create and return response
        response = SoftDeleteEventTypeResponse(
            success=True,
            message="Event type soft deleted successfully",
            deletedAt=current_timestamp
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {"endpoint": "delete_event_type", "event_type_id": event_type_id})
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete event type"
        )

# Route: POST /:id/restore - Restore deleted event type
@router.post("/{event_type_id}/restore", response_model=RestoreEventTypeResponse)
async def restore_event_type(
    request: Request,
    event_type_id: int
):
    """
    Restore a previously deleted event type.
    
    Args:
        request: FastAPI request object
        event_type_id: ID of the event type to restore
    
    Returns:
        Restored event type information with success message
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Restoring event type with ID: {event_type_id}")
        
        # Validate event_type_id parameter
        if event_type_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event type ID must be a positive integer"
            )
        
        # Check if event type exists and is deleted
        event_type_query = """
            SELECT id, name, is_deleted
            FROM event_types 
            WHERE id = ?
        """
        
        existing_event_type = fetch_one(event_type_query, (event_type_id,))
        
        if not existing_event_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event type with ID {event_type_id} not found"
            )
        
        if existing_event_type["is_deleted"] == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Event type with ID {event_type_id} is not deleted"
            )
        
        # Get current timestamp for restoration
        current_timestamp = datetime.now().isoformat()
        
        # Restore the event type
        restore_query = """
            UPDATE event_types 
            SET is_deleted = 0, 
                deleted_at = NULL, 
                updated_at = ?
            WHERE id = ?
        """
        
        restore_params = (current_timestamp, event_type_id)
        
        # Execute restore query
        affected_rows = execute_query(restore_query, restore_params)
        
        if affected_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restore event type - no rows affected"
            )
        
        # Fetch the restored event type
        restored_event_type_query = """
            SELECT id, name, category, color, icon, created_at, updated_at
            FROM event_types 
            WHERE id = ?
        """
        
        restored_event_type_data = fetch_one(restored_event_type_query, (event_type_id,))
        
        if not restored_event_type_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch restored event type"
            )
        
        # Create response object
        restored_event_type = EventTypeResponse(
            id=restored_event_type_data["id"],
            name=restored_event_type_data["name"],
            category=restored_event_type_data["category"],
            color=restored_event_type_data["color"],
            icon=restored_event_type_data["icon"],
            created_at=restored_event_type_data["created_at"],
            updated_at=restored_event_type_data["updated_at"]
        )
        
        # Log the business event
        log_business_event("event_type_restored", "event_type", str(event_type_id), {
            "restored_at": current_timestamp,
            "name": existing_event_type["name"]
        })
        
        # Log the response
        logger.info(f"Successfully restored event type with ID: {event_type_id} at {current_timestamp}")
        
        # Create and return response
        response = RestoreEventTypeResponse(
            success=True,
            data=restored_event_type,
            message="Event type restored successfully"
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {"endpoint": "restore_event_type", "event_type_id": event_type_id})
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore event type"
        )
