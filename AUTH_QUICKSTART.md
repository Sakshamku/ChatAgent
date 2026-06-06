# Quick Start: Authentication Setup & Testing

## 1. Install Dependencies

### Backend
```bash
cd backend
pip install -r requirements.txt
```

### Frontend
```bash
cd next-frontend
npm install
```

---

## 2. Environment Configuration

### Backend (create `.env` or set shell variables)
```bash
# Required (CHANGE IN PRODUCTION!)
export AUTH_SECRET_KEY="dev-secret-key-change-this-in-production"

# Optional (defaults shown)
export ACCESS_TOKEN_EXPIRE_MINUTES=10080
export DATABASE_URL="sqlite:///./data/auth.db"
```

### Frontend
```bash
# In next-frontend/.env.local (create if missing)
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

---

## 3. Run the Application

### Terminal 1: Backend
```bash
cd d:\ChatAgent\backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Frontend
```bash
cd d:\ChatAgent\next-frontend
npm run dev
# Open http://localhost:3000
```

---

## 4. Manual Testing Workflow

### 4.1 Sign Up (New User)
1. Navigate to `http://localhost:3000`
2. Browser redirects to `/login`
3. Click "Create an account" → Go to `/signup`
4. Fill in:
   - Full Name: `John Doe`
   - Email: `john@example.com`
   - Password: `SecurePass123`
5. Click "Create Account"
6. **Expected**: Redirected to `/mock-test-arena`, localStorage has `chatagent_token`

### 4.2 Mock Test Generation
1. On Mock Test Arena, select "DSA Mock Test"
2. (Optional) Enter LeetCode/GFG usernames
3. Click "Generate Test"
4. **Expected**: Single DSA problem loads with adaptive difficulty
5. Token sent as `Authorization: Bearer <token>` header
6. Backend validates token, creates mock_test_attempt with authenticated user_id

### 4.3 Sign Out & Sign Back In
1. Browser DevTools → Application → Storage → localStorage
2. Clear `chatagent_token` manually
3. Refresh page
4. **Expected**: Redirected to `/login`
5. Sign in with same email/password from 4.1
6. **Expected**: Redirected back to `/mock-test-arena`

### 4.4 Test Data Isolation
1. Sign up as `user1@example.com`
2. Generate a test, submit an answer (score recorded)
3. Clear localStorage, sign out
4. Sign up as `user2@example.com`
5. View analytics → **Expected**: 0 score (different user's data hidden)
6. View `/mock-tests/analytics/user1-id` as user2 → **Expected**: 403 Forbidden

---

## 5. API Testing (Postman/cURL)

### Sign Up
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User",
    "email": "test@example.com",
    "password": "TestPass123"
  }'

# Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "full_name": "Test User",
    "email": "test@example.com",
    "created_at": "2025-01-20T14:30:00"
  }
}
```

### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123"
  }'

# Response: Same as signup
```

### Validate Token
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# Response:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Test User",
  "email": "test@example.com",
  "created_at": "2025-01-20T14:30:00"
}
```

### Generate Mock Test (Protected)
```bash
curl -X POST http://localhost:8000/mock/dsa/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -d '{
    "leetcode_username": "johndoe",
    "gfg_username": "johndoe"
  }'

# Response: DSA test with user's question saved to database
```

### Without Token (Should Fail)
```bash
curl -X POST http://localhost:8000/mock/dsa/generate \
  -H "Content-Type: application/json" \
  -d '{"leetcode_username": "johndoe"}'

# Response: 403 Unauthorized
# detail: "Not authenticated"
```

---

## 6. Database Inspection

### View SQLite Auth Database
```bash
sqlite3 d:\ChatAgent\data\auth.db

# List users
SELECT id, full_name, email, created_at FROM users;

# Count users
SELECT COUNT(*) FROM users;
```

### View SQLite Chat Database (with user associations)
```bash
sqlite3 d:\ChatAgent\data\chat_history.db

# View mock test attempts with user_id
SELECT id, user_id, test_type, status, started_at FROM mock_test_attempts LIMIT 10;

# Count tests per user
SELECT user_id, test_type, COUNT(*) FROM mock_test_attempts GROUP BY user_id, test_type;
```

---

## 7. Debugging Checklist

| Issue | Check |
|-------|-------|
| 401 Unauthorized on protected endpoints | JWT token valid? Bearer format correct? `Authorization: Bearer <token>` |
| Token not persisting | localStorage key correct? Check DevTools Storage |
| 403 Forbidden on analytics | Accessing own user_id or another user's? Backend validates ownership |
| Redirect loop to /login | AuthContext provider missing in layout.tsx? |
| Password hash mismatch at login | bcrypt version compatible? Check backend/auth.py |
| CORS errors from frontend | Backend CORS middleware? Check app.add_middleware in api/main.py |
| Database locked error | Multiple processes accessing sqlite? Use PostgreSQL for multi-process |

---

## 8. Production Deployment Notes

### Docker Compose Example
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      AUTH_SECRET_KEY: "${AUTH_SECRET_KEY}"
      DATABASE_URL: "postgresql://user:pass@db:5432/chatagent"
    depends_on:
      - db

  frontend:
    build: ./next-frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: "http://localhost:8000"

  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: "postgres"
      POSTGRES_DB: "chatagent"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### Secrets Management
- Use environment variables or secrets vault (AWS Secrets Manager, HashiCorp Vault, etc.)
- Never commit `.env` files with real secrets
- Rotate `AUTH_SECRET_KEY` periodically

### HTTPS Setup
- Use Let's Encrypt or self-signed certificates
- Configure nginx/Apache reverse proxy
- Force HTTPS redirect
- Set Secure flag on cookies (if using cookies instead of localStorage)

---

## 9. Known Limitations & TODOs

- ✅ Email uniqueness enforced
- ⚠️ No email verification workflow
- ⚠️ No password reset functionality
- ⚠️ No rate limiting on auth endpoints (add for production)
- ⚠️ Token revocation not implemented (consider for logout)
- ⚠️ Single device session (no session list/management)

---

## 10. Support & Debugging

### Enable Debug Logging
```python
# In backend/api/main.py before running
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Frontend Console Errors
- Open DevTools (F12) → Console tab
- Check for CORS, auth, or network errors
- Network tab → Check request/response headers and bodies

### Common Errors
```
"email already exists" → User registered twice, use login endpoint
"Invalid email or password" → Check credentials carefully (case-sensitive)
"Could not validate credentials" → Token expired, re-login needed
"Unauthorized to submit this test" → Submitting attempt from different user (should not happen)
```

---

## 11. Quick Reference

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| /auth/signup | POST | ❌ | Register new user |
| /auth/login | POST | ❌ | Sign in, get JWT |
| /auth/me | GET | ✅ | Validate token, get user |
| /mock/{arena}/generate | POST | ✅ | Create test, return question |
| /mock-tests/start | POST | ✅ | Begin test session |
| /mock-tests/submit | POST | ✅ | Submit answer, record score |
| /mock-tests/analytics | GET | ✅ | Get current user's stats |
| /aptitude-tests/generate | POST | ✅ | Generate 20-question test |
| /aptitude-tests/submit | POST | ✅ | Submit all answers, calculate score |

---

Done! ✓ Authentication Phase 1 is ready for testing and deployment.
