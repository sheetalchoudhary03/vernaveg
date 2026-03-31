## Overview
The project persists user accounts and session results in SQLite. The ER diagram captures two core entities — `users` and `results` — and their relationship (results recorded per user). Auxiliary app data (audio words/sentences) are file-based and not part of the DB schema.

## Entities & Attributes
- **users**
  - `id` (PK, integer, autoincrement)
  - `username` (text, unique)
  - `password_hash` (text)
  - `favorite_color` (text, default '')
  - `created_at` (datetime, default CURRENT_TIMESTAMP)
- **results**
  - `id` (PK, integer, autoincrement)
  - `name` (text, username of user who ran the session)
  - `wpm` (real)
  - `accuracy` (real)
  - `time_taken` (real)
  - `test_type` (text, e.g., 'test', 'practice', 'audio_test', 'game')
  - `created_at` (datetime, default CURRENT_TIMESTAMP)

## Relationships
- **users → results**: One-to-many
  - Each user can have many results.
  - Implemented via `results.name` referencing `users.username` (string reference; no FK constraint defined). In the diagram, show a one-to-many link from `users.username` to `results.name`.

## Diagram (Textual Representation)
- users(id PK, username UNIQUE, password_hash, favorite_color, created_at)
- results(id PK, name → users.username, wpm, accuracy, time_taken, test_type, created_at)
- Relationship: users 1 —— N results (by username)

## Notes
- No tables exist for audio content; words and sentences are loaded from text files (e.g., `audio_words.txt`).
- If desired later, we can add a proper foreign key `results.user_id` referencing `users.id` for stronger integrity and faster joins.

## Next Steps (on approval)
1. Deliver a visual ER diagram (PNG/SVG) matching the above.
2. Optionally migrate to `results.user_id` with FK to `users.id`, backfill from `results.name`, and update inserts/queries.