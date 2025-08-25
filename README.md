# TravelPlanner API

Backend API server for the TravelPlanner application, built with Python and FastAPI.

## Features

- RESTful API endpoints for travel management
- Event management system
- Database integration with SQLite
- CORS middleware support
- Comprehensive error handling
- Logging system
- Input validation
- Test suite with pytest

## Project Structure

```
travelplanner-api/
├── config/           # Configuration management
├── database/         # Database schema and utilities
├── middleware/       # Custom middleware (CORS, error handling, etc.)
├── routes/           # API route definitions
├── tests/            # Test files
├── utils/            # Utility functions
├── logs/             # Application logs
├── uploads/          # File upload directory
├── main.py           # Main application entry point
├── start_server.py   # Server startup script
├── requirements.txt  # Python dependencies
└── pytest.ini       # Pytest configuration
```

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd travelplanner-api
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
python -c "from database.db import init_db; init_db()"
```

### Running the Server

#### Development Mode
```bash
python start_server.py
```

#### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, you can access:
- Interactive API docs: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`

## API Endpoints

### Travels
- `GET /travels` - List all travels
- `POST /travels` - Create a new travel
- `GET /travels/{id}` - Get travel by ID
- `PUT /travels/{id}` - Update travel
- `DELETE /travels/{id}` - Delete travel

### Events
- `GET /events` - List all events
- `POST /events` - Create a new event
- `GET /events/{id}` - Get event by ID
- `PUT /events/{id}` - Update event
- `DELETE /events/{id}` - Delete event

### Event Types
- `GET /event-types` - List all event types
- `POST /event-types` - Create a new event type
- `GET /event-types/{id}` - Get event type by ID
- `PUT /event-types/{id}` - Update event type
- `DELETE /event-types/{id}` - Delete event type

## Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=.
```

## Configuration

The application uses environment variables for configuration. Create a `.env` file in the root directory:

```env
DATABASE_URL=sqlite:///./travelplanner.db
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License.