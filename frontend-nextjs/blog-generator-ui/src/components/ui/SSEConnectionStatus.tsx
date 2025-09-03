import { useSession } from 'next-auth/react';
import { AlertCircle, CheckCircle, Loader2, WifiOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { signIn, signOut } from 'next-auth/react';

interface SSEConnectionStatusProps {
  isConnected?: boolean;
  isConnecting?: boolean;
  error?: string | null;
  onRetry?: () => void;
  className?: string;
}

export function SSEConnectionStatus({ 
  isConnected = false, 
  isConnecting = false, 
  error = null,
  onRetry,
  className = '' 
}: SSEConnectionStatusProps) {
  const { status } = useSession();

  // Don't show anything if there's no active task
  if (!isConnecting && !isConnected && !error) {
    return null;
  }

  // Authentication error handling
  if (status === 'unauthenticated' || (error && error.includes('sign'))) {
    return (
      <div className={`flex items-center gap-2 px-3 py-2 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-md text-sm ${className}`}>
        <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
        <span className="text-amber-800 dark:text-amber-200">Authentication required for real-time updates</span>
        <Button 
          size="sm" 
          variant="outline" 
          onClick={() => signIn()}
          className="ml-auto"
        >
          Sign In
        </Button>
      </div>
    );
  }

  // Session expired error
  if (error && (error.includes('expired') || error.includes('401'))) {
    return (
      <div className={`flex items-center gap-2 px-3 py-2 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-md text-sm ${className}`}>
        <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" />
        <span className="text-red-800 dark:text-red-200">Session expired</span>
        <Button 
          size="sm" 
          variant="outline" 
          onClick={() => {
            signOut({ redirect: false }).then(() => signIn());
          }}
          className="ml-auto"
        >
          Sign In Again
        </Button>
      </div>
    );
  }

  // Connection error with retry
  if (error) {
    return (
      <div className={`flex items-center gap-2 px-3 py-2 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-md text-sm ${className}`}>
        <WifiOff className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" />
        <span className="text-red-800 dark:text-red-200 flex-1">{error}</span>
        {onRetry && (
          <Button 
            size="sm" 
            variant="outline" 
            onClick={onRetry}
            className="ml-2"
          >
            Retry
          </Button>
        )}
      </div>
    );
  }

  // Connecting state
  if (isConnecting) {
    return (
      <div className={`flex items-center gap-2 px-3 py-2 bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-md text-sm ${className}`}>
        <Loader2 className="w-4 h-4 text-blue-600 dark:text-blue-400 animate-spin flex-shrink-0" />
        <span className="text-blue-800 dark:text-blue-200">Connecting to real-time updates...</span>
      </div>
    );
  }

  // Connected state
  if (isConnected) {
    return (
      <div className={`flex items-center gap-2 px-3 py-2 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800 rounded-md text-sm ${className}`}>
        <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0" />
        <span className="text-green-800 dark:text-green-200">Real-time updates connected</span>
      </div>
    );
  }

  return null;
}
