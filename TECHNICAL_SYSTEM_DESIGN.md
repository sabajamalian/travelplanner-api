# Travel Planner - Simple Technical System Design

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Database Design](#database-design)
4. [API Design](#api-design)
5. [Frontend Architecture](#frontend-architecture)
6. [Data Models](#data-models)
7. [Security Considerations](#security-considerations)
8. [Implementation Phases](#implementation-phases)

## System Overview

### Purpose
A simple travel planning platform where anonymous users can create travel itineraries, share them via URLs, and collaboratively plan events on a shared timeline calendar.

### Core Features
- **Travel Creation**: Create travel plans with start/end dates
- **Shared Timelines**: Collaborative calendar views accessible via URL
- **Event Management**: Create, edit, and delete travel-related events
- **Simple Sharing**: Shareable URLs using travel IDs
- **Event Types**: Basic categorized events (accommodation, transportation, activities, etc.)

### User Model
- **Anonymous Users**: No registration or login required
- **URL-Based Access**: Travels identified by their ID in the URL
- **Simple Collaboration**: Anyone with the URL can view and edit

## Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    ┌   Backend API   │    ┌   Database      │
│   (React)       │◄──►│   (Node.js)     │◄──►│   (SQLite)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Technology Stack
- **Frontend**: React 18, React Big Calendar, CSS
- **Backend**: Node.js, Express.js
- **Database**: SQLite with better-sqlite3
- **File Storage**: Local file system (for simplicity)
- **Deployment**: Single server deployment

## Database Design

### Core Tables

#### 1. Travels Table
```sql
CREATE TABLE travels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  start_date TEXT NOT NULL, -- ISO date string
  end_date TEXT NOT NULL,   -- ISO date string
  destination TEXT,
  is_deleted INTEGER DEFAULT 0, -- 0 = active, 1 = deleted
  deleted_at TEXT, -- ISO datetime string when soft deleted
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
```

#### 2. Event_Types Table
```sql
CREATE TABLE event_types (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  category TEXT NOT NULL, -- accommodation, transportation, activity, food, etc.
  color TEXT NOT NULL,    -- hex color code
  icon TEXT,
  is_deleted INTEGER DEFAULT 0, -- 0 = active, 1 = deleted
  deleted_at TEXT, -- ISO datetime string when soft deleted
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

-- Insert default event types
INSERT INTO event_types (name, category, color, icon) VALUES
  ('Accommodation', 'accommodation', '#28a745', '🏨'),
  ('Transportation', 'transportation', '#17a2b8', '✈️'),
  ('Activity', 'activity', '#ffc107', '🎯'),
  ('Food', 'food', '#fd7e14', '🍽️'),
  ('Shopping', 'shopping', '#6f42c1', '🛍️'),
  ('Entertainment', 'entertainment', '#e83e8c', '🎭');
```

#### 3. Events Table
```sql
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  travel_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  event_type_id INTEGER NOT NULL,
  start_datetime TEXT NOT NULL, -- ISO datetime string
  end_datetime TEXT NOT NULL,   -- ISO datetime string
  location TEXT,
  is_deleted INTEGER DEFAULT 0, -- 0 = active, 1 = deleted
  deleted_at TEXT, -- ISO datetime string when soft deleted
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (travel_id) REFERENCES travels(id) ON DELETE CASCADE,
  FOREIGN KEY (event_type_id) REFERENCES event_types(id)
);
```

#### 4. Event_Attachments Table
```sql
CREATE TABLE event_attachments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL,
  file_name TEXT NOT NULL,
  file_path TEXT NOT NULL, -- local file path
  file_type TEXT,
  file_size INTEGER,
  is_deleted INTEGER DEFAULT 0, -- 0 = active, 1 = deleted
  deleted_at TEXT, -- ISO datetime string when soft deleted
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);
```

### Database Indexes
```sql
-- Simple performance indexes
CREATE INDEX idx_events_travel ON events(travel_id);
CREATE INDEX idx_events_datetime ON events(start_datetime);
CREATE INDEX idx_events_type ON events(event_type_id);

-- Soft delete indexes for better performance
CREATE INDEX idx_travels_deleted ON travels(is_deleted);
CREATE INDEX idx_events_deleted ON events(is_deleted);
CREATE INDEX idx_event_types_deleted ON event_types(is_deleted);
CREATE INDEX idx_event_attachments_deleted ON event_attachments(is_deleted);
```

### Soft Delete Views (Optional)
```sql
-- Create views for active records only
CREATE VIEW active_travels AS
SELECT * FROM travels WHERE is_deleted = 0;

CREATE VIEW active_events AS
SELECT * FROM events WHERE is_deleted = 0;

CREATE VIEW active_event_types AS
SELECT * FROM event_types WHERE is_deleted = 0;

CREATE VIEW active_event_attachments AS
SELECT * FROM event_attachments WHERE is_deleted = 0;
```

## API Design

### RESTful Endpoints

#### Travels
```
GET    /api/travels                    # List all active travels
GET    /api/travels/deleted            # List deleted travels (admin)
POST   /api/travels                    # Create new travel
GET    /api/travels/:id               # Get travel details
PUT    /api/travels/:id               # Update travel
DELETE /api/travels/:id               # Soft delete travel
POST   /api/travels/:id/restore       # Restore deleted travel
```

#### Events
```
GET    /api/travels/:id/events        # List active travel events
GET    /api/travels/:id/events/deleted # List deleted events
POST   /api/travels/:id/events        # Create event
GET    /api/events/:id                # Get event details
PUT    /api/events/:id                # Update event
DELETE /api/events/:id                # Soft delete event
POST   /api/events/:id/restore        # Restore deleted event
```

#### Event Types
```
GET    /api/event-types               # List active event types
GET    /api/event-types/deleted       # List deleted event types
POST   /api/event-types               # Create event type
PUT    /api/event-types/:id           # Update event type
DELETE /api/event-types/:id           # Soft delete event type
POST   /api/event-types/:id/restore   # Restore deleted event type
```

#### Attachments
```
POST   /api/events/:id/attachments    # Upload attachment
DELETE /api/events/:id/attachments/:attachmentId # Soft delete attachment
POST   /api/attachments/:id/restore   # Restore deleted attachment
```

### API Response Format
```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

interface SoftDeleteResponse {
  success: boolean;
  message: string;
  deletedAt: string;
}
```

### Example API Usage
```typescript
// Soft delete a travel
DELETE /api/travels/123
Response: {
  "success": true,
  "message": "Travel soft deleted successfully",
  "deletedAt": "2024-01-15T10:30:00Z"
}

// Restore a deleted travel
POST /api/travels/123/restore
Response: {
  "success": true,
  "message": "Travel restored successfully"
}

// List deleted travels
GET /api/travels/deleted
Response: {
  "success": true,
  "data": [
    {
      "id": 123,
      "title": "Deleted Paris Trip",
      "is_deleted": 1,
      "deleted_at": "2024-01-15T10:30:00Z",
      // ... other fields
    }
  ]
}
```

## Frontend Architecture

### Component Structure
```
src/
├── components/
│   ├── common/
│   │   ├── Header.tsx
│   │   ├── Loading.tsx
│   │   └── ErrorBoundary.tsx
│   ├── travel/
│   │   ├── TravelForm.tsx
│   │   └── TravelInfo.tsx
│   ├── calendar/
│   │   ├── TravelCalendar.tsx
│   │   ├── EventModal.tsx
│   │   └── EventForm.tsx
│   └── shared/
│       └── ShareInfo.tsx
├── pages/
│   ├── Home.tsx
│   ├── CreateTravel.tsx
│   └── TravelTimeline.tsx
├── hooks/
│   ├── useTravel.ts
│   └── useEvents.ts
├── services/
│   ├── api.ts
│   ├── travel.ts
│   └── events.ts
└── utils/
    ├── dateUtils.ts
    └── constants.ts
```

### State Management
- **React useState/useReducer** for local component state
- **React Query** for server state management (optional, can use simple fetch)
- **Local Storage** for user preferences
- **URL State** for travel ID and current view

### Routing
```typescript
const routes = [
  { path: '/', component: Home },
  { path: '/create', component: CreateTravel },
  { path: '/travel/:id', component: TravelTimeline }
];
```

## Data Models

### TypeScript Interfaces
```typescript
interface Travel {
  id: number;
  title: string;
  description?: string;
  startDate: string; // ISO date string
  endDate: string;   // ISO date string
  destination?: string;
  isDeleted: boolean;
  deletedAt?: string; // ISO datetime string
  createdAt: string;
  updatedAt: string;
}

interface Event {
  id: number;
  travelId: number;
  title: string;
  description?: string;
  eventTypeId: number;
  startDateTime: string; // ISO datetime string
  endDateTime: string;   // ISO datetime string
  location?: string;
  isDeleted: boolean;
  deletedAt?: string; // ISO datetime string
  createdAt: string;
  updatedAt: string;
}

interface EventType {
  id: number;
  name: string;
  category: string;
  color: string;
  icon?: string;
  isDeleted: boolean;
  deletedAt?: string; // ISO datetime string
  createdAt: string;
  updatedAt: string;
}

interface EventAttachment {
  id: number;
  eventId: number;
  fileName: string;
  filePath: string;
  fileType?: string;
  fileSize?: number;
  isDeleted: boolean;
  deletedAt?: string; // ISO datetime string
  createdAt: string;
}
```

## Security Considerations

### Simple Security Measures
- **Input Validation**: Basic sanitization and validation
- **SQL Injection Prevention**: Use parameterized queries
- **File Upload Security**: Restrict file types and sizes
- **Rate Limiting**: Basic request limiting per IP
- **CORS**: Configure for your domain

### No Authentication Required
- **Anonymous Access**: Anyone can create and edit travels
- **URL-Based Security**: Travels are identified by their ID
- **Simple Sharing**: Share via URL, no user management

## Implementation Phases

### Phase 1: Core Setup (Week 1)
- [ ] Project setup with React and Node.js
- [ ] SQLite database setup with basic schema
- [ ] Simple Express.js backend
- [ ] Basic frontend structure

### Phase 2: Travel Management (Week 2)
- [ ] Travel CRUD operations
- [ ] Travel creation form
- [ ] Travel timeline view
- [ ] Basic routing

### Phase 3: Event System (Week 3)
- [ ] Event CRUD operations
- [ ] Event creation/editing forms
- [ ] Calendar integration with React Big Calendar
- [ ] Event type management

### Phase 4: File Attachments (Week 4)
- [ ] File upload system
- [ ] Attachment management
- [ ] Basic file storage
- [ ] UI for attachments

### Phase 5: Polish & Deploy (Week 5)
- [ ] UI/UX improvements
- [ ] Error handling
- [ ] Basic testing
- [ ] Simple deployment

## Database Setup

### SQLite Database File with Soft Delete
```bash
# Create database
sqlite3 travelplanner.db

# Run schema
.read schema.sql

# Insert sample data
INSERT INTO event_types (name, category, color, icon) VALUES
  ('Accommodation', 'accommodation', '#28a745', '🏨'),
  ('Transportation', 'transportation', '#17a2b8', '✈️'),
  ('Activity', 'activity', '#ffc107', '🎯'),
  ('Food', 'food', '#fd7e14', '🍽️'),
  ('Shopping', 'shopping', '#6f42c1', '🛍️'),
  ('Entertainment', 'entertainment', '#e83e8c', '🎭');

# Create a sample travel
INSERT INTO travels (title, description, start_date, end_date, destination) VALUES
  ('Sample Paris Trip', 'A weekend getaway to Paris', '2024-06-15', '2024-06-17', 'Paris, France');
```

### Backend Database Connection
```typescript
import Database from 'better-sqlite3';

const db = new Database('travelplanner.db');

// Enable foreign keys
db.pragma('foreign_keys = ON');

// Create tables if they don't exist
db.exec(`
  CREATE TABLE IF NOT EXISTS travels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    destination TEXT,
    is_deleted INTEGER DEFAULT 0,
    deleted_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
  );
  
  CREATE TABLE IF NOT EXISTS event_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    color TEXT NOT NULL,
    icon TEXT,
    is_deleted INTEGER DEFAULT 0,
    deleted_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
  );
  
  CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    travel_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    event_type_id INTEGER NOT NULL,
    start_datetime TEXT NOT NULL,
    end_datetime TEXT NOT NULL,
    location TEXT,
    is_deleted INTEGER DEFAULT 0,
    deleted_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (travel_id) REFERENCES travels(id) ON DELETE CASCADE,
    FOREIGN KEY (event_type_id) REFERENCES event_types(id)
  );
  
  CREATE TABLE IF NOT EXISTS event_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT,
    file_size INTEGER,
    is_deleted INTEGER DEFAULT 0,
    deleted_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
  );
`);

export default db;
```

## Simple Backend Structure

### Express.js Setup
```typescript
import express from 'express';
import cors from 'cors';
import travelRoutes from './routes/travels';
import eventRoutes from './routes/events';
import eventTypeRoutes from './routes/eventTypes';

const app = express();

app.use(cors());
app.use(express.json());
app.use(express.static('uploads')); // For file attachments

app.use('/api/travels', travelRoutes);
app.use('/api/events', eventRoutes);
app.use('/api/event-types', eventTypeRoutes);

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

### Basic Route Example with Soft Delete
```typescript
// routes/travels.ts
import express from 'express';
import db from '../database';

const router = express.Router();

// Get all active travels
router.get('/', (req, res) => {
  try {
    const travels = db.prepare(`
      SELECT * FROM travels 
      WHERE is_deleted = 0 
      ORDER BY created_at DESC
    `).all();
    res.json({ success: true, data: travels });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch travels' });
  }
});

// Get deleted travels
router.get('/deleted', (req, res) => {
  try {
    const deletedTravels = db.prepare(`
      SELECT * FROM travels 
      WHERE is_deleted = 1 
      ORDER BY deleted_at DESC
    `).all();
    res.json({ success: true, data: deletedTravels });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch deleted travels' });
  }
});

// Create travel
router.post('/', (req, res) => {
  try {
    const { title, description, startDate, endDate, destination } = req.body;
    
    const stmt = db.prepare(`
      INSERT INTO travels (title, description, start_date, end_date, destination)
      VALUES (?, ?, ?, ?, ?)
    `);
    
    const result = stmt.run(title, description, startDate, endDate, destination);
    
    res.json({ 
      success: true, 
      data: { id: result.lastInsertRowid },
      message: 'Travel created successfully' 
    });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to create travel' });
  }
});

// Soft delete travel
router.delete('/:id', (req, res) => {
  try {
    const { id } = req.params;
    const deletedAt = new Date().toISOString();
    
    const stmt = db.prepare(`
      UPDATE travels 
      SET is_deleted = 1, deleted_at = ?, updated_at = ?
      WHERE id = ?
    `);
    
    const result = stmt.run(deletedAt, deletedAt, id);
    
    if (result.changes > 0) {
      res.json({ 
        success: true, 
        message: 'Travel soft deleted successfully',
        deletedAt 
      });
    } else {
      res.status(404).json({ success: false, error: 'Travel not found' });
    }
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to delete travel' });
  }
});

// Restore deleted travel
router.post('/:id/restore', (req, res) => {
  try {
    const { id } = req.params;
    const now = new Date().toISOString();
    
    const stmt = db.prepare(`
      UPDATE travels 
      SET is_deleted = 0, deleted_at = NULL, updated_at = ?
      WHERE id = ?
    `);
    
    const result = stmt.run(now, id);
    
    if (result.changes > 0) {
      res.json({ 
        success: true, 
        message: 'Travel restored successfully' 
      });
    } else {
      res.status(404).json({ success: false, error: 'Travel not found' });
    }
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to restore travel' });
  }
});

export default router;
```

### Events Route with Soft Delete
```typescript
// routes/events.ts
import express from 'express';
import db from '../database';

const router = express.Router();

// Get active events for a travel
router.get('/travels/:travelId/events', (req, res) => {
  try {
    const { travelId } = req.params;
    const events = db.prepare(`
      SELECT e.*, et.name as event_type_name, et.color, et.icon
      FROM events e
      JOIN event_types et ON e.event_type_id = et.id
      WHERE e.travel_id = ? AND e.is_deleted = 0
      ORDER BY e.start_datetime
    `).all(travelId);
    
    res.json({ success: true, data: events });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch events' });
  }
});

// Soft delete event
router.delete('/:id', (req, res) => {
  try {
    const { id } = req.params;
    const deletedAt = new Date().toISOString();
    
    const stmt = db.prepare(`
      UPDATE events 
      SET is_deleted = 1, deleted_at = ?, updated_at = ?
      WHERE id = ?
    `);
    
    const result = stmt.run(deletedAt, deletedAt, id);
    
    if (result.changes > 0) {
      res.json({ 
        success: true, 
        message: 'Event soft deleted successfully',
        deletedAt 
      });
    } else {
      res.status(404).json({ success: false, error: 'Event not found' });
    }
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to delete event' });
  }
});

export default router;
```

## Frontend Implementation

### API Service with Soft Delete Support
```typescript
// services/api.ts
const API_BASE = 'http://localhost:3001/api';

export const api = {
  async get(endpoint: string) {
    const response = await fetch(`${API_BASE}${endpoint}`);
    return response.json();
  },
  
  async post(endpoint: string, data: any) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  },
  
  async put(endpoint: string, data: any) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  },
  
  async delete(endpoint: string) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'DELETE'
    });
    return response.json();
  },
  
  // Soft delete specific methods
  async softDelete(endpoint: string) {
    return this.delete(endpoint);
  },
  
  async restore(endpoint: string) {
    return this.post(`${endpoint}/restore`, {});
  },
  
  async getDeleted(endpoint: string) {
    return this.get(`${endpoint}/deleted`);
  }
};
```

### Travel Management with Soft Delete
```typescript
// components/travel/TravelList.tsx
import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';

