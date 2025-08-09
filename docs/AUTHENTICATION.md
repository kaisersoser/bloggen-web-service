# Backend Authentication Setup

## Security Status: ✅ PROTECTED

The backend has been updated with comprehensive authentication and authorization protection.

## Authentication Features

### 🔒 Protected Endpoints
- **`/generate-blog`** - Requires authentication + role-based generation limits
- **`/task-status/<task_id>`** - Requires authentication + user ownership verification
- **`/my-tasks`** - Requires authentication (user's own tasks only)
- **`/tasks`** - Requires authentication + ADMIN role

### 🛡️ Security Middleware
- **JWT Token Verification**: Validates NextAuth.js JWT tokens
- **Role-Based Access Control**: FREE/PREMIUM/ADMIN role restrictions
- **Generation Limits**: Per-role monthly blog generation limits
- **User Ownership**: Users can only access their own resources
- **CORS Protection**: Limited to frontend origin only

### 👥 Role-Based Features
- **FREE**: 3 blogs per month
- **PREMIUM**: 50 blogs per month  
- **ADMIN**: Unlimited access + admin endpoints

## Setup Instructions

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Configuration
Ensure your `backend/.env` file includes:
```bash
# NextAuth.js Configuration (must match frontend)
NEXTAUTH_SECRET="Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w="
NEXTAUTH_URL="http://localhost:3001"

# Frontend URL for CORS
FRONTEND_URL="http://localhost:3001"
```

### 3. Frontend Integration
The frontend now sends JWT tokens in API requests:
```typescript
headers: {
  "Authorization": `Bearer ${token}`
}
```

## Authentication Flow

1. User logs in through frontend (NextAuth.js)
2. Frontend receives JWT token
3. Frontend includes token in API requests to backend
4. Backend middleware verifies JWT token
5. Backend extracts user information (ID, email, role)
6. Backend enforces role-based permissions
7. Backend processes authorized requests

## API Endpoints

### Public Endpoints
- None (all endpoints now require authentication)

### Authenticated Endpoints
- `POST /generate-blog` - Generate blog (with role limits)
- `GET /task-status/<task_id>` - Get task status (own tasks only)
- `GET /my-tasks` - Get user's tasks

### Admin Only Endpoints
- `GET /tasks` - Get all tasks (admin monitoring)

## Error Responses

### 401 Unauthorized
```json
{
  "error": "Authentication required",
  "message": "No valid authentication token provided"
}
```

### 403 Forbidden
```json
{
  "error": "Insufficient permissions",
  "message": "This endpoint requires ADMIN role"
}
```

### 429 Rate Limited
```json
{
  "error": "Generation limit exceeded", 
  "message": "Your free plan has reached its monthly limit",
  "limit": 3
}
```

## Testing Authentication

### Test with curl
```bash
# This will fail without authentication
curl -X POST http://localhost:5000/generate-blog \
  -H "Content-Type: application/json" \
  -d '{"topic": "Test Blog"}'

# This requires valid JWT token
curl -X POST http://localhost:5000/generate-blog \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"topic": "Test Blog"}'
```

## Database Integration

The authentication system integrates with your Supabase database:
- User information is stored and verified against the database
- Blog generation counts are tracked per user
- Role-based permissions are enforced based on database records

Important: Ensure the SAME `DATABASE_URL` value exists in both `frontend-nextjs/blog-generator-ui/.env.local` and `backend/.env`. The backend relies on it for:
- Audit session + llm_calls logging (cost + Serper tracking)
- Admin analytics aggregation
- Any direct schema inspection or diagnostics

If the backend `.env` is missing or has a different value you may see missing Serper or LLM call rows even though the frontend DB is populated.

## Next Steps

1. ✅ Authentication middleware implemented
2. ✅ Protected endpoints configured  
3. ✅ Role-based access control setup
4. 🔄 **Set up OAuth providers** (Google, GitHub)
5. 🔄 **Test complete authentication flow**
6. 🔄 **Deploy with proper production settings**
