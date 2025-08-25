"""
Travel Routes Module

This module contains all the travel-related API endpoints for the Travel Planner application.
Routes handle CRUD operations for travels including soft delete and restore functionality.
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
    prefix="/travels",
    tags=["travels"],
    responses={
        404: {"description": "Travel not found"},
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"}
    }
)

# Setup logging
logger = logging.getLogger(__name__)

# Pydantic models for response
class TravelResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    start_date: str
    end_date: str
    destination: Optional[str] = None
    created_at: str
    updated_at: str

class DeletedTravelResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    start_date: str
    end_date: str
    destination: Optional[str] = None
    is_deleted: int
    deleted_at: str
    created_at: str

class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    pages: int

class TravelListResponse(BaseModel):
    success: bool = True
    data: List[TravelResponse]
    pagination: PaginationInfo

class DeletedTravelListResponse(BaseModel):
    success: bool = True
    data: List[DeletedTravelResponse]
    pagination: PaginationInfo

class CreateTravelRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Travel title")
    description: Optional[str] = Field(None, max_length=1000, description="Travel description")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    destination: Optional[str] = Field(None, max_length=255, description="Travel destination")

class CreateTravelResponse(BaseModel):
    success: bool = True
    data: TravelResponse
    message: str = "Travel created successfully"

class SingleTravelResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    start_date: str
    end_date: str
    destination: Optional[str] = None
    events_count: int = 0
    created_at: str
    updated_at: str

class GetTravelResponse(BaseModel):
    success: bool = True
    data: SingleTravelResponse

class UpdateTravelRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Travel title")
    description: Optional[str] = Field(None, max_length=1000, description="Travel description")
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")
    destination: Optional[str] = Field(None, max_length=255, description="Travel destination")

class UpdateTravelResponse(BaseModel):
    success: bool = True
    data: TravelResponse
    message: str = "Travel updated successfully"

class SoftDeleteResponse(BaseModel):
    success: bool = True
    message: str = "Travel soft deleted successfully"
    deletedAt: str

class RestoreTravelResponse(BaseModel):
    success: bool = True
    data: TravelResponse
    message: str = "Travel restored successfully"

# Route: GET / - List all active travels
@router.get("/", response_model=TravelListResponse)
async def list_travels(
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of travels to return"),
    offset: int = Query(0, ge=0, description="Number of travels to skip"),
    title: Optional[str] = Query(None, description="Filter by title (partial match)"),
    destination: Optional[str] = Query(None, description="Filter by destination (partial match)"),
    start_date_from: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    start_date_to: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date_from: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    end_date_to: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)")
):
    """
    List all active travels with optional filtering and pagination.
    
    Args:
        request: FastAPI request object
        limit: Maximum number of travels to return (1-100, default: 10)
        offset: Number of travels to skip (default: 0)
        title: Filter by title (partial match)
        destination: Filter by destination (partial match)
        start_date_from: Filter by start date from (YYYY-MM-DD)
        start_date_to: Filter by start date to (YYYY-MM-DD)
        end_date_from: Filter by end date from (YYYY-MM-DD)
        end_date_to: Filter by end date to (YYYY-MM-DD)
    
    Returns:
        Paginated list of active travels with metadata
    """
    try:
        # Log the request
        logger.info(f"Listing travels - limit: {limit}, offset: {offset}, filters: title={title}, destination={destination}, start_date_from={start_date_from}, start_date_to={start_date_to}, end_date_from={end_date_from}, end_date_to={end_date_to}")
        
        # Validate date parameters
        date_filters = {}
        if start_date_from:
            try:
                datetime.strptime(start_date_from, "%Y-%m-%d")
                date_filters["start_date_from"] = start_date_from
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date_from format. Use YYYY-MM-DD"
                )
        
        if start_date_to:
            try:
                datetime.strptime(start_date_to, "%Y-%m-%d")
                date_filters["start_date_to"] = start_date_to
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date_to format. Use YYYY-MM-DD"
                )
        
        if end_date_from:
            try:
                datetime.strptime(end_date_from, "%Y-%m-%d")
                date_filters["end_date_from"] = end_date_from
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date_from format. Use YYYY-MM-DD"
                )
        
        if end_date_to:
            try:
                datetime.strptime(end_date_to, "%Y-%m-%d")
                date_filters["end_date_to"] = end_date_to
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date_to format. Use YYYY-MM-DD"
                )
        
        # Build the WHERE clause for filtering
        where_conditions = ["is_deleted = 0"]
        query_params = []
        
        if title:
            where_conditions.append("title LIKE ?")
            query_params.append(f"%{title}%")
        
        if destination:
            where_conditions.append("destination LIKE ?")
            query_params.append(f"%{destination}%")
        
        if start_date_from:
            where_conditions.append("start_date >= ?")
            query_params.append(start_date_from)
        
        if start_date_to:
            where_conditions.append("start_date <= ?")
            query_params.append(start_date_to)
        
        if end_date_from:
            where_conditions.append("end_date >= ?")
            query_params.append(end_date_from)
        
        if end_date_to:
            where_conditions.append("end_date <= ?")
            query_params.append(end_date_to)
        
        where_clause = " AND ".join(where_conditions)
        
        # Get total count for pagination
        count_query = f"SELECT COUNT(*) as total FROM travels WHERE {where_clause}"
        count_result = fetch_one(count_query, tuple(query_params))
        total_count = count_result["total"] if count_result else 0
        
        # Calculate pagination info
        page = (offset // limit) + 1
        total_pages = (total_count + limit - 1) // limit
        
        # Get travels with pagination
        travels_query = f"""
            SELECT id, title, description, start_date, end_date, destination, created_at, updated_at
            FROM travels 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        
        # Add pagination parameters
        query_params.extend([limit, offset])
        
        # Execute query
        travels_data = fetch_all(travels_query, tuple(query_params))
        
        # Transform data to response format
        travels = []
        for travel in travels_data:
            travels.append(TravelResponse(
                id=travel["id"],
                title=travel["title"],
                description=travel["description"],
                start_date=travel["start_date"],
                end_date=travel["end_date"],
                destination=travel["destination"],
                created_at=travel["created_at"],
                updated_at=travel["updated_at"]
            ))
        
        # Create pagination info
        pagination = PaginationInfo(
            page=page,
            limit=limit,
            total=total_count,
            pages=total_pages
        )
        
        # Create response
        response = TravelListResponse(
            success=True,
            data=travels,
            pagination=pagination
        )
        
        # Log the response
        logger.info(f"Successfully listed {len(travels)} travels out of {total_count} total")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {
            "endpoint": "list_travels", 
            "limit": limit, 
            "offset": offset, 
            "title": title,
            "destination": destination,
            "start_date_from": start_date_from,
            "start_date_to": start_date_to,
            "end_date_from": end_date_from,
            "end_date_to": end_date_to
        })
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list travels"
        )

