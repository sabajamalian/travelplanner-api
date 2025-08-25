-- Travel Planner Database Schema
-- Run this to create the database structure

PRAGMA foreign_keys = ON;

-- Create travels table
CREATE TABLE travels (
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

-- Create event_types table
CREATE TABLE event_types (
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

-- Create events table
CREATE TABLE events (
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

-- Create event_attachments table
CREATE TABLE event_attachments (
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

-- Performance indexes
CREATE INDEX idx_events_travel ON events(travel_id);
CREATE INDEX idx_events_datetime ON events(start_datetime);
CREATE INDEX idx_events_type ON events(event_type_id);
CREATE INDEX idx_travels_start_date ON travels(start_date);
CREATE INDEX idx_travels_end_date ON travels(end_date);
CREATE INDEX idx_travels_destination ON travels(destination);
CREATE INDEX idx_travels_created_at ON travels(created_at);
CREATE INDEX idx_event_types_category ON event_types(category);
CREATE INDEX idx_event_attachments_event_id ON event_attachments(event_id);
CREATE INDEX idx_event_attachments_file_type ON event_attachments(file_type);
CREATE INDEX idx_travels_deleted ON travels(is_deleted);
CREATE INDEX idx_events_deleted ON events(is_deleted);
CREATE INDEX idx_event_types_deleted ON event_types(is_deleted);
CREATE INDEX idx_event_attachments_deleted ON event_attachments(is_deleted);
CREATE INDEX idx_events_travel_datetime ON events(travel_id, start_datetime);
CREATE INDEX idx_events_travel_type ON events(travel_id, event_type_id);
CREATE INDEX idx_events_datetime_range ON events(start_datetime, end_datetime);
CREATE INDEX idx_events_soft_delete_time ON events(is_deleted, deleted_at);
CREATE INDEX idx_travels_soft_delete_time ON travels(is_deleted, deleted_at);
CREATE INDEX idx_events_calendar_view ON events(is_deleted, start_datetime, end_datetime);
CREATE INDEX idx_travels_date_range ON travels(is_deleted, start_date, end_date);
CREATE INDEX idx_events_calendar_type ON events(is_deleted, event_type_id, start_datetime);

-- Triggers for automatic timestamps
CREATE TRIGGER update_travels_timestamp 
    AFTER UPDATE ON travels
    FOR EACH ROW
    BEGIN
        UPDATE travels SET updated_at = datetime('now') WHERE id = NEW.id;
    END;

CREATE TRIGGER update_event_types_timestamp 
    AFTER UPDATE ON event_types
    FOR EACH ROW
    BEGIN
        UPDATE event_types SET updated_at = datetime('now') WHERE id = NEW.id;
    END;

CREATE TRIGGER update_events_timestamp 
    AFTER UPDATE ON events
    FOR EACH ROW
    BEGIN
        UPDATE events SET updated_at = datetime('now') WHERE id = NEW.id;
    END;
