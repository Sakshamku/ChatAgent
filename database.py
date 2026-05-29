"""
Database layer for persistent chat history system.
Handles SQLite operations for conversations, messages, and documents.
"""

import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
import json

# Thread-safe database connection
_local = threading.local()

def get_db_connection():
    """Get thread-local database connection"""
    if not hasattr(_local, 'connection'):
        _local.connection = sqlite3.connect('chat_history.db', check_same_thread=False)
        _local.connection.row_factory = sqlite3.Row  # Enable dict-like access
    return _local.connection

@contextmanager
def get_db_cursor():
    """Context manager for database operations"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise

def initialize_database():
    """Initialize database with proper schema and indexes"""
    with get_db_cursor() as cursor:
        # Create conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES conversations(thread_id) ON DELETE CASCADE
            )
        """)
        
        # Create documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                chunks INTEGER NOT NULL,
                pages INTEGER NOT NULL,
                file_size INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES conversations(thread_id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_thread_id ON documents(thread_id)")
        
        # Create trigger to auto-update updated_at
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_conversation_timestamp 
            AFTER INSERT ON messages
            BEGIN
                UPDATE conversations SET updated_at = CURRENT_TIMESTAMP 
                WHERE thread_id = NEW.thread_id;
            END
        """)
        
        # =========================================================
        # Coding Profile Analytics Tables
        # =========================================================
        
        # Connected coding profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coding_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL CHECK (platform IN ('leetcode', 'gfg')),
                username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, platform)
            )
        """)
        
        # Coding stats snapshot
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coding_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                total_solved INTEGER DEFAULT 0,
                easy_count INTEGER DEFAULT 0,
                medium_count INTEGER DEFAULT 0,
                hard_count INTEGER DEFAULT 0,
                contest_rating REAL DEFAULT 0,
                ranking INTEGER DEFAULT 0,
                coding_score INTEGER DEFAULT 0,
                monthly_score INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Topic-wise stats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                topic_name TEXT NOT NULL,
                solved_count INTEGER DEFAULT 0,
                UNIQUE(user_id, platform, topic_name)
            )
        """)
        
        # Contest history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contest_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                contest_name TEXT NOT NULL,
                rating REAL DEFAULT 0,
                ranking INTEGER DEFAULT 0,
                contest_date TEXT,
                top_percentage REAL DEFAULT 0
            )
        """)
        
        # Indexes for coding tables
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_coding_profiles_user ON coding_profiles(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_coding_stats_user ON coding_stats(user_id, platform)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topic_stats_user ON topic_stats(user_id, platform)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contest_history_user ON contest_history(user_id, platform)")

        # Mock interview state and scoring history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_interviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                target_role TEXT NOT NULL,
                focus TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                question TEXT NOT NULL,
                expected_points TEXT,
                answer TEXT,
                score INTEGER,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                answered_at TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES conversations(thread_id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mock_interviews_thread ON mock_interviews(thread_id, created_at)")

        # Adaptive mock test arena attempts and generated questions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_test_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                test_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                source_context TEXT,
                total_questions INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_test_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                question_type TEXT NOT NULL,
                prompt TEXT NOT NULL,
                options TEXT,
                correct_answer TEXT,
                explanation TEXT,
                user_answer TEXT,
                is_correct INTEGER,
                time_spent_seconds INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                answered_at TIMESTAMP,
                FOREIGN KEY (attempt_id) REFERENCES mock_test_attempts(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mock_test_attempts_user ON mock_test_attempts(user_id, test_type, started_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mock_test_questions_attempt ON mock_test_questions(attempt_id)")

def create_conversation(thread_id: str, title: str) -> bool:
    """Create a new conversation"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO conversations (thread_id, title) VALUES (?, ?)",
                (thread_id, title)
            )
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error creating conversation: {e}")
        return False

def save_message(thread_id: str, role: str, content: str) -> bool:
    """Save a message to the database"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "INSERT INTO messages (thread_id, role, content) VALUES (?, ?, ?)",
                (thread_id, role, content)
            )
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error saving message: {e}")
        return False

def load_conversation(thread_id: str) -> List[Dict[str, Any]]:
    """Load all messages for a conversation"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT role, content, timestamp FROM messages WHERE thread_id = ? ORDER BY timestamp ASC",
                (thread_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error loading conversation: {e}")
        return []

def get_all_conversations() -> List[Dict[str, Any]]:
    """Get all conversations ordered by most recent"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT thread_id, title, created_at, updated_at,
                       (SELECT COUNT(*) FROM messages WHERE thread_id = conversations.thread_id) as message_count
                FROM conversations 
                ORDER BY updated_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting conversations: {e}")
        return []

def search_conversations(query: str) -> List[Dict[str, Any]]:
    """Search conversations by title or content"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT c.thread_id, c.title, c.created_at, c.updated_at,
                       (SELECT COUNT(*) FROM messages WHERE thread_id = c.thread_id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.thread_id = m.thread_id
                WHERE c.title LIKE ? OR m.content LIKE ?
                ORDER BY c.updated_at DESC
            """, (f"%{query}%", f"%{query}%"))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error searching conversations: {e}")
        return []

def delete_conversation(thread_id: str) -> bool:
    """Delete a conversation and all related data"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM conversations WHERE thread_id = ?", (thread_id,))
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return False

def save_document_metadata(thread_id: str, filename: str, chunks: int, pages: int, file_size: int = None) -> bool:
    """Save document metadata"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT id FROM documents WHERE thread_id = ?",
                (thread_id,),
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                    UPDATE documents
                    SET filename = ?, chunks = ?, pages = ?, file_size = ?,
                        uploaded_at = CURRENT_TIMESTAMP
                    WHERE thread_id = ?
                """, (filename, chunks, pages, file_size, thread_id))
            else:
                cursor.execute("""
                    INSERT INTO documents (thread_id, filename, chunks, pages, file_size)
                    VALUES (?, ?, ?, ?, ?)
                """, (thread_id, filename, chunks, pages, file_size))
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error saving document metadata: {e}")
        return False

def get_document_metadata(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get document metadata for a thread"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT filename, chunks, pages, file_size, uploaded_at FROM documents WHERE thread_id = ?",
                (thread_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error getting document metadata: {e}")
        return None

def update_conversation_title(thread_id: str, title: str) -> bool:
    """Update conversation title"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE thread_id = ?",
                (title, thread_id)
            )
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating conversation title: {e}")
        return False

def get_conversation_title(thread_id: str) -> Optional[str]:
    """Get conversation title"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT title FROM conversations WHERE thread_id = ?", (thread_id,))
            row = cursor.fetchone()
            return row['title'] if row else None
    except Exception as e:
        print(f"Error getting conversation title: {e}")
        return None

def get_message_count(thread_id: str) -> int:
    """Get message count for a conversation"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM messages WHERE thread_id = ?", (thread_id,))
            row = cursor.fetchone()
            return row['count'] if row else 0
    except Exception as e:
        print(f"Error getting message count: {e}")
        return 0

