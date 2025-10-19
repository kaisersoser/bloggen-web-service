# Frontend Dockerfile for Production Deployment
# Multi-stage build for optimal size

# Stage 1: Dependencies
FROM node:20-alpine AS deps

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Copy Prisma schema (required for prisma generate in postinstall)
COPY prisma ./prisma

# Install ALL dependencies (including devDependencies needed for build)
RUN npm ci

# Stage 2: Builder
FROM node:20-alpine AS builder

WORKDIR /app

# Accept build arguments for Next.js environment variables
ARG NEXT_PUBLIC_PROTOCOL_MODE
ARG NEXT_PUBLIC_FRONTEND_HOST
ARG NEXT_PUBLIC_FRONTEND_PORT
ARG NEXT_PUBLIC_BACKEND_HOST
ARG NEXT_PUBLIC_BACKEND_PORT
ARG NEXT_PUBLIC_API_URL

# Set them as environment variables for the build
ENV NEXT_PUBLIC_PROTOCOL_MODE=$NEXT_PUBLIC_PROTOCOL_MODE
ENV NEXT_PUBLIC_FRONTEND_HOST=$NEXT_PUBLIC_FRONTEND_HOST
ENV NEXT_PUBLIC_FRONTEND_PORT=$NEXT_PUBLIC_FRONTEND_PORT
ENV NEXT_PUBLIC_BACKEND_HOST=$NEXT_PUBLIC_BACKEND_HOST
ENV NEXT_PUBLIC_BACKEND_PORT=$NEXT_PUBLIC_BACKEND_PORT
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Generate Prisma client
RUN npx prisma generate

# Build Next.js application
RUN npm run build

# Stage 3: Runner
FROM node:20-alpine AS runner

WORKDIR /app

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy necessary files from builder
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy Prisma files
COPY --from=builder /app/node_modules/.prisma ./node_modules/.prisma
COPY --from=builder /app/prisma ./prisma

# Create logs directory with proper permissions for nextjs user
RUN mkdir -p /app/logs && chown -R nextjs:nodejs /app/logs

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Set port environment variable
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/api/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# Start application
CMD ["node", "server.js"]
