"""
Event Routes Module

This module contains all the event-related API endpoints for the Travel Planner application.
Routes handle CRUD operations for events including soft delete and restore functionality.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, date
from pydantic import BaseModel, Field

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
    prefix="/events",
    tags=["events"],
    responses={
        404: {"description": "Event not found"},
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"}
    }
)

# Setup logging
logger = logging.getLogger(__name__)

# Pydantic models for request/response
class EventResponse(BaseModel):
    id: int
    travel_id: int
    title: str
    description: Optional[str] = None
    event_type_id: int
    event_type_name: Optional[str] = None
    event_type_color: Optional[str] = None
    event_type_icon: Optional[str] = None
    start_datetime: str
    end_datetime: str
    location: Optional[str] = None
    created_at: str
    updated_at: str

class DeletedEventResponse(BaseModel):
    id: int
    travel_id: int
    title: str
    description: Optional[str] = None
    event_type_id: int
    event_type_name: Optional[str] = None
    event_type_color: Optional[str] = None
    event_type_icon: Optional[str] = None
    start_datetime: str
    end_datetime: str
    location: Optional[str] = None
    is_deleted: int
    deleted_at: str
    created_at: str

class CreateEventRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Event title")
    description: Optional[str] = Field(None, max_length=1000, description="Event description")
    event_type_id: int = Field(..., description="Event type ID")
    start_datetime: str = Field(..., description="Start datetime in ISO format")
    end_datetime: str = Field(..., description="End datetime in ISO format")
    location: Optional[str] = Field(None, max_length=255, description="Event location")

class UpdateEventRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Event title")
    description: Optional[str] = Field(None, max_length=1000, description="Event description")
    event_type_id: Optional[int] = Field(None, description="Event type ID")
    start_datetime: Optional[str] = Field(None, description="Start datetime in ISO format")
    end_datetime: Optional[str] = Field(None, description="End datetime in ISO format")
    location: Optional[str] = Field(None, max_length=255, description="Event location")

class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    pages: int

class EventListResponse(BaseModel):
    success: bool = True
    data: List[EventResponse]
    pagination: PaginationInfo

class DeletedEventListResponse(BaseModel):
    success: bool = True
    data: List[DeletedEventResponse]
    pagination: PaginationInfo

class CreateEventResponse(BaseModel):
    success: bool = True
    data: EventResponse
    message: str = "Event created successfully"

class UpdateEventResponse(BaseModel):
    success: bool = True
    data: EventResponse
    message: str = "Event updated successfully"

class SoftDeleteEventResponse(BaseModel):
    success: bool = True
    message: str = "Event soft deleted successfully"
    deletedAt: str

class RestoreEventResponse(BaseModel):
    success: bool = True
    data: EventResponse
    message: str = "Event restored successfully"

class SingleEventResponse(BaseModel):
    id: int
    travel_id: int
    title: str
    description: Optional[str] = None
    event_type_id: int
    event_type_name: Optional[str] = None
    event_type_color: Optional[str] = None
    event_type_icon: Optional[str] = None
    start_datetime: str
    end_datetime: str
    location: Optional[str] = None
    created_at: str
    updated_at: str

class GetEventResponse(BaseModel):
    success: bool = True
    data: SingleEventResponse

# Health check endpoint for events module
@router.get("/health", include_in_schema=False)
async def events_health_check():
    """
    Health check endpoint for the events module.
    
    Returns:
        Health status of the events module
    """
    return {
        "status": "healthy",
        "module": "events",
        "endpoints": [
            "GET /travels/{id}/events",
            "GET /travels/{id}/events/deleted",
            "POST /travels/{id}/events",
            "GET /{id}",
            "PUT /{id}",
            "DELETE /{id}",
            "POST /{id}/restore"
        ]
    }

# Route: GET /travels/:id/events - List active events for travel
@router.get("/travels/{travel_id}/events", response_model=EventListResponse)
async def list_travel_events(
    request: Request,
    travel_id: int,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    start_date_from: Optional[str] = Query(None, description="Filter by start date from (YYYY-MM-DD)"),
    start_date_to: Optional[str] = Query(None, description="Filter by start date to (YYYY-MM-DD)"),
    event_type_id: Optional[int] = Query(None, description="Filter by event type ID"),
    location: Optional[str] = Query(None, description="Filter by location (partial match)")
):
    """
    List all active events for a specific travel.
    
    Args:
        request: FastAPI request object
        travel_id: ID of the travel
        limit: Maximum number of events to return (1-100, default: 10)
        offset: Number of events to skip (default: 0)
        start_date_from: Filter by start date from (YYYY-MM-DD)
        start_date_to: Filter by start date to (YYYY-MM-DD)
        event_type_id: Filter by event type ID
        location: Filter by location (partial match)
    
    Returns:
        Paginated list of active events for the travel
    """
    try:
        # Log the request
        logger.info(f"Listing events for travel ID: {travel_id} - limit: {limit}, offset: {offset}")
        
        # Validate travel_id parameter
        if travel_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Travel ID must be a positive integer"
            )
        
        # Check if travel exists and is not deleted
        travel_query = """
            SELECT id, title, is_deleted
            FROM travels 
            WHERE id = ?
        """
        
        travel_data = fetch_one(travel_query, (travel_id,))
        
        if not travel_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Travel with ID {travel_id} not found"
            )
        
        if travel_data["is_deleted"] == 1:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Travel with ID {travel_id} has been deleted"
            )
        
        # Build the WHERE clause for filtering
        where_conditions = ["e.travel_id = ?", "e.is_deleted = 0"]
        query_params = [travel_id]
        
        if start_date_from:
            try:
                datetime.strptime(start_date_from, "%Y-%m-%d")
                where_conditions.append("date(e.start_datetime) >= ?")
                query_params.append(start_date_from)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date_from format. Use YYYY-MM-DD"
                )
        
        if start_date_to:
            try:
                datetime.strptime(start_date_to, "%Y-%m-%d")
                where_conditions.append("date(e.start_datetime) <= ?")
                query_params.append(start_date_to)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date_to format. Use YYYY-MM-DD"
                )
        
        if event_type_id:
            where_conditions.append("e.event_type_id = ?")
            query_params.append(event_type_id)
        
        if location:
            where_conditions.append("e.location LIKE ?")
            query_params.append(f"%{location}%")
        
        where_clause = " AND ".join(where_conditions)
        
        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(*) as total
            FROM events e
            WHERE {where_clause}
        """
        count_result = fetch_one(count_query, tuple(query_params))
        total_count = count_result["total"] if count_result else 0
        
        # Calculate pagination info
        page = (offset // limit) + 1
        total_pages = (total_count + limit - 1) // limit
        
        # Get events with pagination
        events_query = f"""
            SELECT e.id, e.travel_id, e.title, e.description, e.event_type_id,
                   et.name as event_type_name, et.color as event_type_color, et.icon as event_type_icon,
                   e.start_datetime, e.end_datetime, e.location, e.created_at, e.updated_at
            FROM events e
            LEFT JOIN event_types et ON e.event_type_id = et.id
            WHERE {where_clause}
            ORDER BY e.start_datetime ASC
            LIMIT ? OFFSET ?
        """
        
        # Add pagination parameters
        query_params.extend([limit, offset])
        
        # Execute query
        events_data = fetch_all(events_query, tuple(query_params))
        
        # Transform data to response format
        events = []
        for event in events_data:
            events.append(EventResponse(
                id=event["id"],
                travel_id=event["travel_id"],
                title=event["title"],
                description=event["description"],
                event_type_id=event["event_type_id"],
                event_type_name=event["event_type_name"],
                event_type_color=event["event_type_color"],
                event_type_icon=event["event_type_icon"],
                start_datetime=event["start_datetime"],
                end_datetime=event["end_datetime"],
                location=event["location"],
                created_at=event["created_at"],
                updated_at=event["updated_at"]
            ))
        
        # Create pagination info
        pagination = PaginationInfo(
            page=page,
            limit=limit,
            total=total_count,
            pages=total_pages
        )
        
        # Create response
        response = EventListResponse(
            success=True,
            data=events,
            pagination=pagination
        )
        
        # Log the response
        logger.info(f"Successfully listed {len(events)} events for travel ID {travel_id} out of {total_count} total")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {
            "endpoint": "list_travel_events", 
            "travel_id": travel_id,
            "limit": limit, 
            "offset": offset
        })
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list events"
        )

