# Phase 1 Authentication Implementation Guide

## Overview
This document describes the authentication system implementation for the ChatAgent Mock Test Arena. All authentication logic is isolated to the mock test endpoints, leaving the existing chat functionality untouched.

---

## 1. Backend Changes

### 1.1 New File: `backend/auth.py`
Comprehensive authentication module with SQLAlchemy ORM, bcrypt password hashing, and JWT token management.

**Key Components:**
- **User Model** - SQLAlchemy table with email uniqueness constraint
- **Password Security** - bcrypt hashing (10 salt rounds)
- **JWT Tokens** - HS256 algorithm, 7-day default expiry
- **OAuth2 Dependency** - `get_current_user()` for endpoint protection
- **Database Init** - Automatic schema creation on import

**Environment Variables:**
```
AUTH_SECRET_KEY          # JWT signing key (default: placeholder, CHANGE THIS)
ACCESS_TOKEN_EXPIRE_MINUTES  # Token expiry in minutes (default: 10080 = 7 days)
DATABASE_URL             # SQLite or PostgreSQL (default: data/auth.db)
```

### 1.2 Modified File: `backend/api/main.py`

**New Endpoints:**
```
POST /auth/signup          → Register new user (full_name, email, password)
POST /auth/login           → Login (email, password) → Returns JWT token
GET  /auth/me              → Validate token + return current user profile
```

**Protected Endpoints (require JWT token in Authorization header):**
```
POST /mock/{arena}/generate          → Uses current_user.id for user_id
POST /mock-tests/start               → Uses current_user.id for user_id
POST /mock-tests/submit              → Validates user owns the attempt
POST /aptitude-tests/generate        → Uses current_user.id for user_id
POST /aptitude-tests/submit          → Validates user owns the attempt
GET  /mock-tests/analytics           → Returns current user's analytics
GET  /mock-tests/analytics/{user_id} → Validates user_id matches current user
GET  /aptitude-tests/attempts        → Returns current user's attempts
GET  /aptitude-tests/attempts/{user_id} → Validates user_id matches current user
```

**No Changes:**
- Chat endpoints remain completely unmodified
- All existing database tables remain intact

### 1.3 Updated: `backend/requirements.txt`
Added packages:
- `bcrypt>=4.0.0` - Password hashing
- `PyJWT>=2.8.0` - JWT token handling
- `SQLAlchemy>=2.0.0` - ORM for user management
- `psycopg2-binary>=2.9.0` - PostgreSQL support (optional)
- `email-validator` - Pydantic email validation

---

## 2. Frontend Changes

### 2.1 New File: `next-frontend/contexts/AuthContext.tsx`
React Context API provider managing authentication state and operations.

**Exported Hook: `useAuth()`**
```typescript
interface AuthContextValue {
  user: User | null;           // Current user or null
  token: string | null;        // JWT token or null
  loading: boolean;            // Loading state on mount
  login: (email, password) => Promise<void>;    // Sign in
  signup: (full_name, email, password) => Promise<void>;  // Register
  logout: () => void;          // Sign out
}
```

**Features:**
- Automatic session validation on app mount
- localStorage token persistence (key: `chatagent_token`)
- Automatic redirect to `/login` on 401 errors
- Router integration for post-login redirects

### 2.2 New File: `next-frontend/app/providers.tsx`
Wraps app with AuthProvider to enable useAuth() throughout the app.

### 2.3 New Pages

#### `next-frontend/app/login/page.tsx`
- Email/password login form
- Error handling and display
- Redirect to `/mock-test-arena` on success
- Link to signup page
- Dark theme styling (slate-950/slate-900)

#### `next-frontend/app/signup/page.tsx`
- Registration form (full_name, email, password)
- Email validation
- Duplicate email detection
- Redirect to `/mock-test-arena` on success
- Link to login page
- Dark theme styling (slate-950/slate-900)

### 2.4 Protected Page: `next-frontend/app/mock-test-arena/page.tsx`
Wrapper component that:
1. Checks `useAuth()` for user session
2. Redirects to `/login` if no user
3. Shows loading state during validation
4. Renders MockTestArena on success

### 2.5 Modified: `next-frontend/app/layout.tsx`
- Wraps children with `<Providers>` component
- Enables AuthContext globally

### 2.6 Updated: `next-frontend/lib/api.ts`
New helper functions and types:
```typescript
authFetch<T>(route, token?, options?) → Promise<T>   // Fetch with Bearer token
signup(payload) → Promise<AuthResponse>               // Register new user
login(payload) → Promise<AuthResponse>                // Sign in
getCurrentUser(token) → Promise<User>                 // Validate token
```

