# Frontend Rewrite Plan – Next.js + TailwindCSS (Preserving Existing Backend Logic)

## 1. Context
The current application is a **single Streamlit process** where `Frontend.py` imports backend functions directly from `Backend.py`. All UI interactions (PDF ingestion, message history, code execution, analytics) happen in‑process. To migrate to a **Next.js + TailwindCSS** frontend we must:

1. **Extract an HTTP API layer** that wraps the existing backend functions.
2. **Preserve all existing functionality** – no breaking changes to the backend logic.
3. **Maintain streaming token‑by‑token UI** using SSE or WebSockets.
4. **Add Tailwind‑styled React components** that replicate the Streamlit UX (sidebar, chat, file upload, status indicators).

This plan outlines the steps, file changes, and verification measures needed to achieve a drop‑in replacement frontend that does **not affect** the current backend code.

---

## 2. Goal
- Create a **Next.js application** (v14) that runs alongside the existing Streamlit app.
- Replace the Streamlit UI with a **Tailwind‑styled React UI** that:
  - Lists conversations, allows creation/deletion, search.
  - Streams LLM responses token‑by‑token.
  - Handles PDF upload and workspace file management.
  - Displays code artifacts, charts, and downloadable files.
- Ensure the **backend API surface remains unchanged** (same function signatures, same DB interactions).
- Keep the existing **SQLite `chatbot.db`** as the data store; no schema changes.

---

## 3. Approach Overview
| Phase | Action | Files / Tools |
|------|--------|---------------|
| **A** | **Create API endpoints** that call the same backend functions used by Streamlit. | `Backend.py` (unchanged) + new **FastAPI** (or **Flask**) layer (e.g., `api/main.py`). |
| **B** | **Expose existing functions** via REST routes: <br>• `POST /conversations` → `create_conversation` <br>• `POST /conversations/{id}/messages` → invoke `chatbot` and stream response <br>• `GET /conversations` → `get_all_conversations_with_metadata` <br>• `DELETE /conversations/{id}` → `delete_thread` <br>• `POST /pdf` → `ingest_pdf` <br>• `GET /files` → `list_uploaded_files` <br>• `GET /search` → `search_conversations` | New **API server** (`api/`). |
| **C** | **Implement streaming** with **Server‑Sent Events (SSE)** or **WebSockets** so the UI receives tokens incrementally. | `api/stream.py` (FastAPI `StreamingResponse`). |
| **D** | **Bootstrap Next.js app** with TailwindCSS. | `create-next-app@latest --ts` + `tailwindcss` config. |
| **E** | **Build UI components** mirroring the Streamlit layout: <br>• Sidebar with conversation list, search, delete, new‑chat buttons. <br>• Chat window with auto‑scroll, streaming placeholder, typing indicator. <br>• File upload component (PDF, CSV, XLSX, JSON, TXT). <br>• Artifact display (charts, downloadable files). | `components/` (e.g., `Sidebar.tsx`, `Chat.tsx`, `FileUploader.tsx`, `ArtifactRenderer.tsx`). |
| **F** | **Connect UI to API**: <br>• Use `fetch`/`axios` for REST calls. <br>• Use `EventSource` (SSE) for streaming responses. <br>• Manage state with React `useState`/`useEffect`. | `pages/api/*` (frontend proxy) or direct calls to the API server. |
| **G** | **Add Tailwind utilities** for animations, responsive layout, and theming (matching Streamlit CSS). | `tailwind.config.js`, `styles/globals.css`. |
| **H** | **Testing & Verification** – run both servers, verify end‑to‑end flow, ensure no data loss. | Postman / local UI test. |

---

## 4. Detailed File Changes

### 4.1 Backend – Add Minimal API Layer
Create **`api/main.py`** (FastAPI) that imports the existing backend functions and exposes them:

```python
# api/main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn
from typing import AsyncGenerator

app = FastAPI()

# Import backend symbols (unchanged)
from Backend import (
    chatbot,
    ingest_pdf,
    get_all_conversations_with_metadata,
    delete_thread,
    search_conversations,
    thread_document_metadata,
    get_conversation_messages,
    list_uploaded_files,
)

# ----------------------------------------------------------------------
# Helper: streaming wrapper around chatbot.invoke
# ----------------------------------------------------------------------
async def stream_chat(message: str, thread_id: str) -> AsyncGenerator[str, None]:
    """Yield response tokens from the LangGraph chatbot."""
    config = {"configurable": {"thread_id": thread_id}}
    response = chatbot.invoke({"messages": [HumanMessage(content=message)], config=config)
    full_msg = response.content
    # Yield character‑by‑character to emulate token streaming
    for i, ch in enumerate(full_msg):
        yield ch
        await asyncio.sleep(0.01)  # tiny pause for UX

# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@app.post("/conversations")
async def create_conv():
    # backend already creates conversation via DB; just return ID
    from database import create_conversation
    thread_id = generate_thread_id()
    create_conversation(thread_id, "Untitled")
    return {"thread_id": thread_id}

@app.post("/conversations/{thread_id}/messages")
async def send_message(thread_id: str, message: str):
    # Stream response back to front‑end
    return StreamingResponse(stream_chat(message, thread_id), media_type="text/event-stream")

@app.get("/conversations")
async def list_convs():
    return get_all_conversations_with_metadata()

@app.delete("/conversations/{thread_id}")
async def delete_conv(thread_id: str):
    return delete_thread(thread_id)

@app.post("/pdf")
async def upload_pdf(file: bytes = File(...), thread_id: str = Form(...), filename: str = Form(...)):
    meta = ingest_pdf(file, thread_id, filename)
    return meta

@app.get("/files")
async def list_files(thread_id: str = Query(...)):
    return list_uploaded_files(thread_id)

@app.get("/search")
async def search(query: str):
    return search_conversations(query)

@app.get("/metadata/{thread_id}")
async def doc_meta(thread_id: str):
    return thread_document_metadata(thread_id)

@app.get("/messages/{thread_id}")
async def get_msgs(thread_id: str):
    return get_conversation_messages(thread_id)
```

