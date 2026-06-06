from __future__ import annotations

import os
import pickle
import re
import shutil
import sqlite3
import tempfile
from functools import lru_cache
from typing import Annotated, Any, Dict, Optional, TypedDict

import requests
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_mistralai import ChatMistralAI

from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from langgraph.checkpoint.sqlite import SqliteSaver

# Import database and utils
from backend.database import (
    create_conversation, save_message, load_conversation,
    get_all_conversations, delete_conversation, save_document_metadata,
    get_document_metadata, update_conversation_title, get_conversation_title,
    get_coding_profiles, get_latest_coding_stats, get_topic_stats,
    save_mock_interview_question, get_latest_mock_interview,
    save_mock_interview_answer
)
from backend.utils import (
    generate_thread_id, generate_chat_title, convert_langchain_messages_to_dict,
    convert_dict_to_langchain_messages, get_message_role, sanitize_filename
)
from backend.code_interpreter import (
    execute_python, format_execution_result,
    save_uploaded_file, list_workspace_files,
    get_workspace_file_path, cleanup_old_workspaces
)
from backend.coding_tools import (
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
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
VECTOR_STORE_DIR = os.path.join(PROJECT_ROOT, "memory", "vectorstores")
FALLBACK_RETRIEVER_FILE = "tfidf_retriever.pkl"


class TfidfRetriever:
    """Small offline retriever used when Hugging Face embeddings are unavailable."""

    def __init__(self, texts: list[str], metadatas: list[dict], k: int = 3):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.texts = texts
        self.metadatas = metadatas
        self.k = k
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
        self.matrix = self.vectorizer.fit_transform(texts)

    def invoke(self, query: str):
        from sklearn.metrics.pairwise import cosine_similarity

        if not self.texts:
            return []

        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix).ravel()
        top_indices = scores.argsort()[::-1][: self.k]

        return [
            Document(page_content=self.texts[index], metadata=self.metadatas[index])
            for index in top_indices
            if scores[index] > 0
        ]

# =========================================================
# Cached LLM
# =========================================================

@lru_cache(maxsize=1)
def get_llm():
    return ChatMistralAI(
        model="mistral-small-latest",
        api_key=os.getenv("MISTRAL_API_KEY"),
        streaming=True,
    )

# =========================================================
# Cached Embeddings
# =========================================================

@lru_cache(maxsize=1)
def get_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu", "local_files_only": True},
        encode_kwargs={"batch_size": 64},
    )

# =========================================================
# SQLite Checkpointer
# =========================================================

@lru_cache(maxsize=1)
def get_checkpointer():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(
        database=os.path.join(DATA_DIR, "chatbot.db"),
        check_same_thread=False
    )

    return SqliteSaver(conn=conn)

# =========================================================
# Retriever helpers
# =========================================================

def _get_retriever(thread_id: Optional[str]):
    if not thread_id:
        return None

    thread_key = str(thread_id)

    if thread_key in _THREAD_RETRIEVERS:
        return _THREAD_RETRIEVERS[thread_key]

    index_path = _thread_vector_store_path(thread_key)
    if os.path.isdir(index_path):
        fallback_path = _thread_fallback_retriever_path(thread_key)
        if os.path.isfile(fallback_path):
            try:
                with open(fallback_path, "rb") as retriever_file:
                    retriever = pickle.load(retriever_file)
                _THREAD_RETRIEVERS[thread_key] = retriever
                return retriever
            except Exception as exc:
                print(f"Error loading fallback retriever for thread {thread_key}: {exc}")

        try:
            from langchain_community.vectorstores import FAISS

            vector_store = FAISS.load_local(
                index_path,
                get_embeddings(),
                allow_dangerous_deserialization=True,
            )
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3},
            )
            _THREAD_RETRIEVERS[thread_key] = retriever
            return retriever
        except Exception as exc:
            print(f"Error loading vector store for thread {thread_key}: {exc}")

    return None


def _thread_vector_store_path(thread_id: str) -> str:
    safe_thread_id = sanitize_filename(str(thread_id))
    return os.path.join(VECTOR_STORE_DIR, safe_thread_id)


