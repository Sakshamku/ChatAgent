"""
Streamlit Frontend with ChatGPT-like Real-Time Streaming UI.
Features smooth token-by-token streaming, auto-scroll, typing animations, and tool calling UI.
"""

import os
import uuid
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from Backend import (
    chatbot,
    ingest_pdf,
    get_all_conversations_with_metadata,
    delete_thread,
    search_conversations,
    thread_document_metadata,
    get_conversation_messages,
)
from database import get_all_conversations, delete_conversation, get_coding_profiles, get_latest_coding_stats
from code_interpreter import (
    save_uploaded_file, list_workspace_files,
    get_workspace_file_path, execute_python, format_execution_result
)
from utils import (
    generate_thread_id, format_message_content, get_time_ago,
    format_file_size, create_error_response, create_success_response
)
import base64
import json

# =========================================================
# Enhanced CSS for ChatGPT-like Streaming Experience
# =========================================================

st.markdown("""
<style>
    /* Auto-scroll container */
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
        scroll-behavior: smooth;
    }
    
    /* Streaming message container */
    .streaming-message {
        animation: fadeIn 0.3s ease-in;
        margin-bottom: 20px;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Typing cursor animation */
    .typing-cursor {
        display: inline-block;
        width: 8px;
        height: 20px;
        background-color: #4caf50;
        margin-left: 2px;
        animation: blink 1s infinite;
        vertical-align: text-bottom;
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
    
    /* Typing dots animation */
    .typing-dots {
        display: inline-flex;
        gap: 4px;
        padding: 8px 12px;
        background-color: #f5f5f5;
        border-radius: 16px;
        border-bottom-left-radius: 4px;
    }
    
    .typing-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #999;
        animation: typing 1.4s infinite ease-in-out;
    }
    
    .typing-dot:nth-child(1) { animation-delay: -0.32s; }
    .typing-dot:nth-child(2) { animation-delay: -0.16s; }
    .typing-dot:nth-child(3) { animation-delay: 0s; }
    
    @keyframes typing {
        0%, 80%, 100% { 
            transform: scale(0.8); 
            opacity: 0.5; 
        }
        40% { 
            transform: scale(1); 
            opacity: 1; 
        }
    }
    
    /* Tool status indicator */
    .tool-status {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        background-color: #e3f2fd;
        border: 1px solid #2196f3;
        border-radius: 8px;
        margin: 8px 0;
        font-size: 0.9em;
        color: #1976d2;
        animation: slideIn 0.3s ease-out;
    }
    
    @keyframes slideIn {
        from { 
            opacity: 0; 
            transform: translateX(-20px); 
        }
        to { 
            opacity: 1; 
            transform: translateX(0); 
        }
    }
    
    .tool-icon {
        animation: spin 2s linear infinite;
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    /* Message styling */
    .chat-message {
        margin-bottom: 20px;
        display: flex;
        gap: 12px;
        animation: messageSlide 0.3s ease-out;
    }
    
    @keyframes messageSlide {
        from { 
            opacity: 0; 
            transform: translateY(20px); 
        }
        to { 
            opacity: 1; 
            transform: translateY(0); 
        }
    }
    
    .chat-message.user {
        flex-direction: row-reverse;
    }
    
    .message-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        font-weight: 600;
        flex-shrink: 0;
    }
    
    .message-avatar.user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .message-avatar.assistant {
        background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
        color: white;
    }
    
    .message-content {
        max-width: 70%;
        padding: 12px 16px;
        border-radius: 16px;
        line-height: 1.6;
        word-wrap: break-word;
    }
    
    .message-content.user {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-bottom-right-radius: 4px;
    }
    
    .message-content.assistant {
        background: linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%);
        border-bottom-left-radius: 4px;
    }
    
    /* Streaming text */
    .streaming-text {
        position: relative;
    }
    
    .streaming-text::after {
        content: '';
        display: inline-block;
        width: 2px;
        height: 1.2em;
        background-color: #4caf50;
        margin-left: 2px;
        animation: cursorBlink 1s infinite;
    }
    
    @keyframes cursorBlink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
    
    /* Smooth transitions */
    .smooth-transition {
        transition: all 0.3s ease;
    }
    
    /* Sidebar improvements */
    .conversation-item {
        padding: 12px;
        margin: 4px 0;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        border: 1px solid transparent;
    }
    
    .conversation-item:hover {
        background-color: #f8f9fa;
        border-color: #e9ecef;
        transform: translateX(2px);
    }
    
    .conversation-item.active {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-color: #2196f3;
    }
    
    /* Input area styling */
    .input-container {
        position: sticky;
        bottom: 0;
        background: white;
        padding: 20px;
        border-top: 1px solid #e9ecef;
        backdrop-filter: blur(10px);
    }
    
    .chat-input {
        border-radius: 24px;
        border: 2px solid #e9ecef;
        transition: all 0.2s ease;
    }
    
    .chat-input:focus {
        border-color: #2196f3;
        box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
    }
    
    /* Loading overlay */
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255, 255, 255, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    }
    
    /* Code block styling */
    .code-block {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        font-family: 'Courier New', monospace;
        overflow-x: auto;
    }
    
    /* Markdown content */
    .markdown-content {
        line-height: 1.6;
    }
    
    .markdown-content h1, .markdown-content h2, .markdown-content h3 {
        margin-top: 16px;
        margin-bottom: 8px;
    }
    
    .markdown-content ul, .markdown-content ol {
        margin: 8px 0;
        padding-left: 20px;
    }
    
    .markdown-content strong {
        font-weight: 600;
    }
    
    .markdown-content em {
        font-style: italic;
    }
    
    .markdown-content code {
        background-color: #f8f9fa;
        padding: 2px 4px;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
    }
    
    /* Code interpreter styling */
    .code-exec-box {
        background: #1e1e2e;
        color: #cdd6f4;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        overflow-x: auto;
        white-space: pre-wrap;
        border: 1px solid #45475a;
    }
    
    .code-output-box {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        overflow-x: auto;
        white-space: pre-wrap;
    }
    
    .exec-status {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 0.85em;
        margin: 4px 0;
    }
    
    .exec-status.running {
        background: #fff3cd;
        color: #856404;
        border: 1px solid #ffc107;
    }
    
    .exec-status.success {
        background: #d4edda;
        color: #155724;
        border: 1px solid #28a745;
    }
    
    .exec-status.error {
        background: #f8d7da;
        color: #721c24;
        border: 1px solid #dc3545;
    }
    
    .file-download-btn {
        display: inline-block;
        padding: 6px 14px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border-radius: 6px;
        text-decoration: none;
        font-size: 0.85em;
        margin: 4px;
    }
    
    /* Stop button */
    .stButton > button[kind="primary"] {
        background: #dc3545 !important;
        color: white !important;
        border: none !important;
        border-radius: 20px !important;
        padding: 8px 24px !important;
        font-weight: 600 !important;
        max-width: 200px;
        margin: 0 auto;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        animation: pulseStop 2s infinite;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: #c82333 !important;
    }
    
    @keyframes pulseStop {
        0%, 100% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.4); }
        50% { box-shadow: 0 0 0 8px rgba(220, 53, 69, 0); }
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# JavaScript for Auto-scroll and Smooth UX
# =========================================================

def inject_auto_scroll_script():
    """Inject JavaScript for smooth auto-scrolling during streaming"""
    js_code = """
    <script>
    // Auto-scroll functionality
    function scrollToBottom(smooth = true) {
        const chatContainer = document.querySelector('.main .block-container');
        if (chatContainer) {
            if (smooth) {
                chatContainer.scrollTo({
                    top: chatContainer.scrollHeight,
                    behavior: 'smooth'
                });
            } else {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }
    }
    
    // Enhanced scroll with throttling
    let scrollTimeout;
    function throttledScrollToBottom() {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            scrollToBottom(true);
        }, 100);
    }
    
    // Auto-scroll on new content
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                throttledScrollToBottom();
            }
        });
    });
    
    // Start observing when page loads
    document.addEventListener('DOMContentLoaded', () => {
        const chatContainer = document.querySelector('.main .block-container');
        if (chatContainer) {
            observer.observe(chatContainer, {
                childList: true,
                subtree: true
            });
        }
    });
    
    // Manual scroll trigger for streaming
    window.triggerAutoScroll = function() {
        scrollToBottom(true);
    };
    
    // Prevent manual scroll during streaming
    let isStreaming = false;
    let userScrolled = false;
    
    document.addEventListener('wheel', (e) => {
        if (!isStreaming) return;
        
        const chatContainer = document.querySelector('.main .block-container');
        if (chatContainer) {
            const isAtBottom = chatContainer.scrollHeight - chatContainer.scrollTop <= chatContainer.clientHeight + 100;
            if (!isAtBottom) {
                userScrolled = true;
            }
        }
    });
    
    // Export functions for Streamlit
    window.setStreamingState = function(streaming) {
        isStreaming = streaming;
        if (!streaming) userScrolled = false;
    };
    
    window.isUserScrolled = function() {
        return userScrolled;
    };
    </script>
    """
    st.components.v1.html(js_code, height=0)

# =========================================================
# Session State Management with Streaming Support
# =========================================================

def init_session_state():
    """Initialize session state with streaming-specific defaults"""
    defaults = {
        "thread_id": generate_thread_id(),
        "message_history": [],
        "conversations": [],
        "current_conversation": None,
        "search_query": "",
        "is_streaming": False,
        "stop_generation": False,
        "streaming_content": "",
        "active_tool": None,
        "tool_status": "",
        "scroll_position": 0,
        "typing_indicator": False,
        "streaming_placeholder": None,
        "tool_status_placeholder": None,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Load conversations from database
    if not st.session_state["conversations"]:
        refresh_conversations()

def refresh_conversations():
    """Refresh conversation list from database"""
    try:
        conversations = get_all_conversations_with_metadata()
        st.session_state["conversations"] = conversations
        
        # Set current conversation if not set
        if not st.session_state["current_conversation"] and conversations:
            latest_conv = max(conversations, key=lambda x: x.get("updated_at", ""))
            st.session_state["current_conversation"] = latest_conv["thread_id"]
            st.session_state["thread_id"] = latest_conv["thread_id"]
            load_conversation_messages(latest_conv["thread_id"])
    except Exception as e:
        st.error(f"Error loading conversations: {e}")

def load_conversation_messages(thread_id: str):
    """Load messages for a specific conversation"""
    try:
        messages = get_conversation_messages(thread_id)
        
        display_messages = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            display_messages.append({
                "role": role,
                "content": msg.content,
                "timestamp": datetime.now().isoformat()
            })
        
        st.session_state["message_history"] = display_messages
        st.session_state["thread_id"] = thread_id
        st.session_state["current_conversation"] = thread_id
        
    except Exception as e:
        st.error(f"Error loading conversation: {e}")
        st.session_state["message_history"] = []

def create_new_conversation():
    """Create a new conversation"""
    new_thread_id = generate_thread_id()
    st.session_state["thread_id"] = new_thread_id
    st.session_state["current_conversation"] = new_thread_id
    st.session_state["message_history"] = []
    st.session_state["search_query"] = ""

# =========================================================
# Streaming Message Functions
# =========================================================

def create_streaming_placeholder():
    """Create a placeholder for streaming content"""
    if st.session_state.get("streaming_placeholder") is None:
        st.session_state["streaming_placeholder"] = st.empty()
    return st.session_state["streaming_placeholder"]

def create_tool_status_placeholder():
    """Create a placeholder for tool status"""
    if st.session_state.get("tool_status_placeholder") is None:
        st.session_state["tool_status_placeholder"] = st.empty()
    return st.session_state["tool_status_placeholder"]

def update_streaming_content(content: str, is_complete: bool = False):
    """Update streaming content with smooth rendering (deprecated - using inline updates)"""
    # This function is no longer used - streaming is handled inline
    pass

def update_tool_status(tool_name: str, status: str = "running"):
    """Update tool status with animation"""
    placeholder = create_tool_status_placeholder()
    
    status_icons = {
        "running": "🔄",
        "completed": "✅",
        "error": "❌"
    }
    
    icon = status_icons.get(status, "🔄")
    status_text = f"{icon} Using {tool_name}..."
    
    if status == "completed":
        status_text = f"✅ {tool_name} completed"
    elif status == "error":
        status_text = f"❌ {tool_name} failed"
    
    with placeholder.container():
        st.markdown(
            f'<div class="tool-status"><span class="tool-icon">{icon}</span> {status_text}</div>',
            unsafe_allow_html=True
        )

def clear_tool_status():
    """Clear tool status placeholder"""
    if st.session_state.get("tool_status_placeholder") is not None:
        st.session_state["tool_status_placeholder"].empty()
        st.session_state["tool_status_placeholder"] = None

def show_typing_indicator():
    """Show animated typing indicator"""
    st.markdown("""
    <div class="typing-dots">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# Enhanced Message Display with Streaming Support