def get_last_message(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the last message in a conversation"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT role, content, timestamp FROM messages WHERE thread_id = ? ORDER BY timestamp DESC LIMIT 1",
                (thread_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error getting last message: {e}")
        return None

def cleanup_old_conversations(days: int = 30) -> int:
    """Delete conversations older than specified days"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM conversations WHERE updated_at < datetime('now', '-{} days')".format(days)
            )
            return cursor.rowcount
    except Exception as e:
        print(f"Error cleaning up old conversations: {e}")
        return 0

# =========================================================
# Coding Profile CRUD Functions
# =========================================================

def save_coding_profile(user_id: str, platform: str, username: str) -> bool:
    """Save or update a connected coding profile."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO coding_profiles (user_id, platform, username)
                VALUES (?, ?, ?)
            """, (user_id, platform, username))
            return True
    except Exception as e:
        print(f"Error saving coding profile: {e}")
        return False


def get_coding_profiles(user_id: str) -> List[Dict[str, Any]]:
    """Get all connected coding profiles for a user."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM coding_profiles WHERE user_id = ?",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting coding profiles: {e}")
        return []


def delete_coding_profile(user_id: str, platform: str) -> bool:
    """Delete a connected coding profile."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM coding_profiles WHERE user_id = ? AND platform = ?",
                (user_id, platform)
            )
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting coding profile: {e}")
        return False


def save_coding_stats(user_id: str, platform: str, stats: Dict[str, Any]) -> bool:
    """Save coding stats snapshot."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO coding_stats (user_id, platform, total_solved, easy_count, 
                    medium_count, hard_count, contest_rating, ranking, coding_score, 
                    monthly_score, streak)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, platform,
                stats.get("total_solved", 0),
                stats.get("easy_count", 0),
                stats.get("medium_count", 0),
                stats.get("hard_count", 0),
                stats.get("contest_rating", stats.get("rating", 0)),
                stats.get("ranking", 0),
                stats.get("coding_score", 0),
                stats.get("monthly_score", 0),
                stats.get("streak", 0),
            ))
            return True
    except Exception as e:
        print(f"Error saving coding stats: {e}")
        return False


