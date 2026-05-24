from __future__ import annotations

import asyncio
import json
import threading
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Form, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessageChunk

from Backend import (
    chatbot,
    ingest_pdf,
    get_all_conversations_with_metadata,
    delete_thread,
    search_conversations,
    thread_document_metadata,
)
from database import create_conversation, load_conversation
from code_interpreter import list_workspace_files
from utils import generate_thread_id

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_DONE = object()


def _extract_chunk_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
        return "".join(parts)
    return ""


def _produce_tokens(message: str, thread_id: str, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> None:
    try:
        config = {"configurable": {"thread_id": thread_id}}
        for msg, _meta in chatbot.stream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            stream_mode="messages",
        ):
            if isinstance(msg, AIMessageChunk) and msg.content:
                text = _extract_chunk_content(msg.content)
                if text:
                    loop.call_soon_threadsafe(queue.put_nowait, text)
    except Exception as exc:
        loop.call_soon_threadsafe(queue.put_nowait, exc)
    finally:
        loop.call_soon_threadsafe(queue.put_nowait, _DONE)


async def stream_chat(message: str, thread_id: str) -> AsyncGenerator[str, None]:
    """Stream LLM tokens as Server-Sent Events for immediate client flush."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    worker = threading.Thread(
        target=_produce_tokens,
        args=(message, thread_id, loop, queue),
        daemon=True,
    )
    worker.start()

    while True:
        item = await queue.get()
        if item is _DONE:
            yield "data: [DONE]\n\n"
            break
        if isinstance(item, Exception):
            payload = json.dumps({"error": str(item)})
            yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
            break
        payload = json.dumps({"token": item})
        yield f"data: {payload}\n\n"


@app.post("/conversations")
async def create_conv():
    thread_id = generate_thread_id()
    create_conversation(thread_id, "Untitled")
    return {"thread_id": thread_id}


@app.post("/conversations/{thread_id}/messages")
async def send_message(thread_id: str, payload: dict = None):
    if payload is None:
        payload = {}
    message = payload.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="message required")

    return StreamingResponse(
        stream_chat(message, thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/conversations")
async def list_convs():
    return get_all_conversations_with_metadata()


@app.delete("/conversations/{thread_id}")
async def delete_conv(thread_id: str):
    result = delete_thread(thread_id)
    return {"success": result}


@app.post("/pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    thread_id: str = Form(...),
    filename: str = Form(None),
):
    filename = filename or file.filename
    file_bytes = await file.read()
    meta = ingest_pdf(file_bytes, thread_id, filename)
    return meta


@app.get("/files")
async def list_files(thread_id: str = Query(...)):
    files = list_workspace_files(thread_id)
    if not files:
        return {"files": [], "message": "No files uploaded yet"}
    return {"files": files, "message": f"{len(files)} file(s) available"}


@app.get("/search")
async def search(query: str):
    return search_conversations(query)


@app.get("/metadata/{thread_id}")
async def doc_meta(thread_id: str):
    return thread_document_metadata(thread_id)


@app.get("/messages/{thread_id}")
async def get_msgs(thread_id: str):
    return load_conversation(thread_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
