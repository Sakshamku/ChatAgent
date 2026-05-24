# 🤖 AI Chatbot with Persistent Chat History

A production-ready chatbot application built with Streamlit and LangGraph featuring ChatGPT-like persistent conversation history, PDF RAG capabilities, and comprehensive conversation management.

## ✨ Features

### 🗣️ ChatGPT-like Interface
- **Persistent Chat History**: All conversations automatically saved to SQLite database
- **Smart Conversation Management**: Create, switch, delete conversations seamlessly
- **Automatic Title Generation**: Human-readable titles generated from first message
- **Search Functionality**: Search conversations by title or content
- **Real-time Streaming**: Smooth chat experience with typing indicators

### 📄 PDF RAG System
- **PDF Upload & Processing**: Upload PDFs for contextual conversations
- **Vector Search**: FAISS-based semantic search within documents
- **Document Metadata**: Track file info, chunks, and pages
- **Multi-thread Support**: Each conversation can have its own documents

### 🛠️ Advanced Features
- **Tool Integration**: Calculator, stock prices, web search, PDF RAG
- **LangGraph State Management**: Robust conversation state handling
- **Database Architecture**: Optimized SQLite with proper indexing
- **Error Handling**: Graceful error recovery and user feedback
- **Performance Optimized**: Caching, lazy loading, efficient queries

## 🏗️ Architecture

### File Structure
```
ChatAgent/
├── database.py          # SQLite database layer
├── utils.py             # Helper functions and utilities
├── Backend.py           # LangGraph backend with database integration
├── Frontend_new.py      # Streamlit frontend (ChatGPT-like)
├── requirements_new.txt # Updated dependencies
└── README.md           # This file
```

### Database Schema
```sql
conversations:
├── id (PRIMARY KEY)
├── thread_id (UNIQUE)
├── title
├── created_at
└── updated_at

messages:
├── id (PRIMARY KEY)
├── thread_id (FOREIGN KEY)
├── role (user/assistant/system)
├── content
└── timestamp

documents:
├── id (PRIMARY KEY)
├── thread_id (FOREIGN KEY)
├── filename
├── chunks
├── pages
└── uploaded_at
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements_new.txt
```

### 2. Set Up Environment Variables
Create `.env` file:
```env
MISTRAL_API_KEY=your_mistral_api_key_here
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
```

### 3. Run the Application
```bash
streamlit run Frontend_new.py
```

## 📖 Usage Guide

### Starting Conversations
1. **New Chat**: Click "🆕 New Chat" to start fresh
2. **Automatic Title**: First message generates conversation title
3. **PDF Upload**: Optional PDF upload for contextual questions

### Managing Conversations
- **Switch Chats**: Click any conversation in sidebar
- **Search**: Use search bar to find specific conversations
- **Delete**: Remove conversations with 🗑️ button
- **PDF Indicator**: 📄 shows conversations with uploaded documents

### Features
- **Web Search**: Ask questions about current events
- **Stock Prices**: Get real-time stock information
- **Calculator**: Perform mathematical calculations
- **PDF Q&A**: Ask questions about uploaded documents

## 🔧 Configuration

### API Keys Required
- **Mistral AI**: For chat responses
- **Alpha Vantage**: For stock price data

### Database Settings
- **Location**: `chat_history.db` (SQLite)
- **Auto-backup**: Configurable cleanup intervals
- **Indexes**: Optimized for fast queries

### Performance Settings
- **Caching**: LRU cache for embeddings and LLM
- **Lazy Loading**: Load conversations on demand
- **Memory Management**: Efficient vector storage

## 🧩 Technical Details

### Backend Integration
```python
# Database integration in chat_node
def chat_node(state: ChatState, config=None):
    # Save user message
    save_message(thread_id, "user", message_content)
    
    # Generate title for new conversations
    if not get_conversation_title(thread_id):
        title = generate_chat_title(message_content)
        create_conversation(thread_id, title)
    
    # Get AI response
    response = llm_with_tools.invoke(messages, config)
    
    # Save assistant response
    save_message(thread_id, "assistant", response.content)
```

### Frontend Features
- **Responsive Design**: Works on all screen sizes
- **Real-time Updates**: Live conversation switching
- **Smooth Animations**: CSS transitions and indicators
- **Error Recovery**: Graceful handling of network issues

### Performance Optimizations
- **Database Indexes**: Fast query performance
- **Connection Pooling**: Thread-safe database access
- **Memory Caching**: LRU cache for expensive operations
- **Lazy Loading**: Load data only when needed

## 🔄 Migration from Old System

### Data Migration
If upgrading from the previous system:

1. **Backup existing data**
2. **Run database initialization** (automatic)
3. **Update imports** in existing code
4. **Test functionality**

### Breaking Changes
- **New frontend**: Use `Frontend_new.py`
- **Database schema**: New persistent storage
- **Function names**: Updated API calls

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Error
```bash
# Check database file permissions
ls -la chat_history.db

# Reinitialize database
python -c "from database import initialize_database; initialize_database()"
```

#### API Key Issues
```bash
# Verify environment variables
echo $MISTRAL_API_KEY
echo $ALPHA_VANTAGE_API_KEY

# Check .env file format
cat .env
```

#### PDF Processing Errors
```bash
# Check dependencies
pip install pypdf langchain-community

# Verify PDF file
file your_document.pdf
```

### Performance Issues

#### Slow Loading
- Check database indexes
- Reduce conversation history size
- Clear cache with `streamlit cache clear`

#### Memory Issues
- Limit concurrent conversations
- Use smaller PDF files
- Restart application periodically

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd ChatAgent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements_new.txt

# Run in development mode
streamlit run Frontend_new.py --server.runOnSave true
```

### Code Style
- **Python**: Follow PEP 8
- **Type Hints**: Use for all functions
- **Documentation**: Comprehensive docstrings
- **Error Handling**: Try-catch blocks with user feedback

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **LangChain**: For the LLM framework
- **Streamlit**: For the web interface
- **LangGraph**: For conversation state management
- **FAISS**: For vector similarity search
- **Mistral AI**: For the language model

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the documentation

---

**Built with ❤️ using Streamlit + LangGraph**