# Route: GET /deleted - List deleted travels
@router.get("/deleted", response_model=DeletedTravelListResponse)
async def list_deleted_travels(
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of deleted travels to return"),
    offset: int = Query(0, ge=0, description="Number of deleted travels to skip"),
    title: Optional[str] = Query(None, description="Filter by title (partial match)"),
    destination: Optional[str] = Query(None, description="Filter by destination (partial match)"),
    deleted_date_from: Optional[str] = Query(None, description="Filter by deletion date from (YYYY-MM-DD)"),
    deleted_date_to: Optional[str] = Query(None, description="Filter by deletion date to (YYYY-MM-DD)")
):
    """
    List all deleted travels with optional filtering and pagination.
    
    Args:
        request: FastAPI request object
        limit: Maximum number of deleted travels to return (1-100, default: 10)
        offset: Number of deleted travels to skip (default: 0)
        title: Filter by title (partial match)
        destination: Filter by destination (partial match)
        deleted_date_from: Filter by deletion date from (YYYY-MM-DD)
        deleted_date_to: Filter by deletion date to (YYYY-MM-DD)
    
    Returns:
        Paginated list of deleted travels with soft delete metadata
    """
    try:
        # Log the request
        logger.info(f"Listing deleted travels - limit: {limit}, offset: {offset}, filters: title={title}, destination={destination}, deleted_date_from={deleted_date_from}, deleted_date_to={deleted_date_to}")
        
        # Validate date parameters
        date_filters = {}
        if deleted_date_from:
            try:
                datetime.strptime(deleted_date_from, "%Y-%m-%d")
                date_filters["deleted_date_from"] = deleted_date_from
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid deleted_date_from format. Use YYYY-MM-DD"
                )
        
        if deleted_date_to:
            try:
                datetime.strptime(deleted_date_to, "%Y-MM-DD")
                date_filters["deleted_date_to"] = deleted_date_to
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid deleted_date_to format. Use YYYY-MM-DD"
                )
        
        # Build the WHERE clause for filtering
        where_conditions = ["is_deleted = 1"]
        query_params = []
        
        if title:
            where_conditions.append("title LIKE ?")
            query_params.append(f"%{title}%")
        
        if destination:
            where_conditions.append("destination LIKE ?")
            query_params.append(f"%{destination}%")
        
        if deleted_date_from:
            where_conditions.append("date(deleted_at) >= ?")
            query_params.append(deleted_date_from)
        
        if deleted_date_to:
            where_conditions.append("date(deleted_at) <= ?")
            query_params.append(deleted_date_to)
        
        where_clause = " AND ".join(where_conditions)
        
        # Get total count for pagination
        count_query = f"SELECT COUNT(*) as total FROM travels WHERE {where_clause}"
        count_result = fetch_one(count_query, tuple(query_params))
        total_count = count_result["total"] if count_result else 0
        
        # Calculate pagination info
        page = (offset // limit) + 1
        total_pages = (total_count + limit - 1) // limit
        
        # Get deleted travels with pagination
        travels_query = f"""
            SELECT id, title, description, start_date, end_date, destination, 
                   is_deleted, deleted_at, created_at
            FROM travels 
            WHERE {where_clause}
            ORDER BY deleted_at DESC
            LIMIT ? OFFSET ?
        """
        
        # Add pagination parameters
        query_params.extend([limit, offset])
        
        # Execute query
        travels_data = fetch_all(travels_query, tuple(query_params))
        
        # Transform data to response format
        deleted_travels = []
        for travel in travels_data:
            deleted_travels.append(DeletedTravelResponse(
                id=travel["id"],
                title=travel["title"],
                description=travel["description"],
                start_date=travel["start_date"],
                end_date=travel["end_date"],
                destination=travel["destination"],
                is_deleted=travel["is_deleted"],
                deleted_at=travel["deleted_at"],
                created_at=travel["created_at"]
            ))
        
        # Create pagination info
        pagination = PaginationInfo(
            page=page,
            limit=limit,
            total=total_count,
            pages=total_pages
        )
        
        # Create response
        response = DeletedTravelListResponse(
            success=True,
            data=deleted_travels,
            pagination=pagination
        )
        
        # Log the response
        logger.info(f"Successfully listed {len(deleted_travels)} deleted travels out of {total_count} total")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {
            "endpoint": "list_deleted_travels", 
            "limit": limit, 
            "offset": offset, 
            "title": title,
            "destination": destination,
            "deleted_date_from": deleted_date_from,
            "deleted_date_to": deleted_date_to
        })
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list deleted travels"
        )

