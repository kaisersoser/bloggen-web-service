#!/bin/bash
# Switch to HTTPS mode for both frontend and backend

echo "🔒 Switching to HTTPS mode..."

# Update .env.protocol
sed -i 's/PROTOCOL_MODE=http/PROTOCOL_MODE=https/' .env.protocol

# Update frontend .env.local
cd frontend-nextjs/blog-generator-ui
sed -i 's/NEXT_PUBLIC_PROTOCOL_MODE=http/NEXT_PUBLIC_PROTOCOL_MODE=https/' .env.local
sed -i 's|NEXTAUTH_URL="http://|NEXTAUTH_URL="https://|' .env.local
sed -i 's|API_BASE_URL="http://|API_BASE_URL="https://|' .env.local
sed -i 's|NEXT_PUBLIC_API_URL="http://|NEXT_PUBLIC_API_URL="https://|' .env.local

cd ../..

echo "✅ Switched to HTTPS mode"
echo "📋 Frontend: https://localhost:3001"
echo "📋 Backend: https://localhost:5000"
echo ""
echo "🚀 Start servers with:"
echo "   Backend: cd backend/src && python main.py"
echo "   Frontend: cd frontend-nextjs/blog-generator-ui && npm run dev"
