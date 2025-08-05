# CrewAI Blog Generation Service

A sophisticated AI-powered blog generation service using CrewAI multi-agent workflows, Next.js frontend, and real-time streaming capabilities.

## 🚀 **Quick Start**

For detailed setup instructions, see our comprehensive documentation in the [`docs/`](docs/) folder:

- **[📚 Complete Documentation](docs/README.md)** - Full documentation index
- **[🚀 Deployment Guide](docs/DEPLOYMENT.md)** - Step-by-step deployment
- **[⚙️ Backend Setup](docs/BACKEND_README.md)** - Backend configuration
- **[🎨 Frontend Setup](docs/FRONTEND_README.md)** - Frontend configuration
- **[🔐 Authentication](docs/AUTHENTICATION.md)** - Auth system setup

## 🏗️ **Architecture Overview**

```
CrewAI Blog Generation Service
├── 🐍 Backend (Python Flask + CrewAI Flows)
│   ├── Real-time blog generation with AI agents
│   ├── SSE streaming for progress updates
│   ├── Cost tracking and audit logging
│   └── RESTful API with authentication
├── ⚛️ Frontend (Next.js 14 + TypeScript)
│   ├── Modern React UI with Tailwind CSS
│   ├── Real-time progress tracking
│   ├── User authentication with NextAuth.js
│   └── Responsive design with shadcn/ui
└── 🗄️ Database Layer
    ├── PostgreSQL (user management via Prisma)
    ├── ChromaDB (vector storage)
    └── Audit logging system
```

## ✨ **Key Features**

- **🤖 Multi-Agent AI System**: Research → Content → Fact-Check → Finalize
- **📡 Real-time Streaming**: SSE-based progress updates
- **🔐 Authentication**: Role-based access (FREE/PREMIUM/ADMIN)
- **🖼️ Image Integration**: Automatic Unsplash image insertion
- **💰 Cost Tracking**: Comprehensive LLM usage monitoring
- **🔒 HTTPS Security**: Production-ready security configuration

## 📁 **Project Structure**

```
bloggen-web-service/
├── 📚 docs/                    # 📚 All documentation organized here
│   ├── README.md              # Documentation index
│   ├── DEPLOYMENT.md          # Deployment guide
│   ├── BACKEND_README.md      # Backend setup
│   ├── FRONTEND_README.md     # Frontend setup
│   ├── AUTHENTICATION.md      # Auth configuration
│   ├── HTTPS_SECURITY.md      # Security setup
│   ├── UNSPLASH_SETUP.md      # Image integration
│   ├── COST_TRACKING.md       # Cost monitoring
│   └── EFFICIENCY_SUMMARY.md  # Performance improvements
├── 🐍 backend/                 # Python Flask + CrewAI backend
│   ├── src/
│   │   ├── core/              # 🔧 Unified utilities & config
│   │   ├── bloggen/           # 🤖 CrewAI flows & agents
│   │   ├── main.py            # 🚀 Flask application
│   │   └── api.py             # 📡 REST API endpoints
│   └── requirements.txt
├── ⚛️ frontend-nextjs/         # Next.js 14 + TypeScript frontend
│   └── blog-generator-ui/
│       ├── src/
│       │   ├── app/           # 📄 Next.js app router
│       │   ├── components/    # 🎨 React components
│       │   ├── lib/           # 🔧 Utilities & services
│       │   └── hooks/         # 🪝 Custom React hooks
│       └── prisma/            # 🗄️ Database schema
├── 🐳 docker-compose.yml      # Container orchestration
├── 🔧 Makefile               # Development commands
└── 📋 README.md              # This file
```

## 🛠️ **Development**

### **Quick Commands**
```bash
# Install everything and start development
make install && make dev

# Backend only
make backend-dev

# Frontend only  
make frontend-dev

# Full production deployment
make deploy
```

### **Environment Setup**
```bash
# Copy environment template
cp .env.example .env

# Configure your API keys and database settings
# See docs/DEPLOYMENT.md for detailed configuration
```

## 📚 **Documentation**

All detailed documentation is organized in the [`docs/`](docs/) folder:

| Document | Description |
|----------|-------------|
| **[📚 Documentation Index](docs/README.md)** | Complete documentation overview |
| **[🚀 Deployment Guide](docs/DEPLOYMENT.md)** | Step-by-step deployment instructions |
| **[⚙️ Backend Setup](docs/BACKEND_README.md)** | Backend development setup |
| **[🎨 Frontend Setup](docs/FRONTEND_README.md)** | Frontend development setup |
| **[🔐 Authentication](docs/AUTHENTICATION.md)** | Authentication system configuration |
| **[🔒 HTTPS Security](docs/HTTPS_SECURITY.md)** | Production security setup |
| **[🖼️ Unsplash Integration](docs/UNSPLASH_SETUP.md)** | Image integration setup |
| **[💰 Cost Tracking](docs/COST_TRACKING.md)** | LLM cost monitoring system |

## 🤝 **Contributing**

1. **Review Documentation**: Start with [`docs/README.md`](docs/README.md)
2. **Follow Setup Guides**: Use component-specific setup guides
3. **Check Architecture**: Understand the multi-agent system design
4. **Test Thoroughly**: Validate changes across all components

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 **Support**

- **Documentation**: [`docs/`](docs/) folder contains comprehensive guides
- **Issues**: GitHub Issues for bug reports and feature requests
- **Architecture Questions**: Review [`docs/COPILOT_INSTRUCTIONS.md`](docs/COPILOT_INSTRUCTIONS.md)

---

**🚀 Ready to build amazing AI-powered blogs? Start with [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)!**