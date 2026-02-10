'use client';

import { ReactNode, useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { isCognitoEnabled } from '../lib/amplify-config';

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setIsReady(true);
  }, []);

  // For local development without Cognito
  if (!isCognitoEnabled || process.env.NEXT_PUBLIC_USE_MOCK_AUTH === 'true') {
    return <>{children}</>;
  }

  // Skip auth on public pages
  const publicPages = ['/login', '/signup'];
  if (publicPages.includes(pathname)) {
    return <>{children}</>;
  }

  if (!isReady) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <Authenticator
      hideSignUp={false}
      loginMechanisms={['email']}
      components={{
        Header() {
          return (
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold">Compliance Platform</h1>
              <p className="text-sm text-muted-foreground mt-2">
                Threat Risk Assessment & Management
              </p>
            </div>
          );
        },
      }}
    >
      {({ signOut, user }) => <>{children}</>}
    </Authenticator>
  );
}
