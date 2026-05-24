from __future__ import annotations

import os
import sqlite3
import tempfile
from functools import lru_cache
from typing import Annotated, Any, Dict, Optional, TypedDict

import requests
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_mistralai import ChatMistralAI

from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from langgraph.checkpoint.sqlite import SqliteSaver

# Import database and utils
from database import (
    create_conversation, save_message, load_conversation,
    get_all_conversations, delete_conversation, save_document_metadata,
    get_document_metadata, update_conversation_title, get_conversation_title
)
from utils import (
    generate_thread_id, generate_chat_title, convert_langchain_messages_to_dict,
    convert_dict_to_langchain_messages, get_message_role, sanitize_filename
)
from code_interpreter import (
    execute_python, format_execution_result,
    save_uploaded_file, list_workspace_files,
    get_workspace_file_path, cleanup_old_workspaces
)
from coding_tools import (
    get_leetcode_stats, get_gfg_stats,
    analyze_coding_topics, weakest_topic_analysis,
    strongest_topic_analysis, generate_coding_roadmap,
    contest_analysis, coding_progress_summary,
    list_connected_profiles
)

load_dotenv()

# =========================================================
# In-memory stores
# =========================================================

_THREAD_RETRIEVERS: Dict[str, Any] = {}
_THREAD_METADATA: Dict[str, dict] = {}

# =========================================================
# Cached LLM
# =========================================================

@lru_cache(maxsize=1)
def get_llm():
    return ChatMistralAI(
        model="mistral-small-latest",
        api_key=os.getenv("MISTRAL_API_KEY"),
    )

# =========================================================
# Cached Embeddings
# =========================================================

@lru_cache(maxsize=1)
def get_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"batch_size": 64},
    )

# =========================================================
# SQLite Checkpointer
# =========================================================

@lru_cache(maxsize=1)
def get_checkpointer():
    conn = sqlite3.connect(
        database="chatbot.db",
        check_same_thread=False
    )

    return SqliteSaver(conn=conn)

# =========================================================
# Retriever helpers
# =========================================================

def _get_retriever(thread_id: Optional[str]):
    if thread_id and thread_id in _THREAD_RETRIEVERS:
        return _THREAD_RETRIEVERS[thread_id]

    return None

# =========================================================
# PDF Ingestion
# =========================================================

def ingest_pdf(
    file_bytes: bytes,
    thread_id: str,
    filename: Optional[str] = None
):
    """
    Lazy-load heavy libraries only when needed.
    Integrates with database for persistent storage.
    """

    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.vectorstores import FAISS

    if not file_bytes:
        raise ValueError("No PDF uploaded")

    # Sanitize filename
    safe_filename = sanitize_filename(filename or "uploaded.pdf")
    
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ) as temp_file:

        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        loader = PyPDFLoader(temp_path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200
        )

        chunks = splitter.split_documents(docs)

        # Batch embed for speed: encode all texts at once, then add to FAISS
        embeddings = get_embeddings()
        texts = [chunk.page_content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        # FAISS.from_texts uses batch encoding internally
        vector_store = FAISS.from_texts(
            texts,
            embeddings,
            metadatas=metadatas
        )

        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )

        _THREAD_RETRIEVERS[str(thread_id)] = retriever

        metadata = {
            "filename": safe_filename,
            "documents": len(docs),
            "chunks": len(chunks),
        }

        _THREAD_METADATA[str(thread_id)] = metadata
        
        # Save to database
        save_document_metadata(
            thread_id=thread_id,
            filename=safe_filename,
            chunks=len(chunks),
            pages=len(docs),
            file_size=len(file_bytes)
        )

        return metadata

    finally:
        try:
            os.remove(temp_path)
        except:
            pass

# =========================================================
# Tools
# =========================================================

@tool
def calculator(
    first_num: float,
    second_num: float,
    operation: str
):
    """
    Basic calculator tool.
    """

    operations = {
        "add": first_num + second_num,
        "sub": first_num - second_num,
        "mul": first_num * second_num,
    }

    if operation == "div":
        if second_num == 0:
            return {"error": "Division by zero"}

        return {"result": first_num / second_num}

    if operation not in operations:
        return {"error": "Unsupported operation"}

    return {"result": operations[operation]}

@tool
def get_stock_price(symbol: str):
    """
    Get latest stock price from Alpha Vantage.
    """

    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    if not api_key:
        return {"error": "Missing API key"}

    url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE"
        f"&symbol={symbol}"
        f"&apikey={api_key}"
    )

    try:
        response = requests.get(url, timeout=10)

        return response.json()

    except Exception as e:
        return {"error": str(e)}