export default function TravelList() {
  const [travels, setTravels] = useState([]);
  const [deletedTravels, setDeletedTravels] = useState([]);
  const [showDeleted, setShowDeleted] = useState(false);
  
  useEffect(() => {
    loadTravels();
  }, []);
  
  const loadTravels = async () => {
    try {
      const response = await api.get('/travels');
      if (response.success) {
        setTravels(response.data);
      }
    } catch (error) {
      console.error('Failed to load travels:', error);
    }
  };
  
  const loadDeletedTravels = async () => {
    try {
      const response = await api.getDeleted('/travels');
      if (response.success) {
        setDeletedTravels(response.data);
      }
    } catch (error) {
      console.error('Failed to load deleted travels:', error);
    }
  };
  
  const handleSoftDelete = async (travelId: number) => {
    try {
      const response = await api.softDelete(`/travels/${travelId}`);
      if (response.success) {
        loadTravels(); // Refresh the list
        alert('Travel deleted successfully');
      }
    } catch (error) {
      console.error('Failed to delete travel:', error);
    }
  };
  
  const handleRestore = async (travelId: number) => {
    try {
      const response = await api.restore(`/travels/${travelId}`);
      if (response.success) {
        loadDeletedTravels(); // Refresh deleted list
        loadTravels(); // Refresh active list
        alert('Travel restored successfully');
      }
    } catch (error) {
      console.error('Failed to restore travel:', error);
    }
  };
  
  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Travel Plans</h1>
        <button
          onClick={() => {
            setShowDeleted(!showDeleted);
            if (!showDeleted) {
              loadDeletedTravels();
            }
          }}
          className="bg-gray-500 text-white px-4 py-2 rounded"
        >
          {showDeleted ? 'Hide Deleted' : 'Show Deleted'}
        </button>
      </div>
      
      {/* Active Travels */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Active Travels</h2>
        {travels.map(travel => (
          <div key={travel.id} className="border p-4 mb-4 rounded">
            <h3 className="text-lg font-medium">{travel.title}</h3>
            <p className="text-gray-600">{travel.description}</p>
            <div className="flex justify-between items-center mt-2">
              <span className="text-sm text-gray-500">
                {travel.start_date} - {travel.end_date}
              </span>
              <button
                onClick={() => handleSoftDelete(travel.id)}
                className="bg-red-500 text-white px-3 py-1 rounded text-sm"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
      
      {/* Deleted Travels */}
      {showDeleted && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Deleted Travels</h2>
          {deletedTravels.map(travel => (
            <div key={travel.id} className="border p-4 mb-4 rounded bg-gray-50">
              <h3 className="text-lg font-medium text-gray-600">{travel.title}</h3>
              <p className="text-gray-500">{travel.description}</p>
              <div className="flex justify-between items-center mt-2">
                <span className="text-sm text-gray-400">
                  Deleted: {travel.deleted_at}
                </span>
                <button
                  onClick={() => handleRestore(travel.id)}
                  className="bg-green-500 text-white px-3 py-1 rounded text-sm"
                >
                  Restore
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

## Conclusion

This simplified technical design with soft delete capability provides a robust foundation for a travel planning application while maintaining simplicity and ease of implementation.

### Key Benefits of Soft Delete
- **Data Recovery**: Accidental deletions can be easily reversed
- **Audit Trail**: Track when items were deleted
- **Referential Integrity**: Maintain relationships between tables
- **User Experience**: Users can restore items they didn't mean to delete

### Implementation Notes
- **Soft delete is implemented** for travels, events, event types, and attachments
- **Active records only** are shown by default in most queries
- **Restore functionality** is available for all soft-deleted items
- **Performance optimized** with proper indexing on is_deleted flags
- **API endpoints** support both active and deleted record management

The system maintains the simplicity of anonymous users and SQLite while adding professional-grade data management capabilities that users expect from modern applications.