def _thread_fallback_retriever_path(thread_id: str) -> str:
    return os.path.join(_thread_vector_store_path(thread_id), FALLBACK_RETRIEVER_FILE)


def _format_pdf_context(thread_id: Optional[str], query: str) -> str:
    if not thread_id:
        return ""

    metadata = thread_document_metadata(str(thread_id))
    if not metadata:
        return ""

    retriever = _get_retriever(str(thread_id))
    if retriever is None:
        return (
            "\n\nUPLOADED PDF STATUS:\n"
            f"- A PDF named {metadata.get('filename', 'uploaded.pdf')} is attached, "
            "but its searchable index is not available. Ask the user to re-upload it."
        )

    docs = retriever.invoke(query)
    if not docs:
        return (
            "\n\nUPLOADED PDF STATUS:\n"
            f"- A PDF named {metadata.get('filename', 'uploaded.pdf')} is attached, "
            "but no relevant text was retrieved for this question."
        )

    context_parts = []
    for index, doc in enumerate(docs, start=1):
        page = doc.metadata.get("page")
        page_label = f" page {page + 1}" if isinstance(page, int) else ""
        context_parts.append(
            f"[Excerpt {index}{page_label}]\n{doc.page_content.strip()}"
        )

    return (
        "\n\nUPLOADED PDF CONTEXT:\n"
        f"Filename: {metadata.get('filename', 'uploaded.pdf')}\n"
        "Use this extracted document text to answer the user's request. "
        "Do not claim you cannot access uploads when context is present.\n\n"
        + "\n\n".join(context_parts)
    )

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
    thread_key = str(thread_id)
    save_uploaded_file(thread_key, safe_filename, file_bytes)
    
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

        texts = [chunk.page_content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        if not any(text.strip() for text in texts):
            raise ValueError("No readable text found in this PDF")

        index_path = _thread_vector_store_path(thread_key)
        if os.path.isdir(index_path):
            shutil.rmtree(index_path)
        os.makedirs(index_path, exist_ok=True)

        try:
            # Batch embed for speed: encode all texts at once, then add to FAISS.
            # local_files_only prevents upload from hanging on blocked Hugging Face network calls.
            embeddings = get_embeddings()
            vector_store = FAISS.from_texts(
                texts,
                embeddings,
                metadatas=metadatas
            )
            vector_store.save_local(index_path)

            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )
        except Exception as exc:
            print(f"FAISS/Hugging Face embedding unavailable, using TF-IDF fallback: {exc}")
            retriever = TfidfRetriever(texts, metadatas, k=3)
            with open(_thread_fallback_retriever_path(thread_key), "wb") as retriever_file:
                pickle.dump(retriever, retriever_file)

        _THREAD_RETRIEVERS[thread_key] = retriever

        metadata = {
            "filename": safe_filename,
            "documents": len(docs),
            "chunks": len(chunks),
        }

        _THREAD_METADATA[thread_key] = metadata
        
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


def _resume_interview_context(thread_id: Optional[str]) -> dict:
    if not thread_id:
        return {"has_resume": False, "text": "", "filename": None}

    metadata = thread_document_metadata(str(thread_id))
    retriever = _get_retriever(str(thread_id))
    if not metadata or retriever is None:
        return {"has_resume": False, "text": "", "filename": None}

    docs = retriever.invoke(
        "resume projects technical skills internship experience education achievements"
    )
    text = "\n\n".join(doc.page_content.strip() for doc in docs if doc.page_content.strip())
    return {
        "has_resume": bool(text),
        "text": text[:4000],
        "filename": metadata.get("filename"),
    }


def _coding_interview_context(thread_id: Optional[str]) -> dict:
    user_id = thread_id or "default_user"
    profiles = get_coding_profiles(user_id)
    platforms = [profile["platform"] for profile in profiles] or ["leetcode"]

    stats: dict[str, Any] = {}
    all_topics: list[dict[str, Any]] = []
    for platform in platforms:
        latest = get_latest_coding_stats(user_id, platform)
        if latest:
            stats[platform] = latest
        for topic in get_topic_stats(user_id, platform):
            all_topics.append({**topic, "platform": platform})

    weak_topics = sorted(
        all_topics,
        key=lambda topic: int(topic.get("solved_count") or 0),
    )[:5]

    return {
        "profiles": [{"platform": p["platform"], "username": p["username"]} for p in profiles],
        "stats": stats,
        "weak_topics": weak_topics,
    }