> **Note:** Only the API layer is added; **all business logic stays in `Backend.py`**.

### 4.2 Frontend – Next.js + Tailwind Setup
Run:

```bash
npx create-next-app@latest my-chat-app --ts
cd my-chat-app
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Configure `tailwind.config.js` to enable JIT mode and set `content: ["./src/**/*.{js,ts,jsx,tsx}"]`.

Add global styles in `src/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Custom scrollbars to mimic Streamlit */
html::-webkit-scrollbar { width: 8px; }
html::-webkit-scrollbar-thumb { background: #bbb; border-radius: 4px; }
```

Create layout components:

- `components/Sidebar.tsx` – renders conversation list, search input, delete button, new‑chat button (mirrors Streamlit sidebar).
- `components/Chat.tsx` – handles message display, auto‑scroll, typing indicator, streaming placeholder (replicates the JS from `Frontend.py`).
- `components/FileUploader.tsx` – supports PDF, CSV, XLSX, JSON, TXT upload; calls `/api/upload-pdf` and shows success messages.
- `components/ArtifactRenderer.tsx` – displays charts (image component) and downloadable file links.
- `components/StatusToast.tsx` – replicates Streamlit `st.toast` notifications.

All UI components will use **Tailwind utility classes** to achieve the same visual spacing, gradients, and button styles used in the original Streamlit CSS.

### 4.3 API Integration in Next.js
- Create an **`api/proxy.ts`** (or use `fetch` directly) to call the FastAPI server running on `http://localhost:8000`.
- For streaming, instantiate an **`EventSource`** that connects to `/conversations/{id}/messages/stream` and appends tokens to state.
- Use `useEffect` to manage auto‑scroll to the bottom after each new token (similar to `scrollToBottom` in the original JS).
- Mirror the **session state** logic (`thread_id`, `message_history`) using React’s `useState` and `useReducer`.

### 4.4 Preserve Backend Logic
- **Do not modify** any existing `Backend.py` code.
- **Do not change** the SQLite schema or DB file location.
- The API layer simply **calls** the same imported functions; therefore all existing unit logic, caching, and DB interactions remain untouched.

---

## 5. Verification & Validation Plan

| Step | Action | Expected Outcome |
|------|--------|------------------|
| **1** | Start **backend API** (`uvicorn api.main:app --reload`). | FastAPI docs available at `/docs`. |
| **2** | Launch **Next.js app** (`npm run dev`). | App runs at `http://localhost:3000` with Tailwind UI. |
| **3** | Open the UI, **create a new conversation**. | Backend receives `POST /conversations`, DB entry appears, conversation shows in sidebar. |
| **4** | Send a message → **streaming** using SSE. | Tokens appear token‑by‑token, typing indicator matches Streamlit animation. |
| **5** | Upload a **PDF** via the file uploader. | Request sent to `/pdf`, PDF processed, metadata displayed in sidebar. |
| **6** | Search conversations (search box). | Results returned via `/search`; UI updates list. |
| **7** | Delete a conversation. | `DELETE /conversations/{id}` called, entry removed from DB and sidebar. |
| **8** | Verify **artifacts** (charts, downloadable files) appear correctly and can be downloaded. | Files served from workspace directory, download links work. |
| **9** | Run existing **unit tests** (if any) to ensure backend functions still behave identically. | No regression in `Backend.py` behavior. |
| **10** | Compare **network payloads** between original Streamlit calls and new API calls – they should be equivalent (same request bodies, same response formats). | Confirm no data loss or mutation. |

---

## 6. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| **Breaking API contract** (e.g., missing field) | Keep function signatures identical; add explicit validation in FastAPI; write unit tests for each endpoint. |
| **Streaming mismatch** (token delay) | Use a small `await asyncio.sleep(0.01)` loop; adjust front‑end timing to match original JS delays. |
| **Tailwind styling divergence** | Base Tailwind theme on the existing Streamlit CSS values (colors, gradients, spacing). Use the same hex codes. |
| **CORS / same‑origin** | Run API on a different port but configure Next.js `proxy` in `package.json` (`"proxy": "http://localhost:8000"`). |
| **File‑system permissions** | Ensure the API user has read/write access to the workspace directory; reuse the same temporary file handling as Streamlit. |

---

## 7. Success Criteria
- The **Next.js UI** can fully replace the Streamlit UI without any changes to the backend logic.
- All **existing backend functions** are exercised through the new API with **identical results**.
- The UI **streams responses** token‑by‑token, **shows typing indicators**, **auto‑scrolls**, and **renders PDFs, charts, and files** exactly as before.
- No **database schema changes**; the `chatbot.db` file remains untouched.
- End‑to‑end functional testing passes, confirming parity with the original application.

---

**Next Steps**
1. Review this plan with you and confirm whether the **FastAPI** approach works for you, or if you prefer **Flask**/another framework.
2. Once approved, I will proceed to:
   - Implement the API layer (`api/main.py`).
   - Scaffold the Next.js + Tailwind project.
   - Build the core UI components and integrate streaming.
3. After each major step I will call **ExitPlanMode** to obtain your approval before moving forward.

Please let me know if any part of the plan needs adjustment or if you have a preferred backend web‑framework for the API layer.