# Route: GET /travels/:id/events/deleted - List deleted events for travel
@router.get("/travels/{travel_id}/events/deleted", response_model=DeletedEventListResponse)
async def list_travel_deleted_events(
    request: Request,
    travel_id: int,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of deleted events to return"),
    offset: int = Query(0, ge=0, description="Number of deleted events to skip")
):
    """
    List all deleted events for a specific travel.
    
    Args:
        request: FastAPI request object
        travel_id: ID of the travel
        limit: Maximum number of deleted events to return (1-100, default: 10)
        offset: Number of deleted events to skip (default: 0)
    
    Returns:
        Paginated list of deleted events for the travel
    """
    try:
        # Log the request
        logger.info(f"Listing deleted events for travel ID: {travel_id} - limit: {limit}, offset: {offset}")
        
        # Validate travel_id parameter
        if travel_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Travel ID must be a positive integer"
            )
        
        # Check if travel exists
        travel_query = """
            SELECT id, title, is_deleted
            FROM travels 
            WHERE id = ?
        """
        
        travel_data = fetch_one(travel_query, (travel_id,))
        
        if not travel_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Travel with ID {travel_id} not found"
            )
        
        # Get total count for pagination
        count_query = """
            SELECT COUNT(*) as total
            FROM events e
            WHERE e.travel_id = ? AND e.is_deleted = 1
        """
        count_result = fetch_one(count_query, (travel_id,))
        total_count = count_result["total"] if count_result else 0
        
        # Calculate pagination info
        page = (offset // limit) + 1
        total_pages = (total_count + limit - 1) // limit
        
        # Get deleted events with pagination
        events_query = """
            SELECT e.id, e.travel_id, e.title, e.description, e.event_type_id,
                   et.name as event_type_name, et.color as event_type_color, et.icon as event_type_icon,
                   e.start_datetime, e.end_datetime, e.location, e.is_deleted, e.deleted_at, e.created_at
            FROM events e
            LEFT JOIN event_types et ON e.event_type_id = et.id
            WHERE e.travel_id = ? AND e.is_deleted = 1
            ORDER BY e.deleted_at DESC
            LIMIT ? OFFSET ?
        """
        
        # Execute query
        events_data = fetch_all(events_query, (travel_id, limit, offset))
        
        # Transform data to response format
        deleted_events = []
        for event in events_data:
            deleted_events.append(DeletedEventResponse(
                id=event["id"],
                travel_id=event["travel_id"],
                title=event["title"],
                description=event["description"],
                event_type_id=event["event_type_id"],
                event_type_name=event["event_type_name"],
                event_type_color=event["event_type_color"],
                event_type_icon=event["event_type_icon"],
                start_datetime=event["start_datetime"],
                end_datetime=event["end_datetime"],
                location=event["location"],
                is_deleted=event["is_deleted"],
                deleted_at=event["deleted_at"],
                created_at=event["created_at"]
            ))
        
        # Create pagination info
        pagination = PaginationInfo(
            page=page,
            limit=limit,
            total=total_count,
            pages=total_pages
        )
        
        # Create response
        response = DeletedEventListResponse(
            success=True,
            data=deleted_events,
            pagination=pagination
        )
        
        # Log the response
        logger.info(f"Successfully listed {len(deleted_events)} deleted events for travel ID {travel_id} out of {total_count} total")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {
            "endpoint": "list_travel_deleted_events", 
            "travel_id": travel_id,
            "limit": limit, 
            "offset": offset
        })
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list deleted events"
        )