@tool
def rag_tool(
    query: str,
    thread_id: Optional[str] = None
):
    """
    Retrieve PDF context.
    """

    retriever = _get_retriever(thread_id)

    if retriever is None:
        return {
            "error": "No PDF uploaded"
        }

    docs = retriever.invoke(query)

    return {
        "query": query,
        "context": [doc.page_content for doc in docs],
        "metadata": [doc.metadata for doc in docs],
    }

@tool
def python_interpreter(
    code: str,
    thread_id: Optional[str] = None
):
    """
    Execute Python code in a secure sandbox.
    
    Use this tool to:
    - Perform calculations and math operations
    - Analyze CSV/Excel/data files using pandas
    - Generate charts and visualizations using matplotlib/plotly/seaborn
    - Process and clean datasets
    - Perform statistical analysis
    - Create tables and reports
    - Generate downloadable files (CSV, JSON, etc.)
    
    The code runs in an isolated environment with access to:
    pandas, numpy, matplotlib, plotly, seaborn, scipy, sklearn, openpyxl
    
    Uploaded files are available in the current directory.
    Use matplotlib savefig() or pandas to_csv()/to_excel() to generate output files.
    
    Args:
        code: Python code to execute
        thread_id: Thread ID for file access and workspace isolation
    """
    result = execute_python(code, thread_id or "default")
    
    # Format result for the AI
    formatted = format_execution_result(result)
    
    return {
        "success": result["success"],
        "output": formatted,
        "charts_count": len(result.get("charts", [])),
        "files_generated": [f["name"] for f in result.get("files", [])],
        "execution_time": result.get("execution_time", 0),
        "error": result.get("error"),
    }

@tool
def list_uploaded_files(
    thread_id: Optional[str] = None
):
    """
    List files that have been uploaded to the current conversation workspace.
    Use this before analyzing files to see what's available.
    
    Args:
        thread_id: Thread ID for workspace
    """
    files = list_workspace_files(thread_id or "default")
    if not files:
        return {"files": [], "message": "No files uploaded yet"}
    return {"files": files, "message": f"{len(files)} file(s) available"}

# =========================================================
# Tools Setup
# =========================================================

tools = [
    calculator,
    get_stock_price,
    rag_tool,
    python_interpreter,
    list_uploaded_files,
    # Coding Profile Analytics Tools
    get_leetcode_stats,
    get_gfg_stats,
    analyze_coding_topics,
    weakest_topic_analysis,
    strongest_topic_analysis,
    generate_coding_roadmap,
    contest_analysis,
    coding_progress_summary,
    list_connected_profiles,
]

llm_with_tools = get_llm().bind_tools(tools)

# =========================================================
# Graph State
# =========================================================

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# =========================================================
# Chat Node
# =========================================================

