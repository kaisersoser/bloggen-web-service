# Frontend Tests

This directory contains test files and test utilities for the frontend application.

## Test Files

### Database Tests
- **`check-db.js`** - Database connectivity and schema validation test
- **`test-user-auth.js`** - User authentication and permissions test
- **`update-user-admin.js`** - User role management test/utility

### Frontend Integration Tests  
- **`ssl-test.html`** - SSL certificate and HTTPS connection test
- **`enhanced-sse-test.html`** - Enhanced Server-Sent Events test with authentication
- **`sse-browser-test.html`** - Browser-based SSE connection test
- **`sse_completion_test.html`** - SSE completion and timeout test

## Usage

### Database Tests
```bash
# Test database connectivity
node src/tests/check-db.js

# Test user authentication
node src/tests/test-user-auth.js

# Update user to admin role
node src/tests/update-user-admin.js
```

### Frontend Tests
Open the HTML files in a browser to test frontend functionality:
- SSL certificate validation
- Server-Sent Events connections
- Real-time streaming functionality

## Notes
- Database tests require Prisma client and valid DATABASE_URL
- HTML tests should be served via HTTPS for accurate testing
- All tests are designed for development/debugging purposes