### 2.7 Modified: `next-frontend/components/MockTestArena.tsx`
- Removed localStorage-based anonymous user ID
- Now uses `useAuth()` to get authenticated user ID
- Replaced fetch calls with `authFetch()` for Bearer token injection
- Token validation required for test generation and submission

---

## 3. User Flow

### Registration & First Login
```
1. User visits app → AuthContext checks localStorage for token
2. No token found → AuthProvider sets loading=true, user=null
3. App renders Login page (sees no user)
4. User clicks "Create Account" → Navigate to /signup
5. Enter full_name, email, password → Click "Create Account"
6. Frontend POSTs to /auth/signup with credentials
7. Backend creates User, hashes password with bcrypt
8. Returns JWT token + User object
9. Frontend stores token in localStorage
10. AuthContext updates state: token, user
11. useAuth hook triggers redirect to /mock-test-arena
12. Mock Test Arena renders with authenticated user
```

### Returning User Login
```
1. User visits app → AuthContext checks localStorage
2. Token found → Sets it in state, calls /auth/me
3. /auth/me validates JWT, returns User object
4. AuthContext updates: loading=false, user, token
5. Any protected route now renders (e.g., /mock-test-arena)
```

### Taking a Mock Test
```
1. User on /mock-test-arena clicks "Generate Test"
2. Frontend calls POST /mock/{arena}/generate with Bearer token
3. Backend dependency: get_current_user validates token → extracts user.id
4. endpoint receives current_user object, uses current_user.id for mock_test_attempts
5. Questions saved with user_id linked to authenticated user
6. User submits answer → POST /mock-tests/submit with user_id validation
7. Attempt verified to belong to current_user before recording answer
```

---

## 4. Database Schema

### Users Table (auth.db)
```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_email ON users(email);
```

### Existing Mock Test Tables (chat_history.db)
- `mock_test_attempts` - Now has user_id (text) instead of anonymous user_id
- `mock_test_questions` - Linked via attempt_id
- All queries filtered by `WHERE user_id = ?` to isolate user data

---

## 5. Deployment Checklist

### Environment Variables
```bash
# Production (change these!)
AUTH_SECRET_KEY=your-super-secret-key-here-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Optional: PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/chatagent_auth
```

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
# New auth.py and auth tables auto-initialized on first import
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd next-frontend
npm install
npm run build
npm start
```

### Database
- **SQLite** (default): `data/auth.db` created automatically in project root
- **PostgreSQL**: Set `DATABASE_URL` env var before starting

---

## 6. Security Considerations

✅ **Password Security**
- bcrypt with 10 salt rounds (recommended OWASP standard)
- Never logs or transmits plaintext passwords

✅ **Token Security**
- JWT signed with SECRET_KEY (change this in production!)
- 7-day default expiry (user must re-login)
- Stored in httpOnly cookie NOT recommended (using localStorage for SPA flexibility)

✅ **Authorization**
- Every protected endpoint validates ownership (user_id check)
- Users cannot access other users' test attempts or analytics

✅ **Input Validation**
- Pydantic validates email format and required fields
- Email uniqueness enforced at database level

⚠️ **Production Recommendations**
1. Change `AUTH_SECRET_KEY` to a cryptographically random string
2. Use HTTPS in production (bearer tokens exposed over HTTP)
3. Implement rate limiting on /auth/login and /auth/signup
4. Consider adding CSRF protection if using cookies
5. Log failed login attempts for security monitoring
6. Add email verification workflow (optional enhancement)

---

## 7. Troubleshooting

### "Could not validate credentials" on /auth/me
- Token expired → User must re-login
- Token modified → Invalid signature detected
- Token format wrong → Should be `Authorization: Bearer <token>`

### User can see other users' test results
- Likely backend endpoint missing `current_user` dependency
- Check that endpoint has `current_user=Depends(get_current_user)` parameter
- Verify user_id ownership check before returning data

### Token not persisting across page reloads
- Check browser localStorage (DevTools → Application → Storage)
- Verify `STORAGE_KEY = "chatagent_token"` is set in AuthContext
- Check that AuthProvider wraps entire app in layout.tsx

### "Session expired" on mock test page
- Token likely deleted from localStorage
- User must manually visit /login again
- Consider adding toast notification before redirect

---

## 8. Future Enhancements (Phase 2+)

Possible improvements:
- [ ] Email verification for new signups
- [ ] Password reset functionality
- [ ] Refresh token rotation (separate refresh token endpoint)
- [ ] Multi-device session management
- [ ] Two-factor authentication
- [ ] SSO integration (Google, GitHub, etc.)
- [ ] User profile customization page
- [ ] Activity logging and audit trail
