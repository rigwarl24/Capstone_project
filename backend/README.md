# CodeRace Backend – Database & REST API (Member 2)

Owner: Hafiza Alizada

- `database/` – MySQL schema and seed scripts
- `app/` – FastAPI application (auth, profile, match history, leaderboard)


## Database setup (Windows PowerShell)

Run from the repository root (`Capstone_project`):

    cmd /c "mysql -u root -p < backend\database\schema.sql"

This creates the `coderace` database with 4 tables: users, problems, testcases, matches.
Warning: re-running it deletes all data in these tables.