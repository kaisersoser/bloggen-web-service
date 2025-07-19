# Supabase Setup Guide for AI Blog Generator

## 🚀 Quick Setup Instructions

### 1. Update Environment Variables

Replace the placeholder values in your `.env.local` file with your actual Supabase credentials:

```bash
# Database - Supabase
DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres?schema=public"

# Supabase Configuration  
NEXT_PUBLIC_SUPABASE_URL="https://[YOUR-PROJECT-REF].supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="your-anon-key"
```

### 2. Finding Your Supabase Credentials

1. Go to your [Supabase Dashboard](https://app.supabase.com/)
2. Select your project
3. Go to **Settings > API**
4. Copy the following:
   - **Project URL** → `NEXT_PUBLIC_SUPABASE_URL`
   - **Project API Key (anon public)** → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
5. Go to **Settings > Database**
6. Copy your **Connection String** and modify it for `DATABASE_URL`

### 3. Database URL Format

Your `DATABASE_URL` should look like this:
```
postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres?schema=public
```

**Example:**
```
postgresql://postgres:mypassword@db.abcdefghijklmnop.supabase.co:5432/postgres?schema=public
```

### 4. Run Database Migration

```bash
# Generate Prisma client
npx prisma generate

# Push database schema to Supabase
npx prisma db push
```

### 5. Optional: Set up Row Level Security (RLS)

For production security, enable RLS in your Supabase dashboard:

1. Go to **Database > Tables**
2. For each table (`users`, `blogs`, `blog_logs`, etc.), click on the table
3. Go to **RLS** tab and enable Row Level Security
4. Add policies:

**Users table policy:**
```sql
-- Users can only access their own data
CREATE POLICY "Users can access own data" ON users
FOR ALL USING (auth.uid()::text = id);
```

**Blogs table policy:**
```sql
-- Users can only access their own blogs
CREATE POLICY "Users can access own blogs" ON blogs
FOR ALL USING (auth.uid()::text = "userId");
```

## 🔧 Manual Setup Steps

### Step 1: Update .env.local

Replace these values with your actual Supabase credentials:

```bash
# Replace [YOUR-PROJECT-REF] with your project reference
# Replace [YOUR-PASSWORD] with your database password  
# Replace your-anon-key with your actual anon key

DATABASE_URL="postgresql://postgres:YOUR_ACTUAL_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres?schema=public"
NEXT_PUBLIC_SUPABASE_URL="https://YOUR_PROJECT_REF.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="YOUR_ACTUAL_ANON_KEY"
```

### Step 2: Test Connection

Run the database push command:
```bash
npx prisma db push
```

If successful, you should see:
```
🚀 Your database is now in sync with your Prisma schema.
```

### Step 3: Verify Tables

Check your Supabase dashboard to confirm these tables were created:
- `users`
- `accounts` 
- `sessions`
- `blogs`
- `blog_logs`
- `verificationtokens`

## 🎯 OAuth Configuration

After setting up the database, configure your OAuth providers:

### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Add redirect URI: `http://localhost:3001/api/auth/callback/google`
4. Update `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`

### GitHub OAuth
1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create OAuth App
3. Set callback URL: `http://localhost:3001/api/auth/callback/github`
4. Update `GITHUB_ID` and `GITHUB_SECRET`

## 🚀 Start Development

```bash
npm run dev
```

Visit `http://localhost:3001/blog` to test authentication!

## 🔍 Troubleshooting

**Database Connection Issues:**
- Verify your DATABASE_URL is correct
- Check that your Supabase project is active
- Ensure your database password is correct

**Authentication Issues:**
- Verify OAuth redirect URIs match exactly
- Check that NEXTAUTH_URL is set correctly
- Ensure NEXTAUTH_SECRET is set to a secure random string

**Prisma Issues:**
- Run `npx prisma generate` after any schema changes
- Use `npx prisma db push` to sync schema with database
- Check `npx prisma studio` to browse your data

## 📚 Next Steps

1. **Set up OAuth providers** with real credentials
2. **Test user registration** and login flow
3. **Verify blog generation** with authenticated users
4. **Configure Row Level Security** for production
5. **Set up monitoring** in Supabase dashboard

Your authentication system is now ready with Supabase! 🎉