# Route: POST /travels/:id/events - Create new event for travel
@router.post("/travels/{travel_id}/events", response_model=CreateEventResponse, status_code=status.HTTP_201_CREATED)
async def create_travel_event(
    request: Request,
    travel_id: int,
    event_data: CreateEventRequest
):
    """
    Create a new event for a specific travel.
    
    Args:
        request: FastAPI request object
        travel_id: ID of the travel
        event_data: Validated event data from request body
    
    Returns:
        Created event information with success message
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Creating event for travel ID: {travel_id} - data: {event_data.dict()}")
        
        # Validate travel_id parameter
        if travel_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Travel ID must be a positive integer"
            )
        
        # Check if travel exists and is not deleted
        travel_query = """
            SELECT id, title, is_deleted
            FROM travels 
            WHERE id = ?
        """
        
        travel_data = fetch_one(travel_query, (travel_id,))
        
        if not travel_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Travel with ID {travel_id} not found"
            )
        
        if travel_data["is_deleted"] == 1:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Travel with ID {travel_id} has been deleted"
            )
        
        # Validate event type exists
        event_type_query = """
            SELECT id, name
            FROM event_types 
            WHERE id = ? AND is_deleted = 0
        """
        
        event_type_data = fetch_one(event_type_query, (event_data.event_type_id,))
        
        if not event_type_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event type with ID {event_data.event_type_id} not found or deleted"
            )
        
        # Validate and parse datetimes
        try:
            start_datetime = datetime.fromisoformat(event_data.start_datetime.replace('Z', '+00:00'))
            end_datetime = datetime.fromisoformat(event_data.end_datetime.replace('Z', '+00:00'))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid datetime format. Use ISO format. Error: {str(e)}"
            )
        
        # Validate datetime logic
        if start_datetime >= end_datetime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_datetime must be before end_datetime"
            )
        
        # Sanitize input data
        sanitized_title = sanitize_input(event_data.title) if event_data.title else ""
        sanitized_description = sanitize_input(event_data.description) if event_data.description else None
        sanitized_location = sanitize_input(event_data.location) if event_data.location else None
        
        # Validate sanitized data
        if not sanitized_title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title cannot be empty after sanitization"
            )
        
        # Prepare data for database insertion
        insert_data = {
            "travel_id": travel_id,
            "title": sanitized_title,
            "description": sanitized_description,
            "event_type_id": event_data.event_type_id,
            "start_datetime": event_data.start_datetime,
            "end_datetime": event_data.end_datetime,
            "location": sanitized_location,
            "is_deleted": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Insert into database
        insert_query = """
            INSERT INTO events (travel_id, title, description, event_type_id, start_datetime, end_datetime, location, is_deleted, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        insert_params = (
            insert_data["travel_id"],
            insert_data["title"],
            insert_data["description"],
            insert_data["event_type_id"],
            insert_data["start_datetime"],
            insert_data["end_datetime"],
            insert_data["location"],
            insert_data["is_deleted"],
            insert_data["created_at"],
            insert_data["updated_at"]
        )
        
        # Execute insert query
        event_id = execute_insert(insert_query, insert_params)
        
        if not event_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create event - no ID returned"
            )
        
        # Fetch the created event to return
        fetch_query = """
            SELECT e.id, e.travel_id, e.title, e.description, e.event_type_id,
                   et.name as event_type_name, et.color as event_type_color, et.icon as event_type_icon,
                   e.start_datetime, e.end_datetime, e.location, e.created_at, e.updated_at
            FROM events e
            LEFT JOIN event_types et ON e.event_type_id = et.id
            WHERE e.id = ?
        """
        
        created_event_data = fetch_one(fetch_query, (event_id,))
        
        if not created_event_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch created event"
            )
        
        # Create response object
        created_event = EventResponse(
            id=created_event_data["id"],
            travel_id=created_event_data["travel_id"],
            title=created_event_data["title"],
            description=created_event_data["description"],
            event_type_id=created_event_data["event_type_id"],
            event_type_name=created_event_data["event_type_name"],
            event_type_color=created_event_data["event_type_color"],
            event_type_icon=created_event_data["event_type_icon"],
            start_datetime=created_event_data["start_datetime"],
            end_datetime=created_event_data["end_datetime"],
            location=created_event_data["location"],
            created_at=created_event_data["created_at"],
            updated_at=created_event_data["updated_at"]
        )
        
        # Log the business event
        log_business_event("event_created", "event", str(event_id), {
            "travel_id": travel_id,
            "title": sanitized_title,
            "event_type_id": event_data.event_type_id
        })
        
        # Log the response
        logger.info(f"Successfully created event with ID: {event_id} for travel ID: {travel_id}")
        
        # Create and return response
        response = CreateEventResponse(
            success=True,
            data=created_event,
            message="Event created successfully"
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {
            "endpoint": "create_travel_event", 
            "travel_id": travel_id,
            "event_data": event_data.dict() if hasattr(event_data, 'dict') else str(event_data)
        })
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create event"
        )