def _pick_resume_project(resume_text: str) -> str:
    candidates = re.findall(
        r"([A-Z][A-Za-z0-9 +&'/-]{4,80}(?:Planner|System|App|Platform|Portal|Assistant|Algorithm|Project))",
        resume_text,
    )
    if candidates:
        return candidates[0].strip()
    return "one of your resume projects"


@tool
def start_mock_interview(
    target_role: str = "software engineer",
    focus: str = "mixed",
    difficulty: str = "medium",
    thread_id: Optional[str] = None,
):
    """
    Start a personalized mock interview using the uploaded resume and coding profile data.

    Use this when the user asks to start a mock interview, practice interview,
    resume-based interview, project interview, or DSA interview.

    Args:
        target_role: Target job role, such as "software engineer" or "AI intern"
        focus: "mixed", "resume", "project", "dsa", or "behavioral"
        difficulty: "easy", "medium", or "hard"
        thread_id: Thread ID for resume/coding profile lookup
    """
    resume = _resume_interview_context(thread_id)
    coding = _coding_interview_context(thread_id)

    focus_key = focus.lower().strip()
    weak_topic = (
        coding["weak_topics"][0]["topic_name"]
        if coding["weak_topics"]
        else "arrays, graphs, or dynamic programming"
    )
    project_name = _pick_resume_project(resume["text"]) if resume["has_resume"] else "your strongest project"

    if focus_key in {"dsa", "coding"}:
        question = (
            f"You are interviewing for a {target_role} role. "
            f"Let's practice a {difficulty} DSA question from your weaker area: {weak_topic}. "
            "Explain your approach for this problem: given a realistic input size, how would you choose the data "
            "structure, analyze complexity, and handle edge cases before coding?"
        )
        expected_points = [
            "clarifies constraints and edge cases",
            "chooses an appropriate data structure or algorithm",
            "explains time and space complexity",
            "walks through an example",
            "mentions tradeoffs or optimizations",
        ]
    elif focus_key in {"resume", "project"}:
        question = (
            f"For a {target_role} interview, walk me through {project_name}. "
            "What problem did it solve, what architecture or algorithm did you use, what was your personal "
            "contribution, and how would you improve it if you had one more week?"
        )
        expected_points = [
            "states the problem and users clearly",
            "explains architecture or algorithm choices",
            "identifies personal contribution",
            "discusses measurable impact or outcome",
            "proposes a realistic improvement",
        ]
    elif focus_key == "behavioral":
        question = (
            f"Tell me about a challenging technical situation from your resume that is relevant to a "
            f"{target_role} role. Use the STAR format and include what you learned."
        )
        expected_points = [
            "uses situation-task-action-result structure",
            "shows ownership",
            "explains technical challenge",
            "includes a concrete result",
            "reflects on learning",
        ]
    else:
        question = (
            f"We'll do a mixed {target_role} mock interview. First question: choose one resume project, "
            f"preferably {project_name}, and explain how its core technical idea works. Then connect it to "
            f"one DSA topic you want to improve, such as {weak_topic}."
        )
        expected_points = [
            "selects a relevant resume project",
            "explains the core technical idea",
            "connects implementation to DSA or system design concepts",
            "communicates clearly and concisely",
            "mentions tradeoffs or improvements",
        ]

    interview_id = save_mock_interview_question(
        thread_id or "default",
        target_role,
        focus_key,
        difficulty,
        question,
        expected_points,
    )

    return {
        "interview_id": interview_id,
        "target_role": target_role,
        "focus": focus_key,
        "difficulty": difficulty,
        "question": question,
        "expected_points": expected_points,
        "resume_used": resume["has_resume"],
        "resume_file": resume["filename"],
        "coding_profiles": coding["profiles"],
        "weak_topics": coding["weak_topics"],
        "instruction": "Ask the question only, then wait for the user's answer. Do not score yet.",
    }


