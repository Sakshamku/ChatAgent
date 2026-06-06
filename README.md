# ChatAgent

ChatAgent is an AI assistant project with a Python backend, a Next.js frontend, persistent chat history, PDF-aware conversations, coding profile analytics, and a Mock Test Arena for interview preparation.

## Features

- Persistent chat history stored in SQLite.
- FastAPI backend for conversations, PDF uploads, messages, coding analytics, and mock tests.
- Next.js frontend in `next-frontend/`.
- PDF RAG support with per-thread document metadata and vector stores.
- Python code interpreter workspace for uploaded files and generated artifacts.
- LeetCode and GeeksforGeeks profile analytics.
- **Authentication system** for Mock Test Arena (Phase 1 ✅)
  - User registration & login with secure password hashing (bcrypt)
  - JWT token-based session management
  - Protected mock test endpoints with user isolation
  - Session persistence with localStorage
  - See [AUTHENTICATION.md](AUTHENTICATION.md) for details
- Mock Test Arena for DSA, aptitude, verbal ability, logical reasoning, and programming concept practice.
- Aptitude test generation with timed questions, scoring, topic analysis, and suggestions.
## Project Structure

```text
ChatAgent/
|-- backend/
|   |-- api/
|   |   `-- main.py              # FastAPI application and API routes
|   |-- coding_platforms/        # LeetCode/GFG fetchers and analytics helpers
|   |-- Backend.py               # LangGraph chatbot, tools, PDF RAG, mock interview logic
|   |-- code_interpreter.py      # Python execution workspace helpers
|   |-- coding_tools.py          # LangChain tools for coding analytics
|   |-- database.py              # SQLite database layer
|   |-- utils.py                 # Shared backend utilities
|   `-- requirements.txt         # Python dependencies
|-- next-frontend/               # Next.js frontend app
|-- tests/                       # Pytest tests
|-- data/                        # Local SQLite databases, ignored by Git
|-- memory/                      # Local vector stores and planning notes
|-- .env                         # Local API keys, ignored by Git
`-- .gitignore
```

## Mock Test Arena

The Mock Test Arena lets users practice interview-style tests from the frontend. The backend supports:

- Test catalog: `GET /mock-tests/catalog`
- Start a single-question adaptive mock test: `POST /mock-tests/start`
- Submit an answer and receive scoring/feedback: `POST /mock-tests/submit`
- View analytics and leaderboard data: `GET /mock-tests/analytics/{user_id}` and `GET /mock-tests/leaderboard`
- Generate a 20-question aptitude test: `POST /aptitude-tests/generate`
- Submit aptitude answers with topic-level analysis: `POST /aptitude-tests/submit`
- View previous aptitude attempts: `GET /aptitude-tests/attempts/{user_id}`

Supported practice areas include DSA, aptitude, verbal ability, logical reasoning, and programming concepts.

## Authentication (Phase 1)

The Mock Test Arena now includes user authentication. For complete setup, testing, and deployment details, see:

- **[AUTHENTICATION.md](AUTHENTICATION.md)** - Technical reference and architecture
- **[AUTH_QUICKSTART.md](AUTH_QUICKSTART.md)** - Setup guide, testing workflow, and API examples
- **[AUTH_CHANGELOG.md](AUTH_CHANGELOG.md)** - File manifest and change log

### Quick Overview
- **Signup/Login** - POST `/auth/signup` and `/auth/login` endpoints
- **Protected Endpoints** - All mock test endpoints require JWT token in `Authorization` header
- **Session Persistence** - Tokens stored in localStorage, auto-validate on app load
- **User Isolation** - Each user's test attempts and analytics are private
- **No Impact on Chat** - Chat system remains completely unchanged

To get started: See [AUTH_QUICKSTART.md](AUTH_QUICKSTART.md) section 2-3 for environment setup.

## Setup

### Backend

```powershell
cd D:\ChatAgent
myvnv\Scripts\activate
pip install -r backend\requirements.txt
```

Create a local `.env` file:

```env
MISTRAL_API_KEY=your_mistral_api_key_here
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
```

Run the FastAPI backend:

```powershell
myvnv\Scripts\uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
```

### Next.js Frontend

```powershell
cd D:\ChatAgent\next-frontend
npm install
npm run dev
```

Open the frontend at:

```text
http://localhost:3000
```

## Local Data

Runtime files are kept out of Git:

- `data/chat_history.db`
- `data/chatbot.db`
- `memory/vectorstores/`
- `.env`
- virtual environments such as `myvnv/`, `.venv/`, and `venv/`
- frontend build/dependency folders such as `node_modules/` and `.next/`

## Development

Run tests:

```powershell
pytest tests
```

Live LeetCode API tests are skipped by default. To enable them:

```powershell
$env:RUN_LEETCODE_LIVE_TESTS="1"
pytest tests
```

## Git Notes

Do not commit `.env`, local databases, virtual environments, `node_modules`, or build output. If any secret key was previously pushed to GitHub, rotate that key immediately even after removing the file from the repository.