# Route: GET /events/:id - Get single event
@router.get("/{event_id}", response_model=GetEventResponse)
async def get_event(
    request: Request,
    event_id: int
):
    """
    Get a single event by ID.
    
    Args:
        request: FastAPI request object
        event_id: ID of the event to retrieve
    
    Returns:
        Event information with event type details
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Getting event with ID: {event_id}")
        
        # Validate event_id parameter
        if event_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event ID must be a positive integer"
            )
        
        # Query database for event
        event_query = """
            SELECT e.id, e.travel_id, e.title, e.description, e.event_type_id,
                   et.name as event_type_name, et.color as event_type_color, et.icon as event_type_icon,
                   e.start_datetime, e.end_datetime, e.location, e.is_deleted, e.created_at, e.updated_at
            FROM events e
            LEFT JOIN event_types et ON e.event_type_id = et.id
            WHERE e.id = ?
        """
        
        event_data = fetch_one(event_query, (event_id,))
        
        # Check if event exists
        if not event_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {event_id} not found"
            )
        
        # Check if event is soft deleted
        if event_data["is_deleted"] == 1:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Event with ID {event_id} has been deleted"
            )
        
        # Create response object
        event = SingleEventResponse(
            id=event_data["id"],
            travel_id=event_data["travel_id"],
            title=event_data["title"],
            description=event_data["description"],
            event_type_id=event_data["event_type_id"],
            event_type_name=event_data["event_type_name"],
            event_type_color=event_data["event_type_color"],
            event_type_icon=event_data["event_type_icon"],
            start_datetime=event_data["start_datetime"],
            end_datetime=event_data["end_datetime"],
            location=event_data["location"],
            created_at=event_data["created_at"],
            updated_at=event_data["updated_at"]
        )
        
        # Log the response
        logger.info(f"Successfully retrieved event with ID: {event_id}")
        
        # Create and return response
        response = GetEventResponse(
            success=True,
            data=event
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {"endpoint": "get_event", "event_id": event_id})
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event"
        )

# Route: PUT /events/:id - Update event
@router.put("/{event_id}", response_model=UpdateEventResponse)
async def update_event(
    request: Request,
    event_id: int,
    event_data: UpdateEventRequest
):
    """
    Update an existing event.
    
    Args:
        request: FastAPI request object
        event_id: ID of the event to update
        event_data: Validated event update data from request body
    
    Returns:
        Updated event information with success message
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Updating event with ID: {event_id} - data: {event_data.dict(exclude_unset=True)}")
        
        # Validate event_id parameter
        if event_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event ID must be a positive integer"
            )
        
        # Check if event exists and is not deleted
        event_query = """
            SELECT id, travel_id, title, description, event_type_id, start_datetime, end_datetime, location, is_deleted
            FROM events 
            WHERE id = ?
        """
        
        existing_event = fetch_one(event_query, (event_id,))
        
        if not existing_event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {event_id} not found"
            )
        
        if existing_event["is_deleted"] == 1:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Event with ID {event_id} has been deleted"
            )
        
        # Prepare update data - only include fields that were provided
        update_fields = []
        update_params = []
        
        # Handle title update
        if event_data.title is not None:
            sanitized_title = sanitize_input(event_data.title)
            if not sanitized_title.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Title cannot be empty after sanitization"
                )
            update_fields.append("title = ?")
            update_params.append(sanitized_title)
        
        # Handle description update
        if event_data.description is not None:
            sanitized_description = sanitize_input(event_data.description)
            update_fields.append("description = ?")
            update_params.append(sanitized_description)
        
        # Handle event_type_id update
        if event_data.event_type_id is not None:
            # Validate event type exists
            event_type_query = """
                SELECT id, name
                FROM event_types 
                WHERE id = ? AND is_deleted = 0
            """
            
            event_type_data = fetch_one(event_type_query, (event_data.event_type_id,))
            
            if not event_type_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Event type with ID {event_data.event_type_id} not found or deleted"
                )
            
            update_fields.append("event_type_id = ?")
            update_params.append(event_data.event_type_id)
        
        # Handle start_datetime update
        if event_data.start_datetime is not None:
            try:
                start_datetime = datetime.fromisoformat(event_data.start_datetime.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_datetime format. Use ISO format"
                )
            update_fields.append("start_datetime = ?")
            update_params.append(event_data.start_datetime)
        
        # Handle end_datetime update
        if event_data.end_datetime is not None:
            try:
                end_datetime = datetime.fromisoformat(event_data.end_datetime.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_datetime format. Use ISO format"
                )
            update_fields.append("end_datetime = ?")
            update_params.append(event_data.end_datetime)
        
        # Handle location update
        if event_data.location is not None:
            sanitized_location = sanitize_input(event_data.location)
            update_fields.append("location = ?")
            update_params.append(sanitized_location)
        
        # Check if any fields were provided for update
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update"
            )
        
        # Validate datetime logic if both dates are being updated
        if event_data.start_datetime is not None and event_data.end_datetime is not None:
            if start_datetime >= end_datetime:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_datetime must be before end_datetime"
                )
        # Validate datetime logic if only one date is being updated
        elif event_data.start_datetime is not None:
            # Check against existing end_datetime
            existing_end_datetime = datetime.fromisoformat(existing_event["end_datetime"].replace('Z', '+00:00'))
            if start_datetime >= existing_end_datetime:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_datetime must be before existing end_datetime"
                )
        elif event_data.end_datetime is not None:
            # Check against existing start_datetime
            existing_start_datetime = datetime.fromisoformat(existing_event["start_datetime"].replace('Z', '+00:00'))
            if existing_start_datetime >= end_datetime:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="existing start_datetime must be before end_datetime"
                )
        
        # Add updated_at timestamp
        update_fields.append("updated_at = ?")
        update_params.append(datetime.now().isoformat())
        
        # Add event_id to params for WHERE clause
        update_params.append(event_id)
        
        # Build and execute update query
        update_query = f"""
            UPDATE events 
            SET {', '.join(update_fields)}
            WHERE id = ?
        """
        
        # Execute update query
        affected_rows = execute_query(update_query, tuple(update_params))
        
        if affected_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update event - no rows affected"
            )
        
        # Fetch the updated event
        updated_event_query = """
            SELECT e.id, e.travel_id, e.title, e.description, e.event_type_id,
                   et.name as event_type_name, et.color as event_type_color, et.icon as event_type_icon,
                   e.start_datetime, e.end_datetime, e.location, e.created_at, e.updated_at
            FROM events e
            LEFT JOIN event_types et ON e.event_type_id = et.id
            WHERE e.id = ?
        """
        
        updated_event_data = fetch_one(updated_event_query, (event_id,))
        
        if not updated_event_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch updated event"
            )
        
        # Create response object
        updated_event = EventResponse(
            id=updated_event_data["id"],
            travel_id=updated_event_data["travel_id"],
            title=updated_event_data["title"],
            description=updated_event_data["description"],
            event_type_id=updated_event_data["event_type_id"],
            event_type_name=updated_event_data["event_type_name"],
            event_type_color=updated_event_data["event_type_color"],
            event_type_icon=updated_event_data["event_type_icon"],
            start_datetime=updated_event_data["start_datetime"],
            end_datetime=updated_event_data["end_datetime"],
            location=updated_event_data["location"],
            created_at=updated_event_data["created_at"],
            updated_at=updated_event_data["updated_at"]
        )
        
        # Log the business event
        log_business_event("event_updated", "event", str(event_id), {
            "updated_fields": list(event_data.dict(exclude_unset=True).keys()),
            "title": existing_event["title"]
        })
        
        # Log the response
        logger.info(f"Successfully updated event with ID: {event_id}")
        
        # Create and return response
        response = UpdateEventResponse(
            success=True,
            data=updated_event,
            message="Event updated successfully"
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {
            "endpoint": "update_event", 
            "event_id": event_id,
            "event_data": event_data.dict(exclude_unset=True) if hasattr(event_data, 'dict') else str(event_data)
        })
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update event"
        )