def get_latest_coding_stats(user_id: str, platform: str) -> Optional[Dict[str, Any]]:
    """Get the latest coding stats for a user/platform."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM coding_stats 
                WHERE user_id = ? AND platform = ?
                ORDER BY updated_at DESC LIMIT 1
            """, (user_id, platform))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error getting coding stats: {e}")
        return None


def save_topic_stats(user_id: str, platform: str, topics: List[Dict[str, Any]]) -> bool:
    """Save topic-wise stats (upsert)."""
    try:
        with get_db_cursor() as cursor:
            for topic in topics:
                cursor.execute("""
                    INSERT OR REPLACE INTO topic_stats (user_id, platform, topic_name, solved_count)
                    VALUES (?, ?, ?, ?)
                """, (user_id, platform, topic.get("topic_name", ""), topic.get("solved_count", 0)))
            return True
    except Exception as e:
        print(f"Error saving topic stats: {e}")
        return False


def get_topic_stats(user_id: str, platform: str) -> List[Dict[str, Any]]:
    """Get topic-wise stats for a user/platform."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT topic_name, solved_count FROM topic_stats WHERE user_id = ? AND platform = ?",
                (user_id, platform)
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting topic stats: {e}")
        return []


def save_contest_history(user_id: str, platform: str, contests: List[Dict[str, Any]]) -> bool:
    """Save contest history entries."""
    try:
        with get_db_cursor() as cursor:
            # Clear old history first
            cursor.execute(
                "DELETE FROM contest_history WHERE user_id = ? AND platform = ?",
                (user_id, platform)
            )
            for contest in contests:
                if contest.get("contest_name") == "__current_stats__":
                    continue
                cursor.execute("""
                    INSERT INTO contest_history (user_id, platform, contest_name, rating, 
                        ranking, contest_date, top_percentage)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, platform,
                    contest.get("contest_name", ""),
                    contest.get("rating", 0),
                    contest.get("ranking", 0),
                    contest.get("contest_date", ""),
                    contest.get("top_percentage", 0),
                ))
            return True
    except Exception as e:
        print(f"Error saving contest history: {e}")
        return False


def get_contest_history(user_id: str, platform: str) -> List[Dict[str, Any]]:
    """Get contest history for a user/platform."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM contest_history WHERE user_id = ? AND platform = ? ORDER BY contest_date DESC",
                (user_id, platform)
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting contest history: {e}")
        return []


# =========================================================
# Mock Interview Functions
# =========================================================

def save_mock_interview_question(
    thread_id: str,
    target_role: str,
    focus: str,
    difficulty: str,
    question: str,
    expected_points: List[str],
) -> int:
    """Persist a generated mock interview question."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO mock_interviews
                    (thread_id, target_role, focus, difficulty, question, expected_points)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                thread_id,
                target_role,
                focus,
                difficulty,
                question,
                json.dumps(expected_points),
            ))
            return int(cursor.lastrowid)
    except Exception as e:
        print(f"Error saving mock interview question: {e}")
        return 0


