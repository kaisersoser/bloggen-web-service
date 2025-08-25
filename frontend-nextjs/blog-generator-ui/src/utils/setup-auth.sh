#!/bin/bash

# Setup script for NextAuth.js and PostgreSQL

echo "🔧 Setting up AI Blog Generator with NextAuth.js and PostgreSQL"

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "❌ .env.local file not found! Please create it first."
    exit 1
fi

echo "📦 Installing required dependencies..."
npm install next-auth @auth/prisma-adapter prisma @prisma/client bcryptjs @types/bcryptjs @radix-ui/react-avatar

echo "🗄️  Setting up PostgreSQL database..."
echo "Please ensure you have PostgreSQL installed and running."
echo "Update your .env.local file with your database connection string:"
echo "DATABASE_URL=\"postgresql://username:password@localhost:5432/bloggen_db?schema=public\""

echo ""
echo "🔐 Setting up OAuth providers..."
echo "You need to set up OAuth applications:"
echo ""
echo "1. Google OAuth:"
echo "   - Go to https://console.cloud.google.com/"
echo "   - Create a project or select existing"
echo "   - Enable Google+ API"
echo "   - Create OAuth 2.0 credentials"
echo "   - Add http://localhost:3001/api/auth/callback/google to redirect URIs"
echo ""
echo "2. GitHub OAuth:"
echo "   - Go to https://github.com/settings/developers"
echo "   - Create a new OAuth App"
echo "   - Set Authorization callback URL to http://localhost:3001/api/auth/callback/github"
echo ""
echo "3. Update your .env.local file with the client IDs and secrets"

echo ""
echo "🔑 Generating NextAuth secret..."
# Generate a random secret for NextAuth
SECRET=$(openssl rand -base64 32)
echo "Add this to your .env.local file:"
echo "NEXTAUTH_SECRET=\"$SECRET\""

echo ""
echo "🏗️  Running database migrations..."
if command -v psql &> /dev/null; then
    echo "Creating database (if it doesn't exist)..."
    # This will create the database if it doesn't exist
    createdb bloggen_db 2>/dev/null || echo "Database might already exist"
fi

echo "Generating Prisma client..."
npx prisma generate

echo "Running database migrations..."
npx prisma db push

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update your .env.local with OAuth credentials"
echo "2. Make sure PostgreSQL is running"
echo "3. Run 'npm run dev' to start the development server"
echo "4. Update your backend to use the new database for user management"
