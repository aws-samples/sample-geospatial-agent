import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { 
  signIn as amplifySignIn, 
  signOut as amplifySignOut, 
  confirmSignIn,
  getCurrentUser, 
  fetchAuthSession 
} from 'aws-amplify/auth';
import { AuthUser } from 'aws-amplify/auth';
import { AuthContextType, AuthError } from './types';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [requiresNewPassword, setRequiresNewPassword] = useState(false);

  const isAuthenticated = user !== null && !requiresNewPassword;

  // Check if user is already authenticated on app load
  useEffect(() => {
    checkAuthState();
  }, []);

  const checkAuthState = async () => {
    try {
      setIsLoading(true);
      const currentUser = await getCurrentUser();
      setUser(currentUser);
    } catch (error) {
      // User is not authenticated
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const signIn = async (username: string, password: string): Promise<void> => {
    try {
      setIsLoading(true);
      
      const signInOutput = await amplifySignIn({
        username,
        password,
      });

      // Check if user needs to set a new password
      if (signInOutput.nextStep.signInStep === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
        setRequiresNewPassword(true);
        setUser(null);
        return;
      }

      if (signInOutput.isSignedIn) {
        // Get the current user after successful sign in
        const currentUser = await getCurrentUser();
        setUser(currentUser);
        setRequiresNewPassword(false);
      } else {
        throw new Error('Sign in was not completed');
      }
    } catch (error: any) {
      setUser(null);
      setRequiresNewPassword(false);
      
      // Transform Amplify errors into our AuthError format
      let authError: AuthError;
      
      if (error.name === 'NotAuthorizedException') {
        authError = {
          type: 'AUTHENTICATION',
          message: 'Invalid username or password',
          details: error
        };
      } else if (error.name === 'UserNotConfirmedException') {
        authError = {
          type: 'AUTHENTICATION',
          message: 'User account is not confirmed',
          details: error
        };
      } else if (error.name === 'UserNotFoundException') {
        authError = {
          type: 'AUTHENTICATION',
          message: 'User not found',
          details: error
        };
      } else if (error.name === 'NetworkError') {
        authError = {
          type: 'NETWORK',
          message: 'Network error occurred. Please check your connection.',
          details: error
        };
      } else {
        authError = {
          type: 'UNKNOWN',
          message: error.message || 'An unexpected error occurred',
          details: error
        };
      }
      
      throw authError;
    } finally {
      setIsLoading(false);
    }
  };

  const completeNewPassword = async (newPassword: string): Promise<void> => {
    try {
      setIsLoading(true);
      
      const confirmOutput = await confirmSignIn({
        challengeResponse: newPassword,
      });

      if (confirmOutput.isSignedIn) {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
        setRequiresNewPassword(false);
      } else {
        throw new Error('Password change was not completed');
      }
    } catch (error: any) {
      let authError: AuthError;
      
      if (error.name === 'InvalidPasswordException') {
        authError = {
          type: 'VALIDATION',
          message: 'Password does not meet requirements',
          details: error
        };
      } else if (error.name === 'NotAuthorizedException') {
        authError = {
          type: 'AUTHENTICATION',
          message: 'Session expired. Please sign in again.',
          details: error
        };
      } else {
        authError = {
          type: 'UNKNOWN',
          message: error.message || 'Failed to set new password',
          details: error
        };
      }
      
      throw authError;
    } finally {
      setIsLoading(false);
    }
  };

  const signOut = async (): Promise<void> => {
    try {
      setIsLoading(true);
      await amplifySignOut();
      setUser(null);
    } catch (error: any) {
      // Even if sign out fails, clear the local user state
      setUser(null);
      
      const authError: AuthError = {
        type: 'UNKNOWN',
        message: error.message || 'Error occurred during sign out',
        details: error
      };
      
      throw authError;
    } finally {
      setIsLoading(false);
    }
  };

  const getAccessToken = async (): Promise<string> => {
    try {
      const session = await fetchAuthSession();
      
      if (!session.tokens?.accessToken) {
        throw new Error('No access token available');
      }
      
      return session.tokens.accessToken.toString();
    } catch (error: any) {
      const authError: AuthError = {
        type: 'AUTHENTICATION',
        message: 'Failed to get access token',
        details: error
      };
      
      throw authError;
    }
  };

  const contextValue: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    requiresNewPassword,
    signIn,
    signOut,
    completeNewPassword,
    getAccessToken,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;