# Health check endpoint for travels module
@router.get("/health", include_in_schema=False)
async def travels_health_check():
    """
    Health check endpoint for the travels module.
    
    Returns:
        Health status of the travels module
    """
    return {
        "status": "healthy",
        "module": "travels",
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

# Route: POST / - Create new travel
@router.post("/", response_model=CreateTravelResponse, status_code=status.HTTP_201_CREATED)
async def create_travel(
    request: Request,
    travel_data: CreateTravelRequest
):
    """
    Create a new travel.
    
    Args:
        request: FastAPI request object
        travel_data: Validated travel data from request body
    
    Returns:
        Created travel information with success message
    
    Raises:
        HTTPException: For validation errors or database failures
    """
    try:
        # Log the request
        logger.info(f"Creating new travel - data: {travel_data.dict()}")
        
        # Validate and parse dates
        try:
            start_date = datetime.strptime(travel_data.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(travel_data.end_date, "%Y-%m-%d").date()
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format. Use YYYY-MM-DD format. Error: {str(e)}"
            )
        
        # Validate date logic
        if start_date >= end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before end_date"
            )
        
        # Check if start_date is not in the past (optional business rule)
        today = date.today()
        if start_date < today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be in the past"
            )
        
        # Sanitize input data
        sanitized_title = sanitize_input(travel_data.title) if travel_data.title else ""
        sanitized_description = sanitize_input(travel_data.description) if travel_data.description else None
        sanitized_destination = sanitize_input(travel_data.destination) if travel_data.destination else None
        
        # Validate sanitized data
        if not sanitized_title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title cannot be empty after sanitization"
            )
        
        # Prepare data for database insertion
        insert_data = {
            "title": sanitized_title,
            "description": sanitized_description,
            "start_date": travel_data.start_date,
            "end_date": travel_data.end_date,
            "destination": sanitized_destination,
            "is_deleted": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Insert into database
        insert_query = """
            INSERT INTO travels (title, description, start_date, end_date, destination, is_deleted, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        insert_params = (
            insert_data["title"],
            insert_data["description"],
            insert_data["start_date"],
            insert_data["end_date"],
            insert_data["destination"],
            insert_data["is_deleted"],
            insert_data["created_at"],
            insert_data["updated_at"]
        )
        
        # Execute insert query
        travel_id = execute_insert(insert_query, insert_params)
        
        if not travel_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create travel - no ID returned"
            )
        
        # Fetch the created travel to return
        fetch_query = """
            SELECT id, title, description, start_date, end_date, destination, created_at, updated_at
            FROM travels 
            WHERE id = ?
        """
        
        created_travel_data = fetch_one(fetch_query, (travel_id,))
        
        if not created_travel_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch created travel"
            )
        
        # Create response object
        created_travel = TravelResponse(
            id=created_travel_data["id"],
            title=created_travel_data["title"],
            description=created_travel_data["description"],
            start_date=created_travel_data["start_date"],
            end_date=created_travel_data["end_date"],
            destination=created_travel_data["destination"],
            created_at=created_travel_data["created_at"],
            updated_at=created_travel_data["updated_at"]
        )
        
        # Log the business event
        log_business_event("travel_created", "travel", str(travel_id), travel_data.dict())
        
        # Log the response
        logger.info(f"Successfully created travel with ID: {travel_id}")
        
        # Create and return response
        response = CreateTravelResponse(
            success=True,
            data=created_travel,
            message="Travel created successfully"
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {"endpoint": "create_travel", "travel_data": travel_data.dict() if hasattr(travel_data, 'dict') else str(travel_data)})
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create travel"
        )

# Route: GET /:id - Get single travel
@router.get("/{travel_id}", response_model=GetTravelResponse)
async def get_travel(
    request: Request,
    travel_id: int
):
    """
    Get a single travel by ID.
    
    Args:
        request: FastAPI request object
        travel_id: ID of the travel to retrieve
    
    Returns:
        Travel information with events count
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Getting travel with ID: {travel_id}")
        
        # Validate travel_id parameter
        if travel_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Travel ID must be a positive integer"
            )
        
        # Query database for travel
        travel_query = """
            SELECT id, title, description, start_date, end_date, destination, 
                   is_deleted, created_at, updated_at
            FROM travels 
            WHERE id = ?
        """
        
        travel_data = fetch_one(travel_query, (travel_id,))
        
        # Check if travel exists
        if not travel_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Travel with ID {travel_id} not found"
            )
        
        # Check if travel is soft deleted
        if travel_data["is_deleted"] == 1:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Travel with ID {travel_id} has been deleted"
            )
        
        # Get events count for this travel
        events_count_query = """
            SELECT COUNT(*) as count
            FROM events 
            WHERE travel_id = ? AND is_deleted = 0
        """
        
        events_count_result = fetch_one(events_count_query, (travel_id,))
        events_count = events_count_result["count"] if events_count_result else 0
        
        # Create response object
        travel = SingleTravelResponse(
            id=travel_data["id"],
            title=travel_data["title"],
            description=travel_data["description"],
            start_date=travel_data["start_date"],
            end_date=travel_data["end_date"],
            destination=travel_data["destination"],
            events_count=events_count,
            created_at=travel_data["created_at"],
            updated_at=travel_data["updated_at"]
        )
        
        # Log the response
        logger.info(f"Successfully retrieved travel with ID: {travel_id}, events count: {events_count}")
        
        # Create and return response
        response = GetTravelResponse(
            success=True,
            data=travel
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {"endpoint": "get_travel", "travel_id": travel_id})
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve travel"
        )

