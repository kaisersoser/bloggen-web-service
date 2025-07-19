"use client"

import { useSession, signOut } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Crown, User, LogOut } from "lucide-react"
import { useUserStats } from "@/hooks/useUserStats"

export function UserProfile() {
  const { data: session, status } = useSession()
  const { stats, loading: statsLoading } = useUserStats()

  if (status === "loading") {
    return (
      <div className="animate-pulse">
        <div className="h-20 bg-gray-200 rounded-lg"></div>
      </div>
    )
  }

  if (!session) {
    return null
  }

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'PREMIUM':
        return <Crown className="w-4 h-4 text-yellow-500" />
      case 'ADMIN':
        return <Crown className="w-4 h-4 text-purple-500" />
      default:
        return <User className="w-4 h-4 text-gray-500" />
    }
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'PREMIUM':
        return 'bg-yellow-100 text-yellow-800'
      case 'ADMIN':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Profile</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center space-x-3">
          <Avatar className="w-12 h-12">
            <AvatarImage src={session.user.image || undefined} alt={session.user.name || 'User'} />
            <AvatarFallback>
              {session.user.name?.charAt(0) || session.user.email?.charAt(0) || 'U'}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <p className="font-semibold">{session.user.name}</p>
            <p className="text-sm text-gray-600">{session.user.email}</p>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {getRoleIcon(session.user.role)}
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleBadgeColor(session.user.role)}`}>
              {session.user.role}
            </span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>This month:</span>
            <span>
              {statsLoading ? (
                "Loading..."
              ) : stats ? (
                `${stats.monthlyGenerations} generations`
              ) : (
                `${session.user.monthlyGenerations} generations`
              )}
            </span>
          </div>
          
          {session.user.role === 'FREE' && (
            <div className="flex justify-between text-sm">
              <span>Remaining:</span>
              <span>
                {statsLoading ? (
                  "Loading..."
                ) : stats ? (
                  `${stats.remainingGenerations} / ${stats.monthlyLimit}`
                ) : (
                  `${Math.max(0, 50 - session.user.monthlyGenerations)} / 50`
                )}
              </span>
            </div>
          )}
        </div>

        <Button 
          onClick={() => signOut()} 
          variant="outline" 
          className="w-full"
        >
          <LogOut className="w-4 h-4 mr-2" />
          Sign Out
        </Button>
      </CardContent>
    </Card>
  )
}
