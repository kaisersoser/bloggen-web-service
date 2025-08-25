#!/bin/bash
# Switch to HTTP mode for both frontend and backend

echo "🔓 Switching to HTTP mode..."

# Update .env.protocol
sed -i 's/PROTOCOL_MODE=https/PROTOCOL_MODE=http/' .env.protocol

# Update frontend .env.local
cd frontend-nextjs/blog-generator-ui
sed -i 's/NEXT_PUBLIC_PROTOCOL_MODE=https/NEXT_PUBLIC_PROTOCOL_MODE=http/' .env.local
sed -i 's|NEXTAUTH_URL="https://|NEXTAUTH_URL="http://|' .env.local
sed -i 's|API_BASE_URL="https://|API_BASE_URL="http://|' .env.local
sed -i 's|NEXT_PUBLIC_API_URL="https://|NEXT_PUBLIC_API_URL="http://|' .env.local

cd ../..

echo "✅ Switched to HTTP mode"
echo "📋 Frontend: http://localhost:3001"
echo "📋 Backend: http://localhost:5000"
echo ""
echo "🚀 Start servers with:"
echo "   Backend: cd backend/src && python main.py"
echo "   Frontend: cd frontend-nextjs/blog-generator-ui && npm run dev"
