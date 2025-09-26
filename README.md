# Simple Expense Tracker

## Quick start

1. Build and run with Docker Compose:
   ```
   docker-compose up --build
   ```
   App will be available at http://localhost:5000

2. Add expenses using the web UI, filter, sort, and view summaries.

## Notes
- Uses SQLite stored in `backend/data/expenses.db` (persisted via volume).
- To reset data, stop container and delete `backend/data/expenses.db`.
