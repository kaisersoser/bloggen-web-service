import { NextConfig } from 'next'
import fs from 'fs'
import path from 'path'

const nextConfig: NextConfig = {
  // Move serverComponentsExternalPackages to the root level
  serverExternalPackages: ['@prisma/client'],
  
  // Image configuration for external domains
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'unsplash.com',
        port: '',
        pathname: '/**',
      },
      // Placeholder service used by OpenAI image tool fallback
      {
        protocol: 'https',
        hostname: 'placehold.co',
        port: '',
        pathname: '/**',
      },
      // Common OpenAI image blob host (may vary by region)
      {
        protocol: 'https',
        hostname: 'oaidalleapiprodscus.blob.core.windows.net',
        port: '',
        pathname: '/**',
      },
    ],
  },
  
  // HTTPS configuration for development
  ...(process.env.NODE_ENV === 'development' && {
    webpack: (config, { dev }) => {
      if (dev) {
        // HTTPS setup for development
        const certPath = path.join(process.cwd(), 'certs', 'localhost.pem')
        const keyPath = path.join(process.cwd(), 'certs', 'localhost-key.pem')
        
        if (fs.existsSync(certPath) && fs.existsSync(keyPath)) {
          console.log('🔒 HTTPS certificates found - enabling HTTPS for development')
        }
      }
      return config
    }
  })
}

export default nextConfig
