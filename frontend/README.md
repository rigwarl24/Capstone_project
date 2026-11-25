# CodeRace – Frontend (Member 1)

Pages: `index`, `login`, `register`, `profile`, `leaderboard`, `arena`.
Stack: HTML5 + Tailwind (CDN) + JavaScript + Monaco Editor.

## Run locally
```bash
cd frontend
python3 -m http.server 5500
# open http://localhost:5500
```

## Connect the backend
- `js/common.js`: set `USE_MOCK = false` and configure `API_URL`.
- Endpoints expected from Member 2: `POST /auth/register`, `POST /auth/login`, `GET /leaderboard`, `GET /users/me/matches`.
- `js/arena.js`: `window.arena.onOpponentUpdate`, `onTestResult` and `onMatchEnd` are the hooks for Members 4 and 5.
