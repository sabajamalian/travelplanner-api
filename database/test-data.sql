-- Travel Planner Test Data
-- Run this after schema.sql to add sample data

-- Event types
INSERT INTO event_types (name, category, color, icon) VALUES
    ('Hotel', 'accommodation', '#28a745', '🏨'),
    ('Hostel', 'accommodation', '#28a745', '🏨'),
    ('Rental', 'accommodation', '#28a745', '🏨'),
    ('Flight', 'transportation', '#17a2b8', '✈️'),
    ('Train', 'transportation', '#17a2b8', '🚄'),
    ('Bus', 'transportation', '#17a2b8', '🚌'),
    ('Car', 'transportation', '#17a2b8', '🚗'),
    ('Museum', 'activity', '#ffc107', '🎯'),
    ('Park', 'activity', '#ffc107', '🏞️'),
    ('Tour', 'activity', '#ffc107', '🎯'),
    ('Hiking', 'activity', '#ffc107', '🏔️'),
    ('Restaurant', 'food', '#fd7e14', '🍽️'),
    ('Cafe', 'food', '#fd7e14', '☕'),
    ('Bar', 'food', '#fd7e14', '🍺'),
    ('Shopping', 'shopping', '#6f42c1', '🛍️'),
    ('Market', 'shopping', '#6f42c1', '🛒'),
    ('Entertainment', 'entertainment', '#e83e8c', '🎭'),
    ('Theater', 'entertainment', '#e83e8c', '🎭'),
    ('Concert', 'entertainment', '#e83e8c', '🎵'),
    ('Movie', 'entertainment', '#e83e8c', '🎬');

-- Sample travels
INSERT INTO travels (title, description, start_date, end_date, destination) VALUES
    ('Weekend in Paris', 'A romantic weekend getaway to the City of Light', '2024-06-15', '2024-06-17', 'Paris, France'),
    ('Business Trip to Tokyo', 'Annual business meeting with Japanese partners', '2024-07-20', '2024-07-25', 'Tokyo, Japan'),
    ('Summer Vacation in Bali', 'Relaxing beach vacation with family', '2024-08-10', '2024-08-20', 'Bali, Indonesia');

-- Sample events
INSERT INTO events (travel_id, title, description, event_type_id, start_datetime, end_datetime, location) VALUES
    (1, 'Flight to Paris', 'Direct flight from home airport', 4, '2024-06-15T08:00:00', '2024-06-15T11:00:00', 'Charles de Gaulle Airport'),
    (1, 'Check-in at Hotel', 'Luxury hotel in the heart of Paris', 1, '2024-06-15T14:00:00', '2024-06-15T15:00:00', 'Hotel Ritz Paris'),
    (1, 'Eiffel Tower Visit', 'Evening visit to see the lights', 10, '2024-06-15T19:00:00', '2024-06-15T21:00:00', 'Eiffel Tower'),
    (1, 'Dinner at French Restaurant', 'Traditional French cuisine', 12, '2024-06-15T21:30:00', '2024-06-15T23:30:00', 'Le Comptoir du Relais'),
    (2, 'Flight to Tokyo', 'Business class flight', 4, '2024-07-20T10:00:00', '2024-07-20T14:00:00', 'Narita International Airport'),
    (2, 'Business Meeting', 'Annual partnership review', 17, '2024-07-21T09:00:00', '2024-07-21T17:00:00', 'Tokyo Business Center'),
    (2, 'Sushi Dinner', 'Traditional sushi experience', 12, '2024-07-21T19:00:00', '2024-07-21T21:00:00', 'Sukiyabashi Jiro');
