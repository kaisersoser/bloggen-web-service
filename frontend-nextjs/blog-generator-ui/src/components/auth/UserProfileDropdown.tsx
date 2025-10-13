"use client"

import { useState, useRef, useEffect } from "react"
import { useSession, signOut } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Crown, User, LogOut, Sun, Moon, Monitor, BarChart3, Activity } from "lucide-react"
import { useUserStats } from "@/hooks/useUserStats"

type ThemeMode = 'light' | 'dark' | 'system'

interface UserProfileDropdownProps {
  themeMode?: ThemeMode
  onThemeChange?: (theme: ThemeMode) => void
}

export function UserProfileDropdown({ themeMode = 'light', onThemeChange }: UserProfileDropdownProps) {
  const { data: session, status } = useSession()
  const { stats, loading: statsLoading } = useUserStats()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  if (status === "loading") {
    return (
      <div className="animate-pulse">
        <div className="h-8 w-8 bg-gray-200 rounded-full"></div>
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

  const getThemeIcon = (theme: ThemeMode) => {
    switch (theme) {
      case 'light':
        return <Sun className="w-4 h-4" />
      case 'dark':
        return <Moon className="w-4 h-4" />
      default:
        return <Monitor className="w-4 h-4" />
    }
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Profile Avatar - Clickable */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      >
        <Avatar className="w-8 h-8">
          <AvatarImage src={session.user.image || undefined} alt={session.user.name || 'User'} />
          <AvatarFallback className="text-sm">
            {session.user.name?.charAt(0) || session.user.email?.charAt(0) || 'U'}
          </AvatarFallback>
        </Avatar>
      </button>

      {/* Dropdown Profile Modal */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-80 z-50">
          <Card className="shadow-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-gray-900 dark:text-gray-100">Profile</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* User Info */}
              <div className="flex items-center space-x-3">
                <Avatar className="w-12 h-12">
                  <AvatarImage src={session.user.image || undefined} alt={session.user.name || 'User'} />
                  <AvatarFallback>
                    {session.user.name?.charAt(0) || session.user.email?.charAt(0) || 'U'}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <p className="font-semibold text-gray-900 dark:text-gray-100">{session.user.name}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{session.user.email}</p>
                </div>
              </div>

              {/* Role Badge */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {getRoleIcon(session.user.role)}
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleBadgeColor(session.user.role)}`}>
                    {session.user.role}
                  </span>
                </div>
              </div>

              {/* Stats */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">This month:</span>
                  <span className="text-gray-900 dark:text-gray-100">
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
                    <span className="text-gray-600 dark:text-gray-400">Remaining:</span>
                    <span className="text-gray-900 dark:text-gray-100">
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

              {/* Theme Selection */}
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">Theme</p>
                <div className="flex space-x-1">
                  {(['light', 'dark', 'system'] as ThemeMode[]).map((theme) => (
                    <button
                      key={theme}
                      onClick={() => onThemeChange?.(theme)}
                      className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm transition-colors ${
                        themeMode === theme
                          ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                      }`}
                    >
                      {getThemeIcon(theme)}
                      <span className="capitalize">{theme}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Admin Dashboard Link - Only for ADMIN users */}
              {session.user.role === 'ADMIN' && (
                <>
                  <Button 
                    onClick={() => {
                      setIsOpen(false)
                      window.open('/admin/audit', '_blank')
                    }} 
                    variant="outline" 
                    className="w-full mb-2"
                  >
                    <BarChart3 className="w-4 h-4 mr-2" />
                    Cost Analytics
                  </Button>
                  <Button 
                    onClick={() => {
                      setIsOpen(false)
                      window.open('/admin/monitoring', '_blank')
                    }} 
                    variant="outline" 
                    className="w-full mb-2"
                  >
                    <Activity className="w-4 h-4 mr-2" />
                    System Health
                  </Button>
                </>
              )}

              {/* Sign Out Button */}
              <Button 
                onClick={() => {
                  setIsOpen(false)
                  signOut()
                }} 
                variant="outline" 
                className="w-full"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Sign Out
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
