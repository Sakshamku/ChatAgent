from __future__ import annotations

import asyncio
import hashlib
import json
import random
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
from coding_platforms.gfg import fetch_gfg_profile
from coding_platforms.leetcode import fetch_leetcode_contests, fetch_leetcode_profile, fetch_leetcode_topics
from database import (
    create_conversation,
    create_mock_test_attempt,
    get_mock_test_analytics,
    get_mock_test_attempt,
    get_mock_test_attempt_questions,
    get_mock_test_question,
    get_previous_mock_test_attempts,
    get_recent_mock_test_prompts,
    load_conversation,
    save_coding_profile,
    save_coding_stats,
    save_mock_test_answer,
    save_mock_test_question,
    complete_mock_test_attempt,
    save_topic_stats,
    update_conversation_title,
)
from code_interpreter import list_workspace_files
from utils import generate_thread_id, generate_chat_title

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_DONE = object()

MOCK_TEST_META = {
    "dsa": {
        "title": "DSA Mock Test",
        "topics": ["Arrays", "Graphs", "Dynamic Programming", "Trees", "Greedy"],
    },
    "aptitude": {
        "title": "Aptitude Mock Test",
        "topics": [
            "Profit & Loss", "Time & Work", "Percentage", "Ratio & Proportion",
            "Number System", "Probability", "Permutation & Combination",
            "Data Interpretation", "Time Speed Distance",
        ],
    },
    "verbal": {
        "title": "Verbal Ability Mock Test",
        "topics": [
            "Grammar Correction", "Sentence Improvement", "Synonyms/Antonyms",
            "Reading Comprehension", "Vocabulary", "Para Jumbles", "Fill in the Blanks",
        ],
    },
    "logical": {
        "title": "Logical Reasoning Mock Test",
        "topics": [
            "Coding-Decoding", "Blood Relations", "Seating Arrangement", "Syllogism",
            "Puzzle", "Direction Sense", "Statement & Conclusion", "Analogy", "Series Completion",
        ],
    },
    "programming": {
        "title": "Programming Concepts Mock Test",
        "topics": [
            "OOPs", "DBMS", "Operating System", "Computer Networks", "Memory Management",
            "Exception Handling", "Multithreading", "API Concepts", "Output Prediction", "Debugging",
        ],
    },
}

APTITUDE_TOPICS = [
    "Percentage",
    "Profit and Loss",
    "Time and Work",
    "Time Speed Distance",
    "Ratio and Proportion",
    "Probability",
    "Permutation and Combination",
    "Number System",
    "Simple Interest & Compound Interest",
    "Data Interpretation",
]

APTITUDE_DIFFICULTIES = ["easy"] * 6 + ["medium"] * 10 + ["hard"] * 4


def _user_id_from_payload(payload: dict) -> str:
    return str(payload.get("user_id") or payload.get("thread_id") or "default_user")


def _adaptive_difficulty(total_solved: int, requested: str | None = None) -> str:
    if requested in {"easy", "medium", "hard"}:
        return requested
    if total_solved < 100:
        return "easy"
    if total_solved < 350:
        return "medium"
    return "hard"


def _seeded_choice(options: list[str], seed_parts: list[str], recent_prompts: list[str]) -> str:
    seed = int(hashlib.sha256("|".join(seed_parts).encode("utf-8")).hexdigest(), 16)
    rng = random.Random(seed)
    shuffled = options[:]
    rng.shuffle(shuffled)
    for option in shuffled:
        if all(option not in prompt for prompt in recent_prompts):
            return option
    return shuffled[0]


def _load_profile_context(user_id: str, payload: dict) -> dict:
    context = {
        "leetcode": None,
        "gfg": None,
        "topics": [],
        "contests": [],
        "total_solved": 0,
    }

    leetcode_username = (payload.get("leetcode_username") or "").strip()
    if leetcode_username:
        profile = fetch_leetcode_profile(leetcode_username)
        if "error" not in profile:
            topics = fetch_leetcode_topics(leetcode_username) or []
            contests = fetch_leetcode_contests(leetcode_username) or []
            save_coding_profile(user_id, "leetcode", leetcode_username)
            save_coding_stats(user_id, "leetcode", profile)
            if topics:
                save_topic_stats(user_id, "leetcode", topics)
            context["leetcode"] = {"username": leetcode_username, **profile}
            context["topics"].extend(topics)
            context["contests"].extend(contests)
            context["total_solved"] += int(profile.get("total_solved") or 0)

    gfg_username = (payload.get("gfg_username") or "").strip()
    if gfg_username:
        profile = fetch_gfg_profile(gfg_username)
        if "error" not in profile:
            save_coding_profile(user_id, "gfg", gfg_username)
            save_coding_stats(user_id, "gfg", profile)
            context["gfg"] = {"username": gfg_username, **profile}
            context["total_solved"] += int(profile.get("total_problems_solved") or 0)

    return context


