import { useCallback } from 'react';
import { signIn } from 'next-auth/react';

/**
 * Hook for handling authentication-related errors and providing user guidance
 */
export function useAuthenticationErrorHandler() {
  const handleAuthError = useCallback((error: Error | string) => {
    const errorMessage = typeof error === 'string' ? error : error.message;
    
    // Check if this is an authentication error
    if (errorMessage.includes('Authentication required') || 
        errorMessage.includes('Please sign in') ||
        errorMessage.includes('Unauthorized')) {
      
      // Show a user-friendly dialog or redirect to sign in
      const shouldSignIn = window.confirm(
        'Your session has expired or you are not authenticated. Would you like to sign in now?'
      );
      
      if (shouldSignIn) {
        signIn();
        return true; // Indicate that we handled the auth error
      }
    }
    
    return false; // Indicate that this wasn't an auth error we could handle
  }, []);

  const checkAuthBeforeAction = useCallback(async (action: () => Promise<void>) => {
    try {
      await action();
    } catch (error) {
      const handled = handleAuthError(error as Error);
      if (!handled) {
        // Re-throw if it wasn't an auth error
        throw error;
      }
    }
  }, [handleAuthError]);

  return {
    handleAuthError,
    checkAuthBeforeAction
  };
}
