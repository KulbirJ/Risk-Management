'use client';

import { ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { 
  LayoutDashboard, 
  FileText, 
  AlertTriangle, 
  Shield, 
  History,
  Menu,
  LogOut
} from 'lucide-react';
import { useAuthenticator } from '@aws-amplify/ui-react';
import { isCognitoEnabled } from '@/lib/amplify-config';

interface LayoutProps {
  children: ReactNode;
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Assessments', href: '/assessments', icon: FileText },
  { name: 'Risk Register', href: '/active-risks', icon: AlertTriangle },
  { name: 'Audit Logs', href: '/audit-logs', icon: History },
];

export default function Layout({ children }: LayoutProps) {
  const pathname = usePathname();
  const { user, signOut } = isCognitoEnabled ? useAuthenticator((context) => [context.user]) : { user: null, signOut: null };

  const handleSignOut = () => {
    if (signOut) {
      signOut();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-200">
            <Shield className="w-8 h-8 text-primary" />
            <div>
              <h1 className="text-lg font-bold">Compliance</h1>
              <p className="text-xs text-muted-foreground">Risk Assessment</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-4 space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary text-white'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* User info and sign out */}
          <div className="p-4 border-t border-gray-200">
            {user && (
              <div className="mb-3">
                <p className="text-sm font-medium text-gray-700 truncate">
                  {user.signInDetails?.loginId || 'User'}
                </p>
              </div>
            )}
            {isCognitoEnabled && (
              <button
                onClick={handleSignOut}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Sign Out
              </button>
            )}
            {!isCognitoEnabled && (
              <div className="text-xs text-muted-foreground">
                Mock Auth Mode
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-64">
        <main className="p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
