"use client"

import { useSearchParams } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertCircle } from "lucide-react"
import Link from "next/link"

const errors = {
  Configuration: "There is a problem with the server configuration.",
  AccessDenied: "You do not have permission to sign in.",
  Verification: "The verification token has expired or has already been used.",
  Default: "An error occurred during authentication."
}

export default function AuthError() {
  const searchParams = useSearchParams()
  const error = searchParams.get('error')
  const errorMessage = errors[error as keyof typeof errors] || errors.Default

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <AlertCircle className="w-12 h-12 text-red-500" />
          </div>
          <CardTitle className="text-2xl font-bold text-red-600">Authentication Error</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-center">
          <p className="text-gray-600">{errorMessage}</p>
          
          <div className="space-y-2">
            <Button asChild className="w-full">
              <Link href="/auth/signin">Try Again</Link>
            </Button>
            
            <Button asChild variant="outline" className="w-full">
              <Link href="/">Go Home</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
