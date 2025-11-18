# Frontend Documentation

Welcome to the AI Blog Generator Frontend documentation. This directory contains all documentation related to the Next.js frontend application.

## 📚 Documentation Structure

### 🏗️ [Architecture](./architecture/)
Design decisions, code structure, and architectural patterns.

- **[CODE_ANALYSIS.md](./architecture/CODE_ANALYSIS.md)** - Comprehensive codebase analysis and structure
- **[ORGANIZATION_SUMMARY.md](./architecture/ORGANIZATION_SUMMARY.md)** - Component organization and file structure
- **[OPTIMIZATION_REQUIREMENTS.md](./architecture/OPTIMIZATION_REQUIREMENTS.md)** - Performance requirements and optimization strategies

### ✨ [Features](./features/)
Feature-specific documentation and implementation details.

- **[AGENT_FLOW_IMPLEMENTATION_PLAN.md](./features/AGENT_FLOW_IMPLEMENTATION_PLAN.md)** - ⭐ Interactive agent workflow visualization (NEW)
- **[PAGE_REFRESH_RECOVERY.md](./features/PAGE_REFRESH_RECOVERY.md)** - State persistence across page refreshes
- **[PERFORMANCE_ENHANCEMENTS.md](./features/PERFORMANCE_ENHANCEMENTS.md)** - Performance optimizations and improvements
- **[SSE_RESILIENCE.md](./features/SSE_RESILIENCE.md)** - Server-Sent Events connection handling and resilience
- **[SSE_ENHANCEMENTS.md](./features/SSE_ENHANCEMENTS.md)** - Real-time update enhancements
- **[LOGGING_CONFIGURATION.md](./features/LOGGING_CONFIGURATION.md)** - Debug logging and verbose mode configuration
- **[CONSOLE_DELAY_FIX.md](./features/CONSOLE_DELAY_FIX.md)** - Console rendering delay fixes
- **[NOTIFICATION_SYSTEM.md](./features/NOTIFICATION_SYSTEM.md)** - Toast notification system implementation
- **[NOTIFICATION_TESTING.md](./features/NOTIFICATION_TESTING.md)** - Notification system testing plan
- **[GRAPH_OPTIMIZATION.md](./features/GRAPH_OPTIMIZATION.md)** - Performance graph optimizations
- **[SMOOTH_GRAPH_UPDATES.md](./features/SMOOTH_GRAPH_UPDATES.md)** - Smooth animation and graph transitions

### � [Guides](./guides/)
Setup, debugging, and development guides.

- **[DEBUG_SETUP.md](./guides/DEBUG_SETUP.md)** - Local development and debugging setup
- **[DEBUG_GUIDE.md](./guides/DEBUG_GUIDE.md)** - Comprehensive debugging guide
- **[DEBUG_STEPS.md](./guides/DEBUG_STEPS.md)** - Step-by-step debugging procedures
- **[HTTPS_SETUP.md](./guides/HTTPS_SETUP.md)** - Local HTTPS development setup
- **[SSL_CERTIFICATE_TRUST.md](./guides/SSL_CERTIFICATE_TRUST.md)** - SSL certificate installation and trust
- **[ENV_CONSOLIDATION.md](./guides/ENV_CONSOLIDATION.md)** - Environment variable consolidation and management

### � [Archive](./archive/)
Historical documentation from completed phases and old reports.

- **[DAY_1_COMPLETION.md](./archive/DAY_1_COMPLETION.md)** - Day 1 milestone report
- **[PHASE_1_COMPLETED.md](./archive/PHASE_1_COMPLETED.md)** - Phase 1 completion report
- **[PHASE_1_IMPLEMENTATION.md](./archive/PHASE_1_IMPLEMENTATION.md)** - Phase 1 implementation details
- **[PHASE_4_INTEGRATION.md](./archive/PHASE_4_INTEGRATION.md)** - Phase 4 frontend integration report
- **[REGRESSION_FIXES.md](./archive/REGRESSION_FIXES.md)** - Historical regression fixes
- **[UNIFIED_OPTIMIZATION_REPORT.md](./archive/UNIFIED_OPTIMIZATION_REPORT.md)** - Unified optimization completion report
- **[ISSUES_FIX.md](./archive/ISSUES_FIX.md)** - Frontend issues resolution history
- **[CLEANUP_REPORT.md](./archive/CLEANUP_REPORT.md)** - Code cleanup and refactoring report

---

## 🚀 Quick Start

### Development Setup
```bash
cd frontend-nextjs/blog-generator-ui
npm install
npm run dev  # Runs HTTPS by default
```

See [DEBUG_SETUP.md](./guides/DEBUG_SETUP.md) for comprehensive setup instructions.

### HTTPS Development
For local HTTPS development (required for OAuth and production-like testing):
```bash
npm run dev      # HTTPS mode (default)
npm run dev:http # HTTP fallback for debugging only
```

See [HTTPS_SETUP.md](./guides/HTTPS_SETUP.md) for SSL certificate setup.

---

## 📝 Contributing

When adding new documentation:
1. Place it in the appropriate category folder (`architecture/`, `features/`, `guides/`, or `archive/`)
2. Update this README with a link to the new document
3. Follow the existing naming conventions (use underscores, all caps for doc names)
4. Add a brief description of the document's purpose

---

## 🔗 Related Documentation

- **Backend Documentation**: See `backend/docs/` for backend-related documentation
- **Project Documentation**: See project root `docs/` for deployment, authentication, and cross-cutting concerns
- **GitHub Copilot Instructions**: See `.github/copilot-instructions.md` for AI assistant guidelines

---

## 📊 Documentation Stats

**Total Documents**: 27
- **Architecture**: 3 documents
- **Features**: 11 documents (1 new implementation plan)
- **Guides**: 6 documents
- **Archive**: 8 documents

**Last Updated**: January 21, 2025