def get_latest_mock_interview(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the latest unanswered mock interview question for a thread."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM mock_interviews
                WHERE thread_id = ? AND answer IS NULL
                ORDER BY created_at DESC
                LIMIT 1
            """, (thread_id,))
            row = cursor.fetchone()
            if not row:
                return None
            result = dict(row)
            result["expected_points"] = json.loads(result.get("expected_points") or "[]")
            return result
    except Exception as e:
        print(f"Error getting mock interview: {e}")
        return None


def save_mock_interview_answer(
    interview_id: int,
    answer: str,
    score: int,
    feedback: Dict[str, Any],
) -> bool:
    """Persist a mock interview answer and evaluation."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE mock_interviews
                SET answer = ?, score = ?, feedback = ?, answered_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (answer, score, json.dumps(feedback), interview_id))
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error saving mock interview answer: {e}")
        return False


# =========================================================
# Mock Test Arena Functions
# =========================================================

def create_mock_test_attempt(
    user_id: str,
    test_type: str,
    source_context: Dict[str, Any],
) -> int:
    """Create a new mock test attempt."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO mock_test_attempts (user_id, test_type, source_context)
                VALUES (?, ?, ?)
            """, (user_id, test_type, json.dumps(source_context)))
            return int(cursor.lastrowid)
    except Exception as e:
        print(f"Error creating mock test attempt: {e}")
        return 0


def save_mock_test_question(
    attempt_id: int,
    topic: str,
    difficulty: str,
    question_type: str,
    prompt: str,
    options: Optional[List[str]],
    correct_answer: str,
    explanation: str,
) -> int:
    """Persist one generated mock test question."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO mock_test_questions
                    (attempt_id, topic, difficulty, question_type, prompt, options, correct_answer, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attempt_id,
                topic,
                difficulty,
                question_type,
                prompt,
                json.dumps(options or []),
                correct_answer,
                explanation,
            ))
            cursor.execute(
                "UPDATE mock_test_attempts SET total_questions = total_questions + 1 WHERE id = ?",
                (attempt_id,),
            )
            return int(cursor.lastrowid)
    except Exception as e:
        print(f"Error saving mock test question: {e}")
        return 0


def get_recent_mock_test_prompts(user_id: str, test_type: str, limit: int = 20) -> List[str]:
    """Return recently asked prompts so generation can avoid repeats."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT q.prompt
                FROM mock_test_questions q
                JOIN mock_test_attempts a ON a.id = q.attempt_id
                WHERE a.user_id = ? AND a.test_type = ?
                ORDER BY q.created_at DESC
                LIMIT ?
            """, (user_id, test_type, limit))
            return [row["prompt"] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting recent mock prompts: {e}")
        return []


def get_mock_test_question(question_id: int) -> Optional[Dict[str, Any]]:
    """Get one mock test question."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT q.*, a.user_id, a.test_type
                FROM mock_test_questions q
                JOIN mock_test_attempts a ON a.id = q.attempt_id
                WHERE q.id = ?
            """, (question_id,))
            row = cursor.fetchone()
            if not row:
                return None
            result = dict(row)
            result["options"] = json.loads(result.get("options") or "[]")
            return result
    except Exception as e:
        print(f"Error getting mock question: {e}")
        return None


def save_mock_test_answer(
    question_id: int,
    user_answer: str,
    is_correct: bool,
    time_spent_seconds: int,
    xp: int,
) -> bool:
    """Persist answer evaluation and update aggregate attempt stats."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE mock_test_questions
                SET user_answer = ?, is_correct = ?, time_spent_seconds = ?,
                    answered_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_answer, 1 if is_correct else 0, time_spent_seconds, question_id))
            cursor.execute("SELECT attempt_id FROM mock_test_questions WHERE id = ?", (question_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    UPDATE mock_test_attempts
                    SET correct_count = correct_count + ?,
                        xp = xp + ?
                    WHERE id = ?
                """, (1 if is_correct else 0, xp, row["attempt_id"]))
            return True
    except Exception as e:
        print(f"Error saving mock test answer: {e}")
        return False


def complete_mock_test_attempt(attempt_id: int) -> bool:
    """Mark a mock test attempt as completed."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE mock_test_attempts
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (attempt_id,))
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error completing mock test attempt: {e}")
        return False


def get_mock_test_attempt_questions(attempt_id: int) -> List[Dict[str, Any]]:
    """Get all questions for an attempt."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM mock_test_questions
                WHERE attempt_id = ?
                ORDER BY id ASC
            """, (attempt_id,))
            questions = []
            for row in cursor.fetchall():
                item = dict(row)
                item["options"] = json.loads(item.get("options") or "[]")
                questions.append(item)
            return questions
    except Exception as e:
        print(f"Error getting attempt questions: {e}")
        return []