def _weak_topic_from_context(test_type: str, profile_context: dict, recent_prompts: list[str]) -> str:
    topics = profile_context.get("topics") or []
    if topics:
        sorted_topics = sorted(topics, key=lambda topic: int(topic.get("solved_count") or 0))
        if sorted_topics:
            return sorted_topics[0].get("topic_name") or sorted_topics[0].get("name") or "Arrays"
    return _seeded_choice(
        MOCK_TEST_META[test_type]["topics"],
        [test_type, str(len(recent_prompts))],
        recent_prompts,
    )


def _generate_mock_question(test_type: str, payload: dict, profile_context: dict, recent_prompts: list[str]) -> dict:
    total_solved = int(profile_context.get("total_solved") or 0)
    difficulty = _adaptive_difficulty(total_solved, payload.get("difficulty"))
    topic = _weak_topic_from_context(test_type, profile_context, recent_prompts)
    language = payload.get("language") or "Python"

    if test_type == "dsa":
        function_name = re_safe_name(topic)
        prompt = (
            f"Personalized {difficulty.title()} DSA Problem - {topic}\n\n"
            f"You are given input related to {topic.lower()}. Design an algorithm that returns the required result "
            "while handling duplicate values, empty inputs, and large constraints.\n\n"
            "Constraints:\n"
            "- 1 <= n <= 2 * 10^5\n"
            "- Values can be negative or repeated\n"
            "- Optimize for interview-quality complexity\n\n"
            "Example:\nInput: nums = [2, 1, 2, 3], target = 4\nOutput: valid result based on your approach\n\n"
            f"Function Signature:\ndef solve_{function_name}(nums: list[int], target: int) -> int:\n    pass\n\n"
            "Expected Time Complexity: O(n log n) or better depending on approach.\n\n"
            "Follow-up Variation: How would your solution change if the input arrives as a stream?\n"
            "Interviewer Edge Case Discussion: Explain behavior for empty arrays, all duplicates, and maximum n."
        )
        return {
            "topic": topic,
            "difficulty": difficulty,
            "question_type": "coding",
            "prompt": prompt,
            "options": [],
            "correct_answer": "Rubric: correct approach, complexity, edge cases, and clean implementation.",
            "explanation": "This adaptive DSA prompt targets weak topics first and evaluates algorithm design depth.",
        }

    if test_type == "aptitude":
        options = ["A. 18%", "B. 20%", "C. 22.5%", "D. 25%"]
        prompt = (
            f"{difficulty.title()} Aptitude - {topic}\n\n"
            "A product is sold for Rs. 960 after giving a 20% discount. If the shopkeeper still makes a "
            "20% profit, find the cost price of the product."
        )
        return {
            "topic": topic,
            "difficulty": difficulty,
            "question_type": "mcq",
            "prompt": prompt,
            "options": options,
            "correct_answer": "B",
            "explanation": "Marked price = 960 / 0.8 = 1200. Cost price = 960 / 1.2 = 800. Profit on CP is 20%.",
        }

    if test_type == "verbal":
        options = [
            "A. He do not knows the answer.",
            "B. He does not know the answer.",
            "C. He did not knew the answer.",
            "D. He don't know the answer.",
        ]
        return {
            "topic": topic,
            "difficulty": difficulty,
            "question_type": "mcq",
            "prompt": f"{difficulty.title()} Verbal Ability - {topic}\n\nChoose the grammatically correct sentence.",
            "options": options,
            "correct_answer": "B",
            "explanation": "With third-person singular subject 'He', use 'does not' followed by the base verb 'know'.",
        }

    if test_type == "logical":
        options = ["A. Q", "B. R", "C. S", "D. T"]
        return {
            "topic": topic,
            "difficulty": difficulty,
            "question_type": "mcq",
            "prompt": (
                f"{difficulty.title()} Logical Reasoning - {topic}\n\n"
                "In a code language, APPLE is written as BQQMF. How is ROSE written in the same code?"
            ),
            "options": options,
            "correct_answer": "B",
            "explanation": "Each character is shifted by +1: R->S, O->P, S->T, E->F, so ROSE becomes SPTF.",
        }

    prompt = (
        f"{difficulty.title()} Programming Concepts - {language} / {topic}\n\n"
        f"Consider this {language} interview scenario. Explain the concept, predict the output if relevant, "
        "identify one bug risk, and mention a production-grade best practice.\n\n"
        "Snippet:\n"
        "```text\n"
        "class Cache:\n"
        "    shared = {}\n"
        "    def put(self, key, value):\n"
        "        self.shared[key] = value\n"
        "```\n"
    )
    return {
        "topic": f"{language} - {topic}",
        "difficulty": difficulty,
        "question_type": "conceptual",
        "prompt": prompt,
        "options": [],
        "correct_answer": "Rubric: shared state, memory behavior, concurrency risk, and language-specific fix.",
        "explanation": "This checks language concepts plus debugging and production design awareness.",
    }