# =========================================================

def display_message(message: Dict[str, Any], message_index: int, is_streaming: bool = False):
    """Display a message with streaming, code highlighting, and code interpreter support"""
    role = message["role"]
    content = message["content"]
    
    with st.chat_message(role):
        if is_streaming and role == "assistant":
            st.markdown(
                f'<div class="streaming-text markdown-content">{content}<span class="typing-cursor"></span></div>',
                unsafe_allow_html=True
            )
        else:
            # Render markdown with native code block support
            st.markdown(content)
            
            # Add copy buttons for code blocks
            render_code_copy_buttons(content)
            
            # Check for code interpreter artifacts (charts, files)
            artifacts = message.get("artifacts", {})
            if artifacts:
                render_code_artifacts(artifacts)


def render_code_copy_buttons(content: str):
    """Detect code blocks in content and add copy buttons"""
    import re
    code_blocks = re.findall(r'```(\w+)?\n(.*?)```', content, re.DOTALL)
    
    if not code_blocks:
        return
    
    for i, (lang, code) in enumerate(code_blocks):
        language = lang or "code"
        code_stripped = code.strip()
        
        # Language label + copy button
        col1, col2 = st.columns([9, 1])
        with col1:
            st.caption(f"📝 {language.upper()}")
        with col2:
            st.code(code_stripped, language=language)

