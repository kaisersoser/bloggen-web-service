import { useCallback } from 'react';
import { signOut } from 'next-auth/react';

export function useAuthenticationErrorHandler() {
  const handleAuthError = useCallback((error: Error): boolean => {
    // Check if error is authentication-related
    const authErrorPatterns = [
      /unauthorized/i,
      /authentication/i,
      /401/i,
      /token.*expired/i,
      /invalid.*token/i,
      /session.*expired/i
    ];
    
    const isAuthError = authErrorPatterns.some(pattern => 
      pattern.test(error.message) || pattern.test(error.name)
    );
    
    if (isAuthError) {
      console.warn('Authentication error detected, signing out:', error.message);
      signOut({ callbackUrl: '/auth/signin' });
      return true;
    }
    
    return false;
  }, []);

  return {
    handleAuthError
  };
}