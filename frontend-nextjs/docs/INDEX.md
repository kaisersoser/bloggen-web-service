# Frontend Documentation Index

This directory contains **frontend-specific documentation** for the Next.js blog generation UI.

## 🎨 Frontend Documentation

### Core Frontend Documentation
- [`FRONTEND_README.md`](./FRONTEND_README.md) - Frontend architecture, setup, and development guide
- [`SSE_RESILIENCE_UPDATES.md`](../blog-generator-ui/src/docs/SSE_RESILIENCE_UPDATES.md) - Adaptive streaming retries and connection telemetry (Priority 2)

## 🏗️ Frontend Architecture Overview

The frontend is built with:
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **NextAuth.js** - Authentication system
- **Prisma ORM** - Database integration
- **Tailwind CSS** - Styling framework
- **shadcn/ui** - UI component library

### Key Frontend Components
- **Authentication**: NextAuth.js with JWT tokens
- **Blog Generation**: Real-time SSE streaming interface
- **User Management**: Role-based access (FREE/PREMIUM/ADMIN)
- **Blog History**: User blog management and viewing
- **Responsive UI**: Mobile-first design

## 📁 Frontend Structure

```
frontend-nextjs/blog-generator-ui/
├── src/
│   ├── app/              # Next.js App Router pages
│   ├── components/       # Reusable UI components
│   ├── hooks/           # Custom React hooks
│   ├── lib/             # Utilities and services
│   ├── types/           # TypeScript type definitions
│   └── styles/          # Global styles
├── prisma/              # Database schema and migrations
├── public/              # Static assets
└── docs/               # Frontend documentation (this directory)
```

## 🔗 Related Documentation

- **Project-Wide Docs**: [`../../docs/`](../../docs/) - Authentication setup, deployment, and full-stack configuration
- **Backend Docs**: [`../../backend/docs/`](../../backend/docs/) - Backend API and system documentation
- **Main README**: [`../../README.md`](../../README.md) - Project overview and getting started

## 📋 Quick Reference

### Development Commands
```bash
# Start development server
npm run dev

# Build for production
npm run build

# Database operations
npx prisma db push
npx prisma studio
```

### Key Frontend Features
- **Real-time Updates**: SSE streaming for blog generation progress
- **Authentication**: Google and GitHub OAuth integration
- **Blog Management**: Create, view, and manage generated blogs
- **User Roles**: Different access levels and generation limits
- **Responsive Design**: Works on desktop and mobile devices

### Environment Variables
See project-wide authentication setup in [`../../docs/AUTH_SETUP.md`](../../docs/AUTH_SETUP.md) for required environment variables.

## 🧪 Testing

Frontend testing and debugging information can be found in the backend test directory at [`../../backend/src/tests/`](../../backend/src/tests/) for integration tests between frontend and backend.
