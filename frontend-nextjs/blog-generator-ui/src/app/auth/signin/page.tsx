"use client"

import { signIn, getProviders } from "next-auth/react"
import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Github, Mail } from "lucide-react"

interface Provider {
  id: string
  name: string
  type: string
  signinUrl: string
  callbackUrl: string
}

export default function SignIn() {
  const [providers, setProviders] = useState<Record<string, Provider> | null>(null)

  useEffect(() => {
    const setUpProviders = async () => {
      const response = await getProviders()
      setProviders(response)
    }
    setUpProviders()
  }, [])

  const getProviderIcon = (providerId: string) => {
    switch (providerId) {
      case 'github':
        return <Github className="w-5 h-5 mr-2" />
      case 'google':
        return <Mail className="w-5 h-5 mr-2" />
      default:
        return null
    }
  }

  const getProviderColor = (providerId: string) => {
    switch (providerId) {
      case 'github':
        return 'bg-gray-900 hover:bg-gray-800 text-white'
      case 'google':
        return 'bg-red-600 hover:bg-red-700 text-white'
      default:
        return 'bg-blue-600 hover:bg-blue-700 text-white'
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">Welcome to AI Blog Generator</CardTitle>
          <p className="text-gray-600 mt-2">Sign in to start generating amazing blogs</p>
        </CardHeader>
        <CardContent className="space-y-4">
          {providers && Object.values(providers).map((provider) => (
            <Button
              key={provider.name}
              onClick={() => signIn(provider.id, { callbackUrl: '/blog' })}
              className={`w-full flex items-center justify-center ${getProviderColor(provider.id)}`}
              variant="default"
            >
              {getProviderIcon(provider.id)}
              Sign in with {provider.name}
            </Button>
          ))}
          
          <div className="text-center text-sm text-gray-500 mt-6">
            <p>Free tier: 5 blogs per month</p>
            <p>Premium: Unlimited blogs + advanced features</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
