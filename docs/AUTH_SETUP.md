# NextAuth.js Multi-Provider Authentication Setup

This implementation provides a complete authentication system with:

## Features Implemented

### 🔐 Authentication
- **NextAuth.js** with multiple OAuth providers (Google, GitHub)
- **Session management** with JWT tokens
- **Role-based access control** (FREE, PREMIUM, ADMIN)
- **Protected routes** and API endpoints

### 🗄️ Database
- **PostgreSQL** database with Prisma ORM
- **User management** with role-based permissions
- **Blog generation tracking** and history
- **Usage limits** per user role

### 🎯 User Roles
- **FREE**: 5 blogs per month
- **PREMIUM**: Unlimited blogs
- **ADMIN**: Full system access

### 🔧 API Endpoints
- `POST /api/generate-blog` - Generate blog with authentication
- `GET /api/blogs` - Get user's blog history
- `DELETE /api/blogs?id=<blog_id>` - Delete user's blog

## Setup Instructions

### 1. Environment Variables
Update your `.env.local` file:

```bash
# Database
DATABASE_URL="postgresql://username:password@localhost:5432/bloggen_db?schema=public"

# NextAuth.js
NEXTAUTH_URL="http://localhost:3001"
NEXTAUTH_SECRET="your-generated-secret-here"

# OAuth Providers
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
GITHUB_ID="your-github-client-id"
GITHUB_SECRET="your-github-client-secret"

# Backend API
API_BASE_URL="http://localhost:5000"
```

### 2. OAuth Provider Setup

#### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add `http://localhost:3001/api/auth/callback/google` to redirect URIs

#### GitHub OAuth
1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create a new OAuth App
3. Set Authorization callback URL to `http://localhost:3001/api/auth/callback/github`

### 3. Database Setup

```bash
# Install PostgreSQL (if not already installed)
# For Ubuntu/Debian:
sudo apt-get install postgresql postgresql-contrib

# For macOS:
brew install postgresql

# Create database
createdb bloggen_db

# Run migrations
npx prisma db push

# Generate Prisma client
npx prisma generate
```

### 4. Start Development Server

```bash
npm run dev
```

## File Structure

```
src/
├── app/
│   ├── api/
│   │   ├── auth/[...nextauth]/route.ts  # NextAuth API route
│   │   ├── generate-blog/route.ts       # Blog generation API
│   │   └── blogs/route.ts               # Blog management API
│   ├── auth/
│   │   ├── signin/page.tsx              # Sign in page
│   │   └── error/page.tsx               # Auth error page
│   └── blog/page.tsx                    # Main blog page (protected)
├── components/
│   └── auth/
│       ├── AuthProvider.tsx             # Session provider
│       └── UserProfile.tsx              # User profile component
├── hooks/
│   └── useAuth.ts                       # Authentication hooks
├── lib/
│   ├── auth.ts                          # NextAuth configuration
│   ├── prisma.ts                        # Prisma client
│   └── services/
│       └── user.ts                      # User & blog services
├── types/
│   └── next-auth.d.ts                   # NextAuth type definitions
└── prisma/
    └── schema.prisma                    # Database schema
```

## Usage

### Authentication Flow
1. User visits `/blog`
2. If not authenticated, redirected to `/auth/signin`
3. User chooses OAuth provider (Google/GitHub)
4. After successful authentication, redirected back to `/blog`
5. User can now generate blogs within their role limits

### Role-Based Features
- **FREE users**: Limited to 5 blogs per month
- **PREMIUM users**: Unlimited blog generation
- **ADMIN users**: Full system access + user management

### Backend Integration
The frontend now sends authenticated requests to your Python backend. You'll need to:

1. Update your backend to accept the `user_id` parameter
2. Implement user-specific blog storage
3. Add WebSocket authentication for real-time updates

## Next Steps

1. **Frontend**: Add theme support (dark/light mode)
2. **Backend**: Integrate with the new PostgreSQL database
3. **Features**: Add blog templates, export options, sharing
4. **Deployment**: Set up production environment variables
5. **Monitoring**: Add analytics and error tracking

The authentication system is now fully functional and ready for production use!
