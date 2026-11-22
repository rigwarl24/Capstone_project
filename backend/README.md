# CodeRace Backend – Database & REST API (Member 2)

Owner: Hafiza Alizada

- `database/` – MySQL schema and seed scripts
- `app/` – FastAPI application (auth, profile, match history, leaderboard)


## Database setup (Windows PowerShell)

Run from the repository root (`Capstone_project`):

    cmd /c "mysql -u root -p < backend\database\schema.sql"

This creates the `coderace` database with 4 tables: users, problems, testcases, matches.
Warning: re-running it deletes all data in these tables.


## Running the API (Windows PowerShell)

1. Create the app database user (once), logged in as root with `mysql -u root -p`:

       CREATE USER IF NOT EXISTS 'coderace_app'@'localhost' IDENTIFIED BY 'choose-a-password';
       GRANT SELECT, INSERT, UPDATE, DELETE ON coderace.* TO 'coderace_app'@'localhost';

2. From the `backend` folder:

       python -m venv .venv
       .venv\Scripts\Activate.ps1
       python -m pip install -r requirements.txt
       copy .env.example .env

3. Edit `.env` and set `DB_PASSWORD` to the app user's password (never commit `.env`).
4. Start the server:

       uvicorn app.main:app --reload

- Health check: http://127.0.0.1:8000/api/health
- Interactive API docs: http://127.0.0.1:8000/docs

### Troubleshooting

- **"Access denied for user 'coderace_app'"**: the password in `.env` does not match MySQL. Restart the server after editing `.env`.
- **"An Application Control policy has blocked this file"** (Windows Smart App Control): reinstall SQLAlchemy without compiled files:

      $env:DISABLE_SQLALCHEMY_CEXT = "1"
      python -m pip install --force-reinstall --no-deps --no-binary sqlalchemy sqlalchemy==2.1.9