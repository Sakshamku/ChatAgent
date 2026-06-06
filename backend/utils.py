"""
Utility functions for the chatbot application.
Includes title generation, text processing, and helper functions.
"""

import re
import uuid
from typing import Optional, List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from langchain_mistralai import ChatMistralAI
import os

def generate_thread_id() -> str:
    """Generate a unique thread ID"""
    return str(uuid.uuid4())

def generate_chat_title(first_message: str, max_length: int = 40) -> str:
    """
    Generate a chat title from the first user message.
    
    Args:
        first_message: The first user message
        max_length: Maximum length of the title
        
    Returns:
        A human-readable title for the conversation
    """
    # Clean the message: remove special chars, extra whitespace
    cleaned = re.sub(r'[^\w\s]', '', first_message)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # If message is short enough, use it directly
    if len(cleaned) <= max_length:
        return cleaned.capitalize() if cleaned else "New Chat"
    
    # For longer messages, try to extract meaningful phrases
    sentences = re.split(r'[.!?]', cleaned)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Try first sentence
    if sentences and len(sentences[0]) <= max_length:
        return sentences[0].capitalize()
    
    # If still too long, truncate with smart breaking
    words = cleaned.split()
    title_words = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_length:
            title_words.append(word)
            current_length += len(word) + 1
        else:
            break
    
    title = ' '.join(title_words)
    return title.capitalize() if title else "New Chat"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length with suffix"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def format_message_content(content: str, max_preview_length: int = 50) -> str:
    """
    Format message content for display in sidebar/preview.
    
    Args:
        content: The message content
        max_preview_length: Maximum length for preview
        
    Returns:
        Formatted content suitable for display
    """
    # Remove excessive whitespace
    content = re.sub(r'\s+', ' ', content).strip()
    
    # Handle code blocks, URLs, etc. for preview
    if content.startswith('```'):
        content = "Code: " + content.split('\n')[0].replace('```', '').strip()
    elif 'http' in content:
        content = "Link: " + content.split()[0] if content.split() else content
    
    return truncate_text(content, max_preview_length)

def get_message_role(message) -> str:
    """Get the role of a message (user/assistant/system)"""
    if isinstance(message, HumanMessage):
        return "user"
    elif isinstance(message, AIMessage):
        return "assistant"
    else:
        return "system"

def convert_langchain_messages_to_dict(messages: List) -> List[Dict[str, Any]]:
    """
    Convert LangChain messages to dictionary format for storage.
    
    Args:
        messages: List of LangChain message objects
        
    Returns:
        List of message dictionaries
    """
    converted = []
    for msg in messages:
        # Skip system messages for storage (they're regenerated)
        if get_message_role(msg) == "system":
            continue
            
        converted.append({
            "role": get_message_role(msg),
            "content": msg.content,
            "timestamp": None  # Will be set by database
        })
    return converted

def convert_dict_to_langchain_messages(messages: List[Dict[str, Any]]) -> List:
    """
    Convert dictionary messages back to LangChain format.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        List of LangChain message objects
    """
    converted = []
    for msg in messages:
        if msg["role"] == "user":
            converted.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            converted.append(AIMessage(content=msg["content"]))
    return converted

def validate_thread_id(thread_id: str) -> bool:
    """Validate thread ID format"""
    if not thread_id or not isinstance(thread_id, str):
        return False
    # Basic UUID format validation
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, thread_id.lower()))

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove path separators and dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    # Limit length
    return sanitized[:255]

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if not size_bytes:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def get_time_ago(timestamp: str) -> str:
    """
    Convert timestamp to "time ago" format.
    
    Args:
        timestamp: ISO format timestamp string
        
    Returns:
        Human readable time ago string
    """
    from datetime import datetime, timezone
    import math
    
    try:
        # Parse timestamp (SQLite returns naive UTC strings)
        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = timestamp
            if getattr(dt, "tzinfo", None) is None:
                dt = dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        diff = now - dt
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = math.floor(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = math.floor(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 604800:
            days = math.floor(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            weeks = math.floor(seconds / 604800)
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
            
    except Exception:
        return "unknown time"

def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """
    Extract keywords from text for search functionality.
    
    Args:
        text: Input text
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of keywords
    """
    # Simple keyword extraction - remove common words and get unique terms
    stop_words = {
        'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but',
        'in', 'with', 'for', 'of', 'to', 'from', 'by', 'about', 'as',
        'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
        'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
        'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their'
    }
    
    # Clean and split text
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Filter out stop words and short words
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Get unique keywords and limit count
    unique_keywords = list(dict.fromkeys(keywords))  # Preserve order while removing duplicates
    return unique_keywords[:max_keywords]

def is_valid_api_key() -> bool:
    """Check if Mistral API key is configured"""
    api_key = os.getenv("MISTRAL_API_KEY")
    return api_key is not None and len(api_key.strip()) > 0

def create_error_response(error_message: str) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "error": True,
        "message": error_message,
        "timestamp": None
    }

def create_success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Create standardized success response"""
    return {
        "error": False,
        "message": message,
        "data": data,
        "timestamp": None
    }

def merge_conversation_data(conversation: Dict, messages: List[Dict], document: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Merge conversation, messages, and document data into single structure.
    
    Args:
        conversation: Conversation metadata
        messages: List of messages
        document: Optional document metadata
        
    Returns:
        Merged conversation data
    """
    merged = conversation.copy()
    merged["messages"] = messages
    if document:
        merged["document"] = document
    return merged
