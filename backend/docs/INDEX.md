# Backend Documentation Index

This directory contains **backend-specific documentation** for the CrewAI Blog Generation Service backend components.

## 🏗️ Backend Documentation

### Core System Documentation
- [`BACKEND_README.md`](./BACKEND_README.md) - Backend architecture and setup guide
- [`DATABASE_AUDIT_IMPLEMENTATION.md`](./DATABASE_AUDIT_IMPLEMENTATION.md) - Database audit system implementation
- [`SSE_STATUS_REPORT.md`](./SSE_STATUS_REPORT.md) - Server-Sent Events implementation status

### Cost Tracking & Performance
- [`COST_TRACKING.md`](./COST_TRACKING.md) - API cost tracking system overview
- [`COST_TRACKING_AUDIT.md`](./COST_TRACKING_AUDIT.md) - Cost tracking audit implementation
- [`EFFICIENCY_IMPROVEMENTS.md`](./EFFICIENCY_IMPROVEMENTS.md) - Backend performance improvements
- [`EFFICIENCY_SUMMARY.md`](./EFFICIENCY_SUMMARY.md) - Performance optimization summary

### Code Quality & Cleanup
- [`BACKEND_CLEANUP_SUMMARY.md`](./BACKEND_CLEANUP_SUMMARY.md) - Backend directory cleanup report
- [`UNUSED_FILES_ANALYSIS.md`](./UNUSED_FILES_ANALYSIS.md) - Unused file analysis and removal report

## 🧪 Testing

Backend tests are located in [`../src/tests/`](../src/tests/) and include:
- Audit system tests
- Integration tests
- Performance benchmarks
- Schema compatibility tests
- Frontend integration tests

## 🔗 Related Documentation

- **Project-Wide Docs**: [`../../docs/`](../../docs/) - Authentication, deployment, and full-stack setup
- **Frontend Docs**: [`../../frontend-nextjs/docs/`](../../frontend-nextjs/docs/) - Frontend-specific documentation
- **Source Code**: [`../src/`](../src/) - Backend source code

## 📋 Quick Reference

### Key Backend Components
- **API Layer**: Flask/FastAPI endpoints in `src/api.py` and `src/main.py`
- **Core Infrastructure**: Database, audit tracking, and LLM interceptors in `src/core/`
- **Blog Generation**: CrewAI flows and agent orchestration in `src/bloggen/`
- **Tools**: Custom tools for image integration and content enhancement

### Development
- **Environment Setup**: See [`BACKEND_README.md`](./BACKEND_README.md)
- **Testing**: Run tests from `src/tests/` directory
- **Debugging**: Use audit system diagnostic tools in `src/tests/`