# =========================================================
# Stop Generation Button (st.fragment for independent rerun)
# =========================================================

try:
    # st.fragment is available in Streamlit >= 1.33.0
    @st.fragment(run_every="1s")
    def render_stop_button():
        """Render stop button that stays clickable during streaming.
        
        Uses st.fragment to run on its own rerun loop (every 1 second),
        so the button remains interactive even while stream_response is
        blocking the main script execution.
        """
        if st.session_state.get("is_streaming", False):
            # Show a centered stop button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("⏹️ Stop Generating", key="stop_generation_btn", use_container_width=True, type="primary"):
                    st.session_state["stop_generation"] = True
                    st.toast("Stopping generation...", icon="⏹️")
except (AttributeError, TypeError):
    # Fallback for older Streamlit versions without st.fragment
    def render_stop_button():
        """Fallback stop button (won't work during blocking calls on older Streamlit)"""
        if st.session_state.get("is_streaming", False):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("⏹️ Stop Generating", key="stop_generation_btn", use_container_width=True, type="primary"):
                    st.session_state["stop_generation"] = True
                    st.toast("Stopping generation...", icon="⏹️")

# =========================================================
# Real-Time Streaming Implementation
# =========================================================

def stream_response(message: str):
    """Stream response from LangGraph with stop generation support.
    
    Uses a two-phase approach:
    1. Phase 1: Run chatbot.invoke in background thread, show typing indicator
    2. Phase 2: Display response character-by-character with streaming effect
    
    The stop button is rendered via st.fragment (separate rerun loop) so it
    stays clickable even while this function is running.
    """
    st.session_state["is_streaming"] = True
    st.session_state["stop_generation"] = False
    
    # Add user message to history
    st.session_state["message_history"].append({
        "role": "user",
        "content": message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Display user message
    with st.chat_message("user"):
        st.write(message)
    
    # Create streaming container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Show typing indicator initially
        message_placeholder.markdown("""
        <div class="typing-dots">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Track code interpreter artifacts
        artifacts = {"charts": [], "files": [], "dataframes": []}
        full_content = ""
        stopped = False
        
        try:
            config = {
                "configurable": {
                    "thread_id": st.session_state["thread_id"]
                }
            }
            
            # --- PHASE 1: Run invoke in background thread ---
            invoke_result = {}
            invoke_error = None
            
            def run_invoke():
                nonlocal invoke_result, invoke_error
                try:
                    invoke_result["response"] = chatbot.invoke(
                        {"messages": [HumanMessage(content=message)]},
                        config=config
                    )
                except Exception as e:
                    invoke_error = e
            
            invoke_thread = threading.Thread(target=run_invoke, daemon=True)
            invoke_thread.start()
            
            # Wait for invoke while checking stop flag
            # The stop button is rendered in a st.fragment (see render_stop_button)
            # which reruns independently, so it can be clicked during this loop
            while invoke_thread.is_alive():
                if st.session_state.get("stop_generation", False):
                    stopped = True
                    break
                time.sleep(0.1)
            
            if stopped:
                message_placeholder.markdown(
                    '<div class="markdown-content">⏹️ Generation stopped.</div>',
                    unsafe_allow_html=True
                )
                st.session_state["message_history"].append({
                    "role": "assistant",
                    "content": "⏹️ Generation stopped by user.",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # --- PHASE 2: Display response ---
                if invoke_error:
                    raise invoke_error
                
                response = invoke_result.get("response")
                
                # Extract content and artifacts from all messages
                if response and response.get("messages"):
                    for msg in response["messages"]:
                        if isinstance(msg, ToolMessage):
                            try:
                                tool_content = msg.content
                                if isinstance(tool_content, str):
                                    tool_data = json.loads(tool_content)
                                else:
                                    tool_data = tool_content
                                
                                if tool_data.get("charts_count", 0) > 0 or tool_data.get("files_generated"):
                                    thread_id = st.session_state["thread_id"]
                                    ws_files = list_workspace_files(thread_id)
                                    
                                    for fname in ws_files:
                                        fpath = get_workspace_file_path(thread_id, fname)
                                        if fpath:
                                            size_kb = os.path.getsize(fpath) / 1024
                                            artifacts["files"].append({
                                                "name": fname,
                                                "size": size_kb * 1024,
                                                "path": fpath
                                            })
                                    
                                    for fname in ws_files:
                                        if fname.endswith(".png"):
                                            fpath = get_workspace_file_path(thread_id, fname)
                                            if fpath:
                                                with open(fpath, "rb") as f:
                                                    img_b64 = base64.b64encode(f.read()).decode("utf-8")
                                                artifacts["charts"].append({
                                                    "type": "chart",
                                                    "format": "png",
                                                    "base64": img_b64
                                                })
                            except (json.JSONDecodeError, TypeError, AttributeError):
                                pass
                    
                    last_message = response["messages"][-1]
                    if hasattr(last_message, 'content') and last_message.content:
                        full_content = last_message.content
                
                # Clear typing indicator
                message_placeholder.empty()
                
                # Simulate streaming character by character with stop check
                displayed_content = ""
                
                for i, char in enumerate(full_content):
                    if st.session_state.get("stop_generation", False):
                        stopped = True
                        break
                    
                    displayed_content += char
                    
                    if i < len(full_content) - 1:
                        message_placeholder.markdown(
                            f'<div class="streaming-text markdown-content">{displayed_content}<span class="typing-cursor"></span></div>',
                            unsafe_allow_html=True
                        )
                    else:
                        message_placeholder.markdown(
                            f'<div class="markdown-content">{displayed_content}</div>',
                            unsafe_allow_html=True
                        )
                    
                    # Natural typing delays
                    if char in '.!?':
                        time.sleep(0.2)
                    elif char in ',;:':
                        time.sleep(0.1)
                    elif char == ' ':
                        time.sleep(0.02)
                    else:
                        time.sleep(0.01)
                
                if stopped:
                    message_placeholder.markdown(
                        f'<div class="markdown-content">{displayed_content}\n\n⏹️ Generation stopped.</div>',
                        unsafe_allow_html=True
                    )
                    full_content = displayed_content + "\n\n⏹️ Generation stopped by user."
                else:
                    if artifacts["charts"] or artifacts["files"]:
                        render_code_artifacts(artifacts)
                
                st.session_state["message_history"].append({
                    "role": "assistant",
                    "content": full_content,
                    "timestamp": datetime.now().isoformat(),
                    "artifacts": artifacts if (not stopped and (artifacts["charts"] or artifacts["files"])) else {}
                })
                
                try:
                    refresh_conversations()
                except Exception as refresh_error:
                    print(f"Refresh error: {refresh_error}")
        
        except Exception as e:
            print(f"Error in stream_response: {e}")
            message_placeholder.markdown("Sorry, I encountered an error. Please try again.")
            
            st.session_state["message_history"].append({
                "role": "assistant",
                "content": "Sorry, I encountered an error while generating my response. Please try again.",
                "timestamp": datetime.now().isoformat()
            })
        
        finally:
            st.session_state["is_streaming"] = False
            st.session_state["stop_generation"] = False
            clear_tool_status()
            st.rerun()

# =========================================================
# Sidebar Components (Same as before but optimized)
# =========================================================

def render_sidebar():
    """Render the sidebar with conversation list"""
    with st.sidebar:
        # Header
        st.markdown("""
        <div class="sidebar-header">
            <h2>💬 Conversations</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # New Chat Button
        if st.button("🆕 New Chat", key="new_chat_btn", use_container_width=True, disabled=st.session_state.get("is_streaming", False)):
            create_new_conversation()
            st.rerun()
        
        # Search
        search_query = st.text_input(
            "🔍 Search conversations...",
            value=st.session_state["search_query"],
            key="search_input",
            placeholder="Search by title or content...",
            disabled=st.session_state.get("is_streaming", False)
        )
        
        if search_query != st.session_state["search_query"]:
            st.session_state["search_query"] = search_query
            search_conversations_query(search_query)
        
        # Conversation List
        conversations = st.session_state["conversations"]
        current_thread = st.session_state["current_conversation"]
        
        if not conversations:
            st.info("No conversations yet")
            return
        
        for conv in conversations:
            thread_id = conv["thread_id"]
            title = conv.get("title", "Untitled")
            message_count = conv.get("message_count", 0)
            updated_at = conv.get("updated_at", "")
            has_pdf = conv.get("has_pdf", False)
            document = conv.get("document", {})
            
            # Get last message preview
            last_msg = conv.get("last_message", "")
            preview = format_message_content(last_msg, 60) if last_msg else "No messages yet"
            
            # Time ago
            time_ago = get_time_ago(updated_at) if updated_at else ""
            
            # Determine if this is the active conversation
            is_active = thread_id == current_thread
            
            # Create conversation item
            with st.container():
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    button_text = f"**{title}**"
                    if has_pdf:
                        button_text += f" 📄{document.get('filename', '')[:10]}"
                    
                    if st.button(
                        button_text,
                        key=f"conv_{thread_id}",
                        help=f"{message_count} messages • {time_ago}",
                        use_container_width=True,
                        disabled=st.session_state.get("is_streaming", False)
                    ):
                        switch_conversation(thread_id)
                
                with col2:
                    if st.button(
                        "🗑️",
                        key=f"delete_{thread_id}",
                        help="Delete conversation",
                        use_container_width=True,
                        disabled=st.session_state.get("is_streaming", False)
                    ):
                        if thread_id == current_thread:
                            delete_current_conversation()
                        else:
                            try:
                                delete_thread(thread_id)
                                refresh_conversations()
                                st.success("Conversation deleted")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting conversation: {e}")
                
                if not is_active:
                    st.caption(f"📝 {preview}")
                    st.caption(f"💬 {message_count} messages • {time_ago}")
                
                st.divider()
        
        # =========================================================
        # Coding Profile Section in Sidebar
        # =========================================================
        st.divider()
        st.markdown("""
        <div class="sidebar-header">
            <h2>🏆 Coding Profiles</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Show connected profiles
        thread_id = st.session_state.get("thread_id", "")
        connected = get_coding_profiles(thread_id)
        
        if connected:
            for profile in connected:
                plat = profile["platform"]
                uname = profile["username"]
                icon = "🟢" if plat == "leetcode" else "🟠"
                st.caption(f"{icon} **{plat.title()}**: {uname}")
                
                # Quick stats
                stats = get_latest_coding_stats(thread_id, plat)
                if stats:
                    total = stats.get("total_solved", stats.get("coding_score", 0))
                    st.caption(f"  → Solved: {total}")
        else:
            st.caption("No profiles connected")
        
        # Connect profile inputs
        with st.expander("🔗 Connect Profile", expanded=False):
            lc_user = st.text_input("LeetCode username", key="lc_username_input", placeholder="your_leetcode_username")
            if st.button("Connect LeetCode", key="connect_lc_btn", use_container_width=True):
                if lc_user.strip():
                    st.session_state["pending_lc_connect"] = lc_user.strip()
                    st.toast("Send a message like 'Analyze my LeetCode profile' to connect!", icon="🏆")
            
            gfg_user = st.text_input("GFG username", key="gfg_username_input", placeholder="your_gfg_username")
            if st.button("Connect GFG", key="connect_gfg_btn", use_container_width=True):
                if gfg_user.strip():
                    st.session_state["pending_gfg_connect"] = gfg_user.strip()
                    st.toast("Send a message like 'Check my GFG profile' to connect!", icon="🏆")

def switch_conversation(thread_id: str):
    """Switch to a different conversation"""
    if thread_id != st.session_state["current_conversation"]:
        load_conversation_messages(thread_id)
        st.rerun()

def delete_current_conversation():
    """Delete the current conversation"""
    if st.session_state["current_conversation"]:
        try:
            delete_thread(st.session_state["current_conversation"])
            create_new_conversation()
            refresh_conversations()
            st.success("Conversation deleted")
            st.rerun()
        except Exception as e:
            st.error(f"Error deleting conversation: {e}")

def search_conversations_query(query: str):
    """Search conversations"""
    if not query.strip():
        refresh_conversations()
        return
    
    try:
        search_results = search_conversations(query)
        st.session_state["conversations"] = search_results
    except Exception as e:
        st.error(f"Error searching conversations: {e}")

# =========================================================
# Main Chat Interface with Streaming
# =========================================================

def render_chat_interface():
    """Render the main chat interface with streaming support"""
    # Current conversation info
    current_conv = None
    if st.session_state.get("conversations") and st.session_state.get("current_conversation"):
        current_conv = next(
            (conv for conv in st.session_state["conversations"] 
             if conv["thread_id"] == st.session_state["current_conversation"]), 
            None
        )
    
    if current_conv:
        st.markdown(f"""
        <div style="padding: 16px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 8px; margin-bottom: 20px;">
            <h3>{current_conv.get('title', 'Untitled')}</h3>
            <p style="margin: 0; color: #666; font-size: 0.9em;">
                {current_conv.get('message_count', 0)} messages • 
                Last updated {get_time_ago(current_conv.get('updated_at', ''))}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Messages container
    message_history = st.session_state.get("message_history", [])
    
    if not message_history and not st.session_state.get("is_streaming", False):
        st.markdown("""
        <div style="text-align: center; padding: 60px 20px; color: #666;">
            <h3>🤖 Start a new conversation</h3>
            <p>Ask me anything! I can help with:</p>
            <ul style="text-align: left; max-width: 400px; margin: 0 auto;">
                <li>Answering questions about uploaded PDFs</li>
                <li>Code generation in any language (Python, JS, Java, C++, etc.)</li>
                <li>🏆 LeetCode & GFG profile analytics</li>
                <li>📊 Topic analysis, roadmaps, FAANG readiness</li>
                <li>Running Python code and data analysis</li>
                <li>Analyzing CSV/Excel files with pandas</li>
                <li>Generating charts and visualizations</li>
                <li>Mathematical calculations</li>
                <li>General knowledge and assistance</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Display existing messages
        for i, message in enumerate(message_history):
            display_message(message, i, is_streaming=False)

def render_code_artifacts(artifacts: Dict[str, Any]):
    """Render code interpreter artifacts: charts, files, dataframes"""
    # Render charts
    charts = artifacts.get("charts", [])
    for chart in charts:
        if chart.get("type") == "chart" and chart.get("base64"):
            img_bytes = base64.b64decode(chart["base64"])
            st.image(img_bytes, use_container_width=True)
    
    # Render dataframes
    dataframes = artifacts.get("dataframes", [])
    for df_data in dataframes:
        if df_data.get("type") == "dataframe":
            try:
                import pandas as pd
                df = pd.DataFrame(
                    data=df_data["data"],
                    columns=df_data["columns"]
                )
                st.dataframe(df, use_container_width=True)
            except Exception:
                pass
    
    # Render downloadable files
    files = artifacts.get("files", [])
    thread_id = st.session_state.get("thread_id", "")
    for file_info in files:
        fname = file_info.get("name", "")
        fpath = get_workspace_file_path(thread_id, fname)
        if fpath and os.path.exists(fpath):
            with open(fpath, "rb") as f:
                file_bytes = f.read()
            
            # Determine mime type
            ext = os.path.splitext(fname)[1].lower()
            mime_map = {
                ".csv": "text/csv", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".json": "application/json", ".txt": "text/plain",
                ".png": "image/png", ".pdf": "application/pdf",
            }
            mime = mime_map.get(ext, "application/octet-stream")
            
            st.download_button(
                label=f"📥 Download {fname}",
                data=file_bytes,
                file_name=fname,
                mime=mime,
                key=f"dl_{fname}_{hash(fpath)}"
            )


def render_input_interface():
    """Render the chat input interface with file upload and streaming support"""
    # File Upload Section (expanded to support CSV, XLSX, PDF, JSON, TXT)
    with st.expander("📁 Upload Files (Optional)", expanded=False):
        uploaded_files = st.file_uploader(
            "Choose files",
            type=["csv", "xlsx", "xls", "pdf", "json", "txt"],
            accept_multiple_files=True,
            disabled=st.session_state.get("is_streaming", False),
            key="file_uploader_main"
        )
        
        if uploaded_files and not st.session_state.get("is_streaming", False):
            thread_id = st.session_state.get("thread_id", generate_thread_id())
            
            for uploaded_file in uploaded_files:
                try:
                    file_bytes = uploaded_file.getvalue()
                    filename = uploaded_file.name
                    
                    if filename.endswith(".pdf"):
                        # PDF goes through RAG pipeline with progress
                        progress = st.progress(0, text=f"📄 Processing {filename}...")
                        try:
                            progress.progress(20, text="📄 Reading PDF pages...")
                            progress.progress(40, text="📄 Splitting into chunks...")
                            metadata = ingest_pdf(
                                file_bytes,
                                thread_id=thread_id,
                                filename=filename
                            )
                            progress.progress(100, text="✅ Done!")
                        finally:
                            progress.empty()
                        st.success(f"""
                        ✅ PDF uploaded: {metadata.get('filename')} ({metadata.get('documents')} pages, {metadata.get('chunks')} chunks)
                        """)
                    else:
                        # CSV, XLSX, JSON, TXT go to workspace
                        saved_path = save_uploaded_file(thread_id, filename, file_bytes)
                        size_kb = len(file_bytes) / 1024
                        st.success(f"✅ File saved: {filename} ({size_kb:.1f} KB) — available for Python analysis")
                
                except Exception as e:
                    st.error(f"Error uploading {uploaded_file.name}: {e}")
            
            refresh_conversations()
    
    # Show uploaded files in workspace
    thread_id = st.session_state.get("thread_id", "")
    workspace_files = list_workspace_files(thread_id)
    if workspace_files:
        with st.expander("📂 Workspace Files", expanded=False):
            for fname in workspace_files:
                fpath = get_workspace_file_path(thread_id, fname)
                if fpath:
                    size_kb = os.path.getsize(fpath) / 1024
                    st.text(f"📄 {fname} ({size_kb:.1f} KB)")
    
    # Stop button — rendered as a fragment so it stays clickable during streaming
    render_stop_button()
    
    # Chat Input with streaming support
    user_input = st.chat_input(
        "Ask me anything... (try 'analyze my data' or 'plot a chart')",
        disabled=st.session_state.get("is_streaming", False),
        key="streaming_chat_input"
    )
    
    # Handle message sending with streaming
    if user_input and user_input.strip() and not st.session_state.get("is_streaming", False):
        stream_response(user_input.strip())

# =========================================================
# Main Application with Streaming
# =========================================================

def main():
    """Main application entry point with streaming support"""
    # Initialize session state
    try:
        init_session_state()
    except Exception as e:
        st.error(f"Error initializing session: {e}")
        return
    
    # Inject auto-scroll JavaScript
    inject_auto_scroll_script()
    
    # Render sidebar
    try:
        render_sidebar()
    except Exception as e:
        st.error(f"Error rendering sidebar: {e}")
    
    # Main content area
    st.title("🤖 AI Assistant")
    
    # Chat interface
    try:
        render_chat_interface()
    except Exception as e:
        st.error(f"Error in chat interface: {e}")
    
    # Input interface
    try:
        render_input_interface()
    except Exception as e:
        st.error(f"Error in input interface: {e}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>💬 Streaming • 📄 PDF • 🐍 Code Interpreter • 🏆 Coding Analytics • 🔍 Search • 🧠 AI</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
