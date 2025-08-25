# Travel Planner Database

## Setup

1. **Create database**: `sqlite3 travelplanner.db < schema.sql`
2. **Add sample data**: `sqlite3 travelplanner.db < test-data.sql`

## Files

- `schema.sql` - Database structure (tables, indexes, triggers)
- `test-data.sql` - Sample data for development

## What You Get

- 4 tables: travels, event_types, events, event_attachments
- 22 performance indexes for fast calendar queries
- 20 event types with colors and icons
- 3 sample travels with 7 sample events