# Route: PUT /:id - Update travel
@router.put("/{travel_id}", response_model=UpdateTravelResponse)
async def update_travel(
    request: Request,
    travel_id: int,
    travel_data: UpdateTravelRequest
):
    """
    Update an existing travel.
    
    Args:
        request: FastAPI request object
        travel_id: ID of the travel to update
        travel_data: Validated travel update data from request body
    
    Returns:
        Updated travel information with success message
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Updating travel with ID: {travel_id} - data: {travel_data.dict(exclude_unset=True)}")
        
        # Validate travel_id parameter
        if travel_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Travel ID must be a positive integer"
            )
        
        # Check if travel exists and is not deleted
        travel_query = """
            SELECT id, title, description, start_date, end_date, destination, 
                   is_deleted, created_at, updated_at
            FROM travels 
            WHERE id = ?
        """
        
        existing_travel = fetch_one(travel_query, (travel_id,))
        
        if not existing_travel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Travel with ID {travel_id} not found"
            )
        
        if existing_travel["is_deleted"] == 1:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Travel with ID {travel_id} has been deleted"
            )
        
        # Prepare update data - only include fields that were provided
        update_fields = []
        update_params = []
        
        # Handle title update
        if travel_data.title is not None:
            sanitized_title = sanitize_input(travel_data.title)
            if not sanitized_title.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Title cannot be empty after sanitization"
                )
            update_fields.append("title = ?")
            update_params.append(sanitized_title)
        
        # Handle description update
        if travel_data.description is not None:
            sanitized_description = sanitize_input(travel_data.description)
            update_fields.append("description = ?")
            update_params.append(sanitized_description)
        
        # Handle start_date update
        if travel_data.start_date is not None:
            try:
                start_date = datetime.strptime(travel_data.start_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use YYYY-MM-DD format"
                )
            update_fields.append("start_date = ?")
            update_params.append(travel_data.start_date)
        
        # Handle end_date update
        if travel_data.end_date is not None:
            try:
                end_date = datetime.strptime(travel_data.end_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use YYYY-MM-DD format"
                )
            update_fields.append("end_date = ?")
            update_params.append(travel_data.end_date)
        
        # Handle destination update
        if travel_data.destination is not None:
            sanitized_destination = sanitize_input(travel_data.destination)
            update_fields.append("destination = ?")
            update_params.append(sanitized_destination)
        
        # Check if any fields were provided for update
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update"
            )
        
        # Validate date logic if both dates are being updated
        if travel_data.start_date is not None and travel_data.end_date is not None:
            if start_date >= end_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_date must be before end_date"
                )
        # Validate date logic if only one date is being updated
        elif travel_data.start_date is not None:
            # Check against existing end_date
            existing_end_date = datetime.strptime(existing_travel["end_date"], "%Y-%m-%d").date()
            if start_date >= existing_end_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_date must be before existing end_date"
                )
        elif travel_data.end_date is not None:
            # Check against existing start_date
            existing_start_date = datetime.strptime(existing_travel["start_date"], "%Y-%m-%d").date()
            if existing_start_date >= end_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="existing start_date must be before end_date"
                )
        
        # Add updated_at timestamp
        update_fields.append("updated_at = ?")
        update_params.append(datetime.now().isoformat())
        
        # Add travel_id to params for WHERE clause
        update_params.append(travel_id)
        
        # Build and execute update query
        update_query = f"""
            UPDATE travels 
            SET {', '.join(update_fields)}
            WHERE id = ?
        """
        
        # Execute update query
        affected_rows = execute_query(update_query, tuple(update_params))
        
        if affected_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update travel - no rows affected"
            )
        
        # Fetch the updated travel
        updated_travel_data = fetch_one(travel_query, (travel_id,))
        
        if not updated_travel_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch updated travel"
            )
        
        # Create response object
        updated_travel = TravelResponse(
            id=updated_travel_data["id"],
            title=updated_travel_data["title"],
            description=updated_travel_data["description"],
            start_date=updated_travel_data["start_date"],
            end_date=updated_travel_data["end_date"],
            destination=updated_travel_data["destination"],
            created_at=updated_travel_data["created_at"],
            updated_at=updated_travel_data["updated_at"]
        )
        
        # Log the business event
        log_business_event("travel_updated", "travel", str(travel_id), travel_data.dict(exclude_unset=True))
        
        # Log the response
        logger.info(f"Successfully updated travel with ID: {travel_id}")
        
        # Create and return response
        response = UpdateTravelResponse(
            success=True,
            data=updated_travel,
            message="Travel updated successfully"
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {"endpoint": "update_travel", "travel_id": travel_id, "travel_data": travel_data.dict(exclude_unset=True) if hasattr(travel_data, 'dict') else str(travel_data)})
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update travel"
        )

# Route: DELETE /:id - Soft delete travel
@router.delete("/{travel_id}", response_model=SoftDeleteResponse)
async def delete_travel(
    request: Request,
    travel_id: int
):
    """
    Soft delete a travel (mark as deleted without removing from database).
    
    Args:
        request: FastAPI request object
        travel_id: ID of the travel to delete
    
    Returns:
        Success message with deletion timestamp
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Soft deleting travel with ID: {travel_id}")
        
        # Validate travel_id parameter
        if travel_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Travel ID must be a positive integer"
            )
        
        # Check if travel exists and is not already deleted
        travel_query = """
            SELECT id, title, is_deleted
            FROM travels 
            WHERE id = ?
        """
        
        existing_travel = fetch_one(travel_query, (travel_id,))
        
        if not existing_travel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Travel with ID {travel_id} not found"
            )
        
        if existing_travel["is_deleted"] == 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Travel with ID {travel_id} is already deleted"
            )
        
        # Get current timestamp for deletion
        current_timestamp = datetime.now().isoformat()
        
        # Soft delete the travel
        delete_query = """
            UPDATE travels 
            SET is_deleted = 1, 
                deleted_at = ?, 
                updated_at = ?
            WHERE id = ?
        """
        
        delete_params = (current_timestamp, current_timestamp, travel_id)
        
        # Execute soft delete query
        affected_rows = execute_query(delete_query, delete_params)
        
        if affected_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to soft delete travel - no rows affected"
            )
        
        # Log the business event
        log_business_event("travel_deleted", "travel", str(travel_id), {
            "deleted_at": current_timestamp,
            "title": existing_travel["title"]
        })
        
        # Log the response
        logger.info(f"Successfully soft deleted travel with ID: {travel_id} at {current_timestamp}")
        
        # Create and return response
        response = SoftDeleteResponse(
            success=True,
            message="Travel soft deleted successfully",
            deletedAt=current_timestamp
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {"endpoint": "delete_travel", "travel_id": travel_id})
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete travel"
        )