def chat_node(state: ChatState, config=None):
    """Chat node with database integration for message persistence"""
    thread_id = None

    if config:
        thread_id = (
            config.get("configurable", {})
            .get("thread_id")
        )

    # Save new messages to database
    if thread_id and state.get("messages"):
        # Get only new messages (last one for user input)
        messages = state["messages"]
        if messages:
            # Save the last user message if it's a human message
            last_message = messages[-1]
            if isinstance(last_message, HumanMessage):
                save_message(thread_id, "user", last_message.content)
                
                # Generate and save title if this is the first message
                existing_title = get_conversation_title(thread_id)
                if not existing_title:
                    title = generate_chat_title(last_message.content)
                    create_conversation(thread_id, title)

    system_message = SystemMessage(
        content=(
            "You are a helpful AI assistant with code execution and coding analytics capabilities. "
            "You can write code in ANY programming language the user requests (Python, JavaScript, Java, C++, C#, Go, Rust, TypeScript, PHP, Ruby, Swift, Kotlin, SQL, HTML/CSS, R, MATLAB, Shell/Bash, Scala, etc.).\n\n"
            "RESPONSE FORMATTING (always use Markdown):\n"
            "- Use **bold** for key terms and section labels.\n"
            "- Use bullet lists (- item) or numbered lists for steps and options.\n"
            "- Use ### headings to organize longer answers.\n"
            "- Use `inline code` for commands, variables, and short snippets.\n"
            "- Use fenced code blocks with language tags for multi-line code.\n"
            "- Keep paragraphs short and scannable.\n\n"
            "CODE GENERATION RULES:\n"
            "- When the user asks for code in a specific language, generate clean, well-commented code in that language.\n"
            "- Always wrap code in markdown code blocks with the correct language tag (```python, ```javascript, ```java, etc.).\n"
            "- Include brief explanations before and after the code.\n"
            "- For Python code that needs execution (calculations, data analysis, charts, file processing), use the python_interpreter tool with thread_id=" + str(thread_id) + ".\n"
            "- For non-Python languages, generate the code as a formatted code block — it will be displayed with syntax highlighting.\n"
            "- If the user doesn't specify a language, default to Python.\n\n"
            "CODING ANALYTICS (LeetCode / GFG):\n"
            "- When the user asks about coding profiles, use get_leetcode_stats or get_gfg_stats to fetch their profile.\n"
            "- When the user asks about topic analysis, use analyze_coding_topics.\n"
            "- When the user asks about weakest/strongest topics, use weakest_topic_analysis or strongest_topic_analysis.\n"
            "- When the user asks for a roadmap or study plan, use generate_coding_roadmap.\n"
            "- When the user asks about contest performance, use contest_analysis.\n"
            "- When the user asks for overall progress or FAANG readiness, use coding_progress_summary.\n"
            "- When the user asks about connected profiles, use list_connected_profiles.\n"
            "- Always pass thread_id=" + str(thread_id) + " to these tools.\n"
            "- After fetching stats, provide insightful analysis and actionable recommendations.\n\n"
            "TOOL USAGE:\n"
            "- Use rag_tool for PDF questions with thread_id=" + str(thread_id) + ".\n"
            "- Use python_interpreter for Python execution (math, data analysis, charts, file processing).\n"
            "- Use list_uploaded_files to check available files before analysis.\n"
            "- When generating charts, use matplotlib savefig() to save them.\n"
            "- When generating data files, use pandas to_csv() or to_excel().\n"
            "- Pass thread_id=" + str(thread_id) + " to all tools that accept it.\n\n"
            "CODE QUALITY:\n"
            "- Write production-quality code with proper error handling.\n"
            "- Add helpful comments explaining key logic.\n"
            "- Follow language-specific conventions and best practices.\n"
            "- Suggest alternative approaches when relevant."
        )
    )

    response = llm_with_tools.invoke(
        [system_message, *state["messages"]],
        config=config,
    )
    
    # Save assistant response to database
    if thread_id and hasattr(response, 'content'):
        save_message(thread_id, "assistant", response.content)

    return {
        "messages": [response]
    }

# =========================================================
# Cached Chatbot
# =========================================================

@lru_cache(maxsize=1)
def get_chatbot():

    graph = StateGraph(ChatState)

    graph.add_node("chat_node", chat_node)

    graph.add_node(
        "tools",
        ToolNode(tools)
    )

    graph.add_edge(START, "chat_node")

    graph.add_conditional_edges(
        "chat_node",
        tools_condition
    )

    graph.add_edge("tools", "chat_node")

    return graph.compile(
        checkpointer=get_checkpointer()
    )

chatbot = get_chatbot()

# =========================================================
# Helpers
# =========================================================

def retrieve_all_threads():
    """
    Get all conversation threads from database.
    """
    conversations = get_all_conversations()
    return [conv["thread_id"] for conv in conversations]

def thread_document_metadata(thread_id: str):
    """
    Get document metadata from database or memory store.
    """
    # First try database
    db_metadata = get_document_metadata(thread_id)
    if db_metadata:
        return {
            "filename": db_metadata["filename"],
            "documents": db_metadata["pages"],
            "chunks": db_metadata["chunks"]
        }
    
    # Fallback to memory store
    return _THREAD_METADATA.get(str(thread_id), {})

def get_conversation_messages(thread_id: str):
    """
    Load conversation messages from database.
    """
    db_messages = load_conversation(thread_id)
    return convert_dict_to_langchain_messages(db_messages)

def get_all_conversations_with_metadata():
    """
    Get all conversations with full metadata for frontend.
    """
    conversations = get_all_conversations()
    
    result = []
    for conv in conversations:
        thread_id = conv["thread_id"]
        
        # Add document metadata
        doc_meta = get_document_metadata(thread_id)
        
        result.append({
            **conv,
            "document": doc_meta,
            "has_pdf": bool(doc_meta)
        })
    
    return result

def delete_thread(thread_id: str) -> bool:
    """
    Delete a thread and all its data.
    """
    # Remove from memory stores
    _THREAD_RETRIEVERS.pop(str(thread_id), None)
    _THREAD_METADATA.pop(str(thread_id), None)
    
    # Delete from database
    return delete_conversation(thread_id)

def search_conversations(query: str):
    """
    Search conversations by title or content.
    """
    from database import search_conversations as db_search
    return db_search(query)

