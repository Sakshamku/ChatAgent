# ChatAgent Frontend

This folder contains the single frontend for ChatAgent. The legacy Streamlit UI has been removed, so all user-facing frontend work should live here.

## Main Features

- Chat interface connected to the FastAPI backend.
- Conversation sidebar and message history.
- PDF upload and document-aware chat support.
- Mock Test Arena page for DSA, aptitude, verbal, logical reasoning, and programming concept practice.
- Aptitude test flow with generated questions, timer, scoring, and topic feedback.

## Run Locally

Start the backend from the project root:

```powershell
cd D:\ChatAgent
myvnv\Scripts\uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend:

```powershell
cd D:\ChatAgent\next-frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Important Folders

```text
next-frontend/
|-- app/                  # Next.js routes
|-- components/           # UI components
|-- hooks/                # React hooks
|-- lib/                  # API helpers
`-- public/               # Static assets
```

The Mock Test Arena route lives at:

```text
app/mock-test-arena/page.tsx
```

The main Mock Test Arena UI component lives at:

```text
components/MockTestArena.tsx
```
