import { NextConfig } from 'next'
import fs from 'fs'
import path from 'path'

const nextConfig: NextConfig = {
  // Move serverComponentsExternalPackages to the root level
  serverExternalPackages: ['@prisma/client'],
  
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
