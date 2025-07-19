#!/bin/bash

# Supabase Setup Script for AI Blog Generator

echo "🚀 Setting up Supabase for AI Blog Generator"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📋 Please have the following ready from your Supabase project:${NC}"
echo "1. Your Supabase Project URL"
echo "2. Your database password"
echo "3. Your project reference ID"
echo ""

# Get Supabase connection details
echo -e "${YELLOW}🔧 Configuring your .env.local file...${NC}"
echo ""
echo "Your DATABASE_URL should look like:"
echo "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres?schema=public"
echo ""
echo "Example:"
echo "postgresql://postgres:mypassword@db.abcdefghijklmnop.supabase.co:5432/postgres?schema=public"
echo ""

read -p "Enter your Supabase project reference ID (from your project URL): " PROJECT_REF
read -s -p "Enter your database password: " DB_PASSWORD
echo ""

# Generate the DATABASE_URL
DATABASE_URL="postgresql://postgres:${DB_PASSWORD}@db.${PROJECT_REF}.supabase.co:5432/postgres?schema=public"

# Update .env.local file
if [ -f ".env.local" ]; then
    # Replace the DATABASE_URL line
    sed -i "s|DATABASE_URL=.*|DATABASE_URL=\"$DATABASE_URL\"|" .env.local
    echo -e "${GREEN}✅ Updated DATABASE_URL in .env.local${NC}"
else
    echo -e "${RED}❌ .env.local file not found!${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}📦 Installing required dependencies...${NC}"
npm install @supabase/supabase-js

echo ""
echo -e "${YELLOW}🗄️ Setting up database schema...${NC}"
echo "Generating Prisma client..."
npx prisma generate

echo "Pushing database schema to Supabase..."
npx prisma db push

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database schema created successfully!${NC}"
else
    echo -e "${RED}❌ Failed to create database schema. Please check your DATABASE_URL and try again.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Supabase setup complete!${NC}"
echo ""
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Set up your OAuth providers (Google, GitHub)"
echo "2. Update the NEXTAUTH_SECRET with a secure random string"
echo "3. Run 'npm run dev' to start development"
echo ""
echo -e "${YELLOW}💡 Optional: Set up Row Level Security (RLS) in Supabase:${NC}"
echo "1. Go to your Supabase Dashboard > Authentication > Settings"
echo "2. Enable Row Level Security for the tables"
echo "3. Create policies to protect user data"
echo ""

# Generate NextAuth secret
echo -e "${YELLOW}🔑 Generating NextAuth secret...${NC}"
if command -v openssl &> /dev/null; then
    SECRET=$(openssl rand -base64 32)
    sed -i "s|NEXTAUTH_SECRET=.*|NEXTAUTH_SECRET=\"$SECRET\"|" .env.local
    echo -e "${GREEN}✅ Generated and set NEXTAUTH_SECRET${NC}"
else
    echo -e "${YELLOW}⚠️ openssl not found. Please manually generate a secure secret for NEXTAUTH_SECRET${NC}"
fi

echo ""
echo -e "${GREEN}🚀 Ready to start development!${NC}"