# Route: DELETE /events/:id - Soft delete event
@router.delete("/{event_id}", response_model=SoftDeleteEventResponse)
async def delete_event(
    request: Request,
    event_id: int
):
    """
    Soft delete an event (mark as deleted without removing from database).
    
    Args:
        request: FastAPI request object
        event_id: ID of the event to delete
    
    Returns:
        Success message with deletion timestamp
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Soft deleting event with ID: {event_id}")
        
        # Validate event_id parameter
        if event_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event ID must be a positive integer"
            )
        
        # Check if event exists and is not already deleted
        event_query = """
            SELECT id, title, is_deleted
            FROM events 
            WHERE id = ?
        """
        
        existing_event = fetch_one(event_query, (event_id,))
        
        if not existing_event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {event_id} not found"
            )
        
        if existing_event["is_deleted"] == 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Event with ID {event_id} is already deleted"
            )
        
        # Get current timestamp for deletion
        current_timestamp = datetime.now().isoformat()
        
        # Soft delete the event
        delete_query = """
            UPDATE events 
            SET is_deleted = 1, 
                deleted_at = ?, 
                updated_at = ?
            WHERE id = ?
        """
        
        delete_params = (current_timestamp, current_timestamp, event_id)
        
        # Execute soft delete query
        affected_rows = execute_query(delete_query, delete_params)
        
        if affected_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to soft delete event - no rows affected"
            )
        
        # Log the business event
        log_business_event("event_deleted", "event", str(event_id), {
            "deleted_at": current_timestamp,
            "title": existing_event["title"]
        })
        
        # Log the response
        logger.info(f"Successfully soft deleted event with ID: {event_id} at {current_timestamp}")
        
        # Create and return response
        response = SoftDeleteEventResponse(
            success=True,
            message="Event soft deleted successfully",
            deletedAt=current_timestamp
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {"endpoint": "delete_event", "event_id": event_id})
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete event"
        )

# Route: POST /events/:id/restore - Restore deleted event
@router.post("/{event_id}/restore", response_model=RestoreEventResponse)
async def restore_event(
    request: Request,
    event_id: int
):
    """
    Restore a previously deleted event.
    
    Args:
        request: FastAPI request object
        event_id: ID of the event to restore
    
    Returns:
        Restored event information with success message
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Restoring event with ID: {event_id}")
        
        # Validate event_id parameter
        if event_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event ID must be a positive integer"
            )
        
        # Check if event exists and is deleted
        event_query = """
            SELECT id, title, is_deleted
            FROM events 
            WHERE id = ?
        """
        
        existing_event = fetch_one(event_query, (event_id,))
        
        if not existing_event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {event_id} not found"
            )
        
        if existing_event["is_deleted"] == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Event with ID {event_id} is not deleted"
            )
        
        # Get current timestamp for restoration
        current_timestamp = datetime.now().isoformat()
        
        # Restore the event
        restore_query = """
            UPDATE events 
            SET is_deleted = 0, 
                deleted_at = NULL, 
                updated_at = ?
            WHERE id = ?
        """
        
        restore_params = (current_timestamp, event_id)
        
        # Execute restore query
        affected_rows = execute_query(restore_query, restore_params)
        
        if affected_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restore event - no rows affected"
            )
        
        # Fetch the restored event
        restored_event_query = """
            SELECT e.id, e.travel_id, e.title, e.description, e.event_type_id,
                   et.name as event_type_name, et.color as event_type_color, et.icon as event_type_icon,
                   e.start_datetime, e.end_datetime, e.location, e.created_at, e.updated_at
            FROM events e
            LEFT JOIN event_types et ON e.event_type_id = et.id
            WHERE e.id = ?
        """
        
        restored_event_data = fetch_one(restored_event_query, (event_id,))
        
        if not restored_event_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch restored event"
            )
        
        # Create response object
        restored_event = EventResponse(
            id=restored_event_data["id"],
            travel_id=restored_event_data["travel_id"],
            title=restored_event_data["title"],
            description=restored_event_data["description"],
            event_type_id=restored_event_data["event_type_id"],
            event_type_name=restored_event_data["event_type_name"],
            event_type_color=restored_event_data["event_type_color"],
            event_type_icon=restored_event_data["event_type_icon"],
            start_datetime=restored_event_data["start_datetime"],
            end_datetime=restored_event_data["end_datetime"],
            location=restored_event_data["location"],
            created_at=restored_event_data["created_at"],
            updated_at=restored_event_data["updated_at"]
        )
        
        # Log the business event
        log_business_event("event_restored", "event", str(event_id), {
            "restored_at": current_timestamp,
            "title": existing_event["title"]
        })
        
        # Log the response
        logger.info(f"Successfully restored event with ID: {event_id} at {current_timestamp}")
        
        # Create and return response
        response = RestoreEventResponse(
            success=True,
            data=restored_event,
            message="Event restored successfully"
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {"endpoint": "restore_event", "event_id": event_id})
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore event"
        )