def re_safe_name(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_") or "problem"


def _shuffle_options(correct_value: str, distractors: list[str], seed: str) -> tuple[list[str], str]:
    rng = random.Random(int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16))
    values = [correct_value, *distractors]
    rng.shuffle(values)
    labels = ["A", "B", "C", "D"]
    options = [f"{label}. {value}" for label, value in zip(labels, values)]
    correct_label = labels[values.index(correct_value)]
    return options, correct_label


def _aptitude_template(topic: str, difficulty: str, index: int, seed: str) -> dict:
    rng = random.Random(int(hashlib.sha256(f"{seed}|{topic}|{difficulty}|{index}".encode("utf-8")).hexdigest(), 16))

    if topic == "Percentage":
        base = rng.choice([200, 240, 320, 400, 500])
        pct = rng.choice([12, 15, 18, 20, 25, 30])
        correct = base * pct // 100
        options, label = _shuffle_options(str(correct), [str(correct + 10), str(max(1, correct - 8)), str(correct + 20)], seed + topic)
        prompt = f"{pct}% of {base} is equal to:"
        explanation = f"{pct}% of {base} = ({pct}/100) * {base} = {correct}."
    elif topic == "Profit and Loss":
        cp = rng.choice([400, 500, 640, 800, 1200])
        profit_pct = rng.choice([10, 12, 15, 20, 25])
        sp = cp + (cp * profit_pct // 100)
        correct = sp
        options, label = _shuffle_options(str(correct), [str(sp - 20), str(sp + 40), str(cp)], seed + topic)
        prompt = f"A shopkeeper buys an article for Rs. {cp} and earns {profit_pct}% profit. What is the selling price?"
        explanation = f"Selling price = CP + {profit_pct}% of CP = {cp} + {cp * profit_pct // 100} = {sp}."
    elif topic == "Time and Work":
        a = rng.choice([10, 12, 15, 20])
        b = rng.choice([15, 20, 30])
        correct_float = (a * b) / (a + b)
        correct = f"{correct_float:.1f} days" if correct_float % 1 else f"{int(correct_float)} days"
        options, label = _shuffle_options(correct, [f"{a + b} days", f"{abs(a - b) or 5} days", f"{min(a, b)} days"], seed + topic)
        prompt = f"A can finish a work in {a} days and B in {b} days. Working together, how long will they take?"
        explanation = f"Combined rate = 1/{a} + 1/{b}. Time = ({a}*{b})/({a}+{b}) = {correct}."
    elif topic == "Time Speed Distance":
        speed = rng.choice([40, 45, 60, 72])
        time = rng.choice([2, 3, 4, 5])
        correct = speed * time
        options, label = _shuffle_options(f"{correct} km", [f"{correct + 20} km", f"{correct - 15} km", f"{speed + time} km"], seed + topic)
        prompt = f"A vehicle travels at {speed} km/h for {time} hours. What distance does it cover?"
        explanation = f"Distance = speed * time = {speed} * {time} = {correct} km."
    elif topic == "Ratio and Proportion":
        x = rng.choice([2, 3, 4, 5])
        y = rng.choice([3, 5, 7])
        total = (x + y) * rng.choice([20, 30, 40])
        correct = total * x // (x + y)
        options, label = _shuffle_options(str(correct), [str(total - correct), str(correct + 10), str(max(1, correct - 10))], seed + topic)
        prompt = f"A sum of {total} is divided in the ratio {x}:{y}. What is the first share?"
        explanation = f"First share = {x}/({x}+{y}) * {total} = {correct}."
    elif topic == "Probability":
        red = rng.choice([3, 4, 5])
        blue = rng.choice([5, 6, 7])
        total = red + blue
        correct = f"{red}/{total}"
        options, label = _shuffle_options(correct, [f"{blue}/{total}", f"{red}/{blue}", f"1/{total}"], seed + topic)
        prompt = f"A bag has {red} red and {blue} blue balls. One ball is drawn. What is the probability of red?"
        explanation = f"Probability = favorable outcomes / total outcomes = {red}/{total}."
    elif topic == "Permutation and Combination":
        n = rng.choice([5, 6, 7, 8])
        correct = n * (n - 1)
        options, label = _shuffle_options(str(correct), [str(n * n), str(n + n), str(correct // 2)], seed + topic)
        prompt = f"How many 2-letter arrangements can be formed from {n} distinct letters without repetition?"
        explanation = f"Arrangements = P({n},2) = {n} * {n - 1} = {correct}."
    elif topic == "Number System":
        num = rng.choice([84, 96, 108, 132, 180])
        correct = sum(1 for i in range(1, num + 1) if num % i == 0)
        options, label = _shuffle_options(str(correct), [str(correct + 2), str(max(1, correct - 2)), str(correct + 4)], seed + topic)
        prompt = f"How many positive factors does {num} have?"
        explanation = f"Prime factorize {num} and multiply (powers + 1) to get {correct} factors."
    elif topic == "Simple Interest & Compound Interest":
        principal = rng.choice([1000, 2000, 5000])
        rate = rng.choice([5, 8, 10, 12])
        years = rng.choice([2, 3])
        correct = principal * rate * years // 100
        options, label = _shuffle_options(f"Rs. {correct}", [f"Rs. {correct + 100}", f"Rs. {max(50, correct - 100)}", f"Rs. {principal + correct}"], seed + topic)
        prompt = f"Find the simple interest on Rs. {principal} at {rate}% per annum for {years} years."
        explanation = f"SI = (P*R*T)/100 = ({principal}*{rate}*{years})/100 = Rs. {correct}."
    else:
        monday = rng.choice([20, 30, 40])
        tuesday = rng.choice([25, 35, 45])
        correct = monday + tuesday
        options, label = _shuffle_options(str(correct), [str(correct + 10), str(max(1, correct - 10)), str(tuesday - monday)], seed + topic)
        prompt = f"Data Interpretation: A store sold {monday} units on Monday and {tuesday} units on Tuesday. What is the total sale?"
        explanation = f"Total sale = Monday + Tuesday = {monday} + {tuesday} = {correct}."

    if difficulty == "hard":
        prompt += " Choose the most accurate answer after checking units and assumptions."
    elif difficulty == "medium":
        prompt += " Solve without using a calculator."

    return {
        "topic": topic,
        "difficulty": difficulty,
        "question_type": "mcq",
        "prompt": prompt,
        "options": options,
        "correct_answer": label,
        "explanation": explanation,
    }


def _generate_aptitude_test_questions(user_id: str, recent_prompts: list[str]) -> list[dict]:
    seed = f"{user_id}|{len(recent_prompts)}|aptitude"
    topic_cycle = (APTITUDE_TOPICS * 2)[:20]
    questions = []
    for index, (topic, difficulty) in enumerate(zip(topic_cycle, APTITUDE_DIFFICULTIES), start=1):
        question = _aptitude_template(topic, difficulty, index, seed)
        if question["prompt"] in recent_prompts:
            question = _aptitude_template(topic, difficulty, index + 100, seed)
        questions.append(question)
    random.Random(int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)).shuffle(questions)
    return questions


def _evaluate_answer(question: dict, user_answer: str) -> dict:
    normalized = user_answer.strip().lower()
    correct_answer = str(question.get("correct_answer") or "").strip()
    if question["question_type"] == "mcq":
        is_correct = normalized[:1] == correct_answer.lower()[:1]
    else:
        rubric_terms = [
            "complexity", "edge", "algorithm", "approach", "tradeoff", "bug",
            "memory", "concurrency", "example", "constraint",
        ]
        matches = sum(1 for term in rubric_terms if term in normalized)
        is_correct = matches >= 3 or len(normalized.split()) >= 80

    xp = 25 if is_correct else 8
    return {
        "is_correct": is_correct,
        "xp": xp,
        "correct_answer": correct_answer,
        "explanation": question["explanation"],
        "feedback": (
            "Strong answer. You covered the expected reasoning path."
            if is_correct
            else "Good attempt. Improve by adding constraints, edge cases, complexity, and a clearer final answer."
        ),
    }


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

    # Auto-generate title from first message if conversation is still "Untitled"
    conv = load_conversation(thread_id)
    # Check if this is the first message (empty conversation)
    if not conv:  # Empty conversation
        generated_title = generate_chat_title(message)
        update_conversation_title(thread_id, generated_title)

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
    if not filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    file_bytes = await file.read()
    try:
        return ingest_pdf(file_bytes, thread_id, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF ingestion failed: {exc}") from exc


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


@app.get("/mock-tests/catalog")
async def mock_test_catalog():
    return [
        {"id": test_id, "title": meta["title"], "topics": meta["topics"]}
        for test_id, meta in MOCK_TEST_META.items()
    ]


@app.post("/mock-tests/start")
async def start_mock_test(payload: dict = None):
    payload = payload or {}
    test_type = str(payload.get("test_type") or "").lower()
    if test_type not in MOCK_TEST_META:
        raise HTTPException(status_code=400, detail="Unsupported mock test type")

    if test_type == "programming" and not payload.get("language"):
        raise HTTPException(status_code=400, detail="Programming language is required")

    user_id = _user_id_from_payload(payload)
    profile_context = _load_profile_context(user_id, payload) if test_type == "dsa" else {
        "leetcode": None,
        "gfg": None,
        "topics": [],
        "contests": [],
        "total_solved": 0,
    }
    recent_prompts = get_recent_mock_test_prompts(user_id, test_type)
    question = _generate_mock_question(test_type, payload, profile_context, recent_prompts)
    attempt_id = create_mock_test_attempt(
        user_id,
        test_type,
        {
            "profile_context": profile_context,
            "language": payload.get("language"),
            "recent_prompt_count": len(recent_prompts),
        },
    )
    if not attempt_id:
        raise HTTPException(status_code=500, detail="Could not create mock test attempt")

    question_id = save_mock_test_question(
        attempt_id=attempt_id,
        topic=question["topic"],
        difficulty=question["difficulty"],
        question_type=question["question_type"],
        prompt=question["prompt"],
        options=question["options"],
        correct_answer=question["correct_answer"],
        explanation=question["explanation"],
    )
    if not question_id:
        raise HTTPException(status_code=500, detail="Could not save generated question")

    return {
        "attempt_id": attempt_id,
        "question_id": question_id,
        "test_type": test_type,
        "title": MOCK_TEST_META[test_type]["title"],
        "timer_seconds": 2700 if test_type == "dsa" else 90,
        "question": {**question, "id": question_id},
        "profile_context": profile_context,
    }


@app.post("/mock-tests/submit")
async def submit_mock_test_answer(payload: dict = None):
    payload = payload or {}
    question_id = int(payload.get("question_id") or 0)
    user_answer = str(payload.get("answer") or "")
    time_spent_seconds = int(payload.get("time_spent_seconds") or 0)

    if not question_id or not user_answer.strip():
        raise HTTPException(status_code=400, detail="question_id and answer are required")

    question = get_mock_test_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    result = _evaluate_answer(question, user_answer)
    save_mock_test_answer(
        question_id,
        user_answer,
        bool(result["is_correct"]),
        time_spent_seconds,
        int(result["xp"]),
    )
    return result


@app.get("/mock-tests/analytics/{user_id}")
async def mock_test_analytics(user_id: str):
    return get_mock_test_analytics(user_id)


@app.get("/mock-tests/leaderboard")
async def mock_test_leaderboard(user_id: str = Query("default_user")):
    return get_mock_test_analytics(user_id).get("leaderboard", [])


@app.post("/aptitude-tests/generate")
async def generate_aptitude_test(payload: dict = None):
    payload = payload or {}
    user_id = _user_id_from_payload(payload)
    company = str(payload.get("company") or "general")
    recent_prompts = get_recent_mock_test_prompts(user_id, "aptitude", limit=80)
    questions = _generate_aptitude_test_questions(user_id, recent_prompts)

    attempt_id = create_mock_test_attempt(
        user_id,
        "aptitude",
        {
            "company": company,
            "question_count": 20,
            "difficulty_mix": {"easy": 6, "medium": 10, "hard": 4},
            "recent_prompt_count": len(recent_prompts),
        },
    )
    if not attempt_id:
        raise HTTPException(status_code=500, detail="Could not create aptitude test")

    public_questions = []
    for index, question in enumerate(questions, start=1):
        question_id = save_mock_test_question(
            attempt_id=attempt_id,
            topic=question["topic"],
            difficulty=question["difficulty"],
            question_type=question["question_type"],
            prompt=question["prompt"],
            options=question["options"],
            correct_answer=question["correct_answer"],
            explanation=question["explanation"],
        )
        public_questions.append({
            "id": question_id,
            "number": index,
            "topic": question["topic"],
            "difficulty": question["difficulty"],
            "question_type": question["question_type"],
            "prompt": question["prompt"],
            "options": question["options"],
        })

    return {
        "attempt_id": attempt_id,
        "title": "Aptitude Mock Test",
        "timer_seconds": 30 * 60,
        "questions": public_questions,
    }


@app.post("/aptitude-tests/submit")
async def submit_aptitude_test(payload: dict = None):
    payload = payload or {}
    attempt_id = int(payload.get("attempt_id") or 0)
    answers = payload.get("answers") or {}
    time_spent_seconds = int(payload.get("time_spent_seconds") or 0)
    if not attempt_id:
        raise HTTPException(status_code=400, detail="attempt_id is required")

    attempt = get_mock_test_attempt(attempt_id)
    if not attempt or attempt.get("test_type") != "aptitude":
        raise HTTPException(status_code=404, detail="Aptitude attempt not found")

    questions = get_mock_test_attempt_questions(attempt_id)
    results = []
    topic_stats: dict[str, dict] = {}
    difficulty_stats: dict[str, dict] = {}
    correct_count = 0
    per_question_time = max(1, time_spent_seconds // max(1, len(questions)))

    for question in questions:
        question_id = str(question["id"])
        answer = str(answers.get(question_id) or "").strip().upper()[:1]
        is_correct = answer == str(question["correct_answer"]).strip().upper()[:1]
        if is_correct:
            correct_count += 1

        save_mock_test_answer(
            int(question["id"]),
            answer,
            is_correct,
            per_question_time,
            10 if is_correct else 2,
        )

        topic = question["topic"]
        difficulty = question["difficulty"]
        topic_stats.setdefault(topic, {"topic": topic, "total": 0, "correct": 0})
        difficulty_stats.setdefault(difficulty, {"difficulty": difficulty, "total": 0, "correct": 0})
        topic_stats[topic]["total"] += 1
        difficulty_stats[difficulty]["total"] += 1
        if is_correct:
            topic_stats[topic]["correct"] += 1
            difficulty_stats[difficulty]["correct"] += 1

        results.append({
            "id": question["id"],
            "number": len(results) + 1,
            "topic": topic,
            "difficulty": difficulty,
            "prompt": question["prompt"],
            "options": question["options"],
            "user_answer": answer,
            "correct_answer": question["correct_answer"],
            "is_correct": is_correct,
            "explanation": question["explanation"],
        })

    complete_mock_test_attempt(attempt_id)
    total = len(questions)
    accuracy = round((correct_count / total) * 100, 1) if total else 0
    topic_performance = list(topic_stats.values())
    weak_areas = sorted(topic_performance, key=lambda item: item["correct"] / max(1, item["total"]))[:3]
    strong_areas = sorted(topic_performance, key=lambda item: item["correct"] / max(1, item["total"]), reverse=True)[:3]

    if accuracy >= 85:
        rank = "Top 10% estimate"
    elif accuracy >= 70:
        rank = "Top 25% estimate"
    elif accuracy >= 50:
        rank = "Developing - around average"
    else:
        rank = "Needs focused practice"

    suggestions = [
        f"Revise {area['topic']} with timed sets." for area in weak_areas
    ] or ["Keep practicing mixed aptitude sets."]
    if time_spent_seconds > 25 * 60:
        suggestions.append("Practice mental math shortcuts to improve speed.")
    if accuracy < 70:
        suggestions.append("Review explanations and retry one weak topic at a time.")

    return {
        "attempt_id": attempt_id,
        "score": correct_count,
        "total": total,
        "correct": correct_count,
        "wrong": total - correct_count,
        "accuracy": accuracy,
        "time_taken_seconds": time_spent_seconds,
        "topic_performance": topic_performance,
        "difficulty_analysis": list(difficulty_stats.values()),
        "weak_areas": weak_areas,
        "strong_areas": strong_areas,
        "suggestions": suggestions,
        "rank_estimation": rank,
        "results": results,
    }


@app.get("/aptitude-tests/attempts/{user_id}")
async def aptitude_attempts(user_id: str):
    return get_previous_mock_test_attempts(user_id, "aptitude")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
