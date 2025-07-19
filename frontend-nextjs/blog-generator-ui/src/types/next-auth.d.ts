import { DefaultSession, DefaultUser } from "next-auth"
import { JWT, DefaultJWT } from "next-auth/jwt"

declare module "next-auth" {
  interface Session {
    user: {
      id: string
      role: string
      monthlyGenerations: number
      lastGenerationReset: Date
    } & DefaultSession["user"]
  }

  interface User extends DefaultUser {
    role: string
    monthlyGenerations: number
    lastGenerationReset: Date
  }
}

declare module "next-auth/jwt" {
  interface JWT extends DefaultJWT {
    userId: string
    role: string
    monthlyGenerations: number
    lastGenerationReset: Date
  }
}