def get_mock_test_attempt(attempt_id: int) -> Optional[Dict[str, Any]]:
    """Get one mock test attempt."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM mock_test_attempts WHERE id = ?", (attempt_id,))
            row = cursor.fetchone()
            if not row:
                return None
            result = dict(row)
            result["source_context"] = json.loads(result.get("source_context") or "{}")
            return result
    except Exception as e:
        print(f"Error getting mock test attempt: {e}")
        return None


def get_previous_mock_test_attempts(user_id: str, test_type: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Return previous attempts for history/resume surfaces."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT id, test_type, status, total_questions, correct_count, xp,
                    started_at, completed_at
                FROM mock_test_attempts
                WHERE user_id = ? AND test_type = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (user_id, test_type, limit))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting previous attempts: {e}")
        return []


def get_mock_test_analytics(user_id: str) -> Dict[str, Any]:
    """Aggregate mock arena performance analytics."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) AS answered,
                    COALESCE(SUM(is_correct), 0) AS correct,
                    COALESCE(AVG(time_spent_seconds), 0) AS avg_time
                FROM mock_test_questions q
                JOIN mock_test_attempts a ON a.id = q.attempt_id
                WHERE a.user_id = ? AND q.user_answer IS NOT NULL
            """, (user_id,))
            summary = dict(cursor.fetchone())

            cursor.execute("""
                SELECT q.topic,
                    COUNT(*) AS answered,
                    COALESCE(SUM(q.is_correct), 0) AS correct
                FROM mock_test_questions q
                JOIN mock_test_attempts a ON a.id = q.attempt_id
                WHERE a.user_id = ? AND q.user_answer IS NOT NULL
                GROUP BY q.topic
            """, (user_id,))
            topics = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT DATE(started_at) AS day, COALESCE(SUM(xp), 0) AS xp
                FROM mock_test_attempts
                WHERE user_id = ?
                GROUP BY DATE(started_at)
                ORDER BY day ASC
                LIMIT 14
            """, (user_id,))
            progress = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT user_id, COALESCE(SUM(xp), 0) AS xp,
                    COALESCE(SUM(correct_count), 0) AS correct
                FROM mock_test_attempts
                GROUP BY user_id
                ORDER BY xp DESC, correct DESC
                LIMIT 10
            """)
            leaderboard = [dict(row) for row in cursor.fetchall()]

        answered = int(summary.get("answered") or 0)
        correct = int(summary.get("correct") or 0)
        accuracy = round((correct / answered) * 100, 1) if answered else 0
        strong_topics = sorted(topics, key=lambda t: (t["correct"] / max(1, t["answered"])), reverse=True)[:3]
        weak_topics = sorted(topics, key=lambda t: (t["correct"] / max(1, t["answered"])))[:3]

        return {
            "answered": answered,
            "correct": correct,
            "accuracy": accuracy,
            "avg_time": round(float(summary.get("avg_time") or 0), 1),
            "strong_topics": strong_topics,
            "weak_topics": weak_topics,
            "progress": progress,
            "leaderboard": leaderboard,
            "streak": len(progress),
            "xp": sum(int(row["xp"] or 0) for row in progress),
        }
    except Exception as e:
        print(f"Error getting mock analytics: {e}")
        return {
            "answered": 0,
            "correct": 0,
            "accuracy": 0,
            "avg_time": 0,
            "strong_topics": [],
            "weak_topics": [],
            "progress": [],
            "leaderboard": [],
            "streak": 0,
            "xp": 0,
        }


# Initialize database on import
initialize_database()