@tool
def evaluate_mock_interview_answer(
    answer: str,
    thread_id: Optional[str] = None,
):
    """
    Score the user's latest mock interview answer and provide feedback.

    Use this after the user answers a mock interview question.

    Args:
        answer: The user's interview answer
        thread_id: Thread ID for interview state lookup
    """
    latest = get_latest_mock_interview(thread_id or "default")
    if not latest:
        return {
            "error": "No active mock interview question found. Start a mock interview first."
        }

    normalized_answer = answer.lower()
    expected_points = latest.get("expected_points", [])
    covered_points = []
    missed_points = []

    for point in expected_points:
        keywords = [
            word for word in re.findall(r"[a-zA-Z]{4,}", point.lower())
            if word not in {"explains", "mentions", "states", "shows", "includes"}
        ]
        if any(keyword in normalized_answer for keyword in keywords):
            covered_points.append(point)
        else:
            missed_points.append(point)

    word_count = len(answer.split())
    structure_score = 20 if any(marker in normalized_answer for marker in ["first", "then", "finally", "because"]) else 10
    depth_score = min(25, max(5, word_count // 8))
    coverage_score = int((len(covered_points) / max(1, len(expected_points))) * 35)
    specificity_score = 20 if re.search(r"\b\d+%?|\bapi\b|\bdatabase\b|\balgorithm\b|\bcomplexity\b|\buser\b", normalized_answer) else 10
    total_score = min(100, structure_score + depth_score + coverage_score + specificity_score)

    feedback = {
        "question": latest["question"],
        "score": total_score,
        "covered_points": covered_points,
        "missed_points": missed_points,
        "strengths": [
            "You gave enough detail to evaluate." if word_count >= 45 else "You answered directly.",
            "Your answer touched the expected rubric." if covered_points else "You stayed on topic.",
        ],
        "improvements": [
            "Use a clearer structure: problem, approach, tradeoffs, result.",
            "Add concrete metrics, constraints, complexity, or impact.",
            "Tie the answer back to your resume or target role.",
        ],
        "next_question_hint": "Ask start_mock_interview again for the next question, or request a follow-up.",
    }

    save_mock_interview_answer(int(latest["id"]), answer, total_score, feedback)
    return feedback

# =========================================================
# Tools Setup
# =========================================================

tools = [
    calculator,
    get_stock_price,
    rag_tool,
    python_interpreter,
    list_uploaded_files,
    start_mock_interview,
    evaluate_mock_interview_answer,
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

    last_user_content = ""

    # Save new messages to database
    if thread_id and state.get("messages"):
        # Get only new messages (last one for user input)
        messages = state["messages"]
        if messages:
            # Save the last user message if it's a human message
            last_message = messages[-1]
            if isinstance(last_message, HumanMessage):
                last_user_content = str(last_message.content)
                save_message(thread_id, "user", last_message.content)
                
                # Generate and save title if this is the first message
                existing_title = get_conversation_title(thread_id)
                if not existing_title:
                    title = generate_chat_title(last_message.content)
                    create_conversation(thread_id, title)

    pdf_context = _format_pdf_context(thread_id, last_user_content)

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
            "MOCK INTERVIEW AGENT:\n"
            "- When the user asks to start a mock interview, practice interview, resume interview, project interview, or DSA interview, call start_mock_interview with thread_id=" + str(thread_id) + ".\n"
            "- Ask exactly one interview question at a time and wait for the user's answer.\n"
            "- When the user answers an active mock interview question, call evaluate_mock_interview_answer with thread_id=" + str(thread_id) + " and score the answer.\n"
            "- After scoring, give concise feedback, a stronger sample answer outline, and offer the next question.\n\n"
            "TOOL USAGE:\n"
            "- If UPLOADED PDF CONTEXT is provided below, answer from that context directly.\n"
            "- Never say you cannot access file uploads when UPLOADED PDF CONTEXT is present.\n"
            "- Use rag_tool for follow-up PDF questions with thread_id=" + str(thread_id) + ".\n"
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
            + pdf_context
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
    from backend.database import search_conversations as db_search
    return db_search(query)

