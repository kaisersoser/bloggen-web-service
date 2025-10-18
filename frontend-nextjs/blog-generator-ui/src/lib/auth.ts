import { NextAuthOptions } from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import GitHubProvider from "next-auth/providers/github"
import { prisma } from "@/lib/prisma"

export const authOptions: NextAuthOptions = {
  // Temporarily disable adapter to test authentication
  // adapter: PrismaAdapter(prisma) as Adapter,
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    GitHubProvider({
      clientId: process.env.GITHUB_ID!,
      clientSecret: process.env.GITHUB_SECRET!,
    }),
    // Microsoft provider can be added later
    // MicrosoftProvider({
    //   clientId: process.env.MICROSOFT_CLIENT_ID!,
    //   clientSecret: process.env.MICROSOFT_CLIENT_SECRET!,
    // }),
  ],
  session: {
    strategy: "jwt",
  },
  // Configure cookies for HTTPS in development
  cookies: {
    sessionToken: {
      name: `next-auth.session-token`,
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production' ? true : process.env.NEXTAUTH_URL?.startsWith('https://') || false
      }
    },
  },
  callbacks: {
    async jwt({ token, user }) {
      // Include user role and other custom data in JWT
      if (user) {
        // Check if user exists in database, create if not
        let dbUser = await prisma.user.findUnique({
          where: { email: user.email! },
          select: { 
            id: true, 
            role: true, 
            monthlyGenerations: true, 
            lastGenerationReset: true 
          }
        })
        
        if (!dbUser) {
          // Create new user since adapter is disabled
          dbUser = await prisma.user.create({
            data: {
              email: user.email!,
              name: user.name,
              image: user.image,
              role: 'FREE',
              monthlyGenerations: 0,
              lastGenerationReset: new Date()
            },
            select: { 
              id: true, 
              role: true, 
              monthlyGenerations: true, 
              lastGenerationReset: true 
            }
          })
        }
        
        if (dbUser) {
          token.role = dbUser.role
          token.userId = dbUser.id
          token.monthlyGenerations = dbUser.monthlyGenerations
          token.lastGenerationReset = dbUser.lastGenerationReset
        }
      }
      return token
    },
    async session({ session, token }) {
      // Add custom fields to session
      if (token) {
        session.user.id = token.userId as string
        session.user.role = token.role as string
        session.user.monthlyGenerations = token.monthlyGenerations as number
        session.user.lastGenerationReset = token.lastGenerationReset as Date
      }
      return session
    },
    async signIn() {
      // Let Prisma adapter handle user creation automatically
      // We can add custom logic here if needed, but don't manually create users
      return true
    },
    async redirect({ url, baseUrl }) {
      // Allows relative callback URLs
      if (url.startsWith("/")) return `${baseUrl}${url}`
      // Allows callback URLs on the same origin
      else if (new URL(url).origin === baseUrl) return url
      return baseUrl + '/blog'
    },
  },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
  // Add debug mode for development
  debug: process.env.NODE_ENV === 'development',
}