# Route: POST /:id/restore - Restore deleted travel
@router.post("/{travel_id}/restore", response_model=RestoreTravelResponse)
async def restore_travel(
    request: Request,
    travel_id: int
):
    """
    Restore a previously deleted travel.
    
    Args:
        request: FastAPI request object
        travel_id: ID of the travel to restore
    
    Returns:
        Restored travel information with success message
    
    Raises:
        HTTPException: For validation errors, not found, or database failures
    """
    try:
        # Log the request
        logger.info(f"Restoring travel with ID: {travel_id}")
        
        # Validate travel_id parameter
        if travel_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Travel ID must be a positive integer"
            )
        
        # Check if travel exists and is deleted
        travel_query = """
            SELECT id, title, description, start_date, end_date, destination, 
                   is_deleted, created_at, updated_at
            FROM travels 
            WHERE id = ?
        """
        
        existing_travel = fetch_one(travel_query, (travel_id,))
        
        if not existing_travel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Travel with ID {travel_id} not found"
            )
        
        if existing_travel["is_deleted"] == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Travel with ID {travel_id} is not deleted"
            )
        
        # Get current timestamp for restoration
        current_timestamp = datetime.now().isoformat()
        
        # Restore the travel
        restore_query = """
            UPDATE travels 
            SET is_deleted = 0, 
                deleted_at = NULL, 
                updated_at = ?
            WHERE id = ?
        """
        
        restore_params = (current_timestamp, travel_id)
        
        # Execute restore query
        affected_rows = execute_query(restore_query, restore_params)
        
        if affected_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restore travel - no rows affected"
            )
        
        # Fetch the restored travel
        restored_travel_data = fetch_one(travel_query, (travel_id,))
        
        if not restored_travel_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch restored travel"
            )
        
        # Create response object
        restored_travel = TravelResponse(
            id=restored_travel_data["id"],
            title=restored_travel_data["title"],
            description=restored_travel_data["description"],
            start_date=restored_travel_data["start_date"],
            end_date=restored_travel_data["end_date"],
            destination=restored_travel_data["destination"],
            created_at=restored_travel_data["created_at"],
            updated_at=restored_travel_data["updated_at"]
        )
        
        # Log the business event
        log_business_event("travel_restored", "travel", str(travel_id), {
            "restored_at": current_timestamp,
            "title": existing_travel["title"]
        })
        
        # Log the response
        logger.info(f"Successfully restored travel with ID: {travel_id} at {current_timestamp}")
        
        # Create and return response
        response = RestoreTravelResponse(
            success=True,
            data=restored_travel,
            message="Travel restored successfully"
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        log_error(e, request, {"endpoint": "restore_travel", "travel_id": travel_id})
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore travel"
        )


