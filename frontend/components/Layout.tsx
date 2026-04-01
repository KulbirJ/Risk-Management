'use client';

import { ReactNode, useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import {
  LayoutDashboard,
  FileText,
  AlertTriangle,
  History,
  Menu,
  LogOut,
  Brain,
  ClipboardCheck,
  Sun,
  Moon,
  Monitor,
  PanelLeftClose,
  PanelLeftOpen,
  X,
  Package,
} from 'lucide-react';
import { useAuthenticator } from '@aws-amplify/ui-react';
import { isCognitoEnabled } from '../lib/amplify-config';
import { useTheme } from './ThemeProvider';
import { usePipeline } from './PipelineContext';
import { PipelineNavIndicator } from './PipelineProgressBar';

interface LayoutProps {
  children: ReactNode;
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Assessments', href: '/assessments', icon: FileText },
  { name: 'Intelligence', href: '/intelligence', icon: Brain },
  { name: 'Compliance', href: '/compliance', icon: ClipboardCheck },
  { name: 'Supply Chain', href: '/supply-chain', icon: Package },
  { name: 'Risk Register', href: '/active-risks', icon: AlertTriangle },
  { name: 'Audit Logs', href: '/audit-logs', icon: History },
];

export default function Layout({ children }: LayoutProps) {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const { pipelines } = usePipeline();
  const { user, signOut } = isCognitoEnabled
    ? useAuthenticator((context) => [context.user])
    : { user: null, signOut: null };

  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Restore collapsed state from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('sidebar-collapsed');
    if (stored === 'true') setCollapsed(true);
  }, []);

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const toggleCollapsed = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem('sidebar-collapsed', String(next));
  };

  const handleSignOut = () => {
    if (signOut) signOut();
  };

  const cycleTheme = () => {
    const order: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system'];
    const idx = order.indexOf(theme);
    setTheme(order[(idx + 1) % order.length]);
  };

  const themeIcon =
    theme === 'dark' ? Moon : theme === 'light' ? Sun : Monitor;
  const ThemeIcon = themeIcon;

  const sidebarW = collapsed ? 'w-[72px]' : 'w-64';

  return (
    <div className="min-h-screen bg-background transition-colors duration-300">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile top bar */}
      <div className="sticky top-0 z-30 flex items-center gap-3 px-4 py-3 bg-sidebar text-sidebar-foreground border-b border-sidebar-border lg:hidden">
        <button
          onClick={() => setMobileOpen(true)}
          className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
          aria-label="Open navigation"
        >
          <Menu className="w-5 h-5" />
        </button>
        <Image
          src="/logo.png"
          alt="EdgeVision"
          width={130}
          height={36}
          className="object-contain"
          priority
        />
      </div>

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 ${sidebarW} bg-gradient-to-b from-slate-900 via-slate-900 to-slate-800 text-slate-100 transition-all duration-300 ease-in-out flex flex-col
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}
      >
        {/* Logo area */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-white/10">
          {!collapsed && (
            <Image
              src="/logo.png"
              alt="EdgeVision — Intelligent Analytics & Insights"
              width={160}
              height={44}
              className="object-contain"
              priority
            />
          )}
          {/* Mobile close */}
          <button
            onClick={() => setMobileOpen(false)}
            className="p-1.5 rounded-lg hover:bg-white/10 transition-colors lg:hidden"
            aria-label="Close navigation"
          >
            <X className="w-5 h-5" />
          </button>
          {/* Desktop collapse toggle */}
          <button
            onClick={toggleCollapsed}
            className="hidden lg:flex p-1.5 rounded-lg hover:bg-white/10 transition-colors"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <PanelLeftOpen className="w-5 h-5" />
            ) : (
              <PanelLeftClose className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== '/' && pathname.startsWith(item.href));
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                title={collapsed ? item.name : undefined}
                className={`group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-primary/20 text-white shadow-sm border-l-[3px] border-primary -ml-[3px]'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                } ${collapsed ? 'justify-center' : ''}`}
              >
                <Icon className={`w-5 h-5 shrink-0 ${isActive ? 'text-primary' : ''}`} />
                {!collapsed && <span>{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Active pipeline indicators */}
        {!collapsed && <PipelineNavIndicator pipelines={pipelines} />}

        {/* Footer */}
        <div className="p-3 border-t border-white/10 space-y-2">
          {/* Theme toggle */}
          <button
            onClick={cycleTheme}
            className={`flex items-center gap-3 w-full px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-all duration-200 ${
              collapsed ? 'justify-center' : ''
            }`}
            title={`Theme: ${theme}`}
            aria-label={`Switch theme (current: ${theme})`}
          >
            <ThemeIcon className="w-5 h-5 shrink-0" />
            {!collapsed && (
              <span className="capitalize">{theme} mode</span>
            )}
          </button>

          {/* User info */}
          {user && !collapsed && (
            <div className="px-3 py-1">
              <p className="text-xs font-medium text-slate-400 truncate">
                {user.signInDetails?.loginId || 'User'}
              </p>
            </div>
          )}

          {/* Sign out */}
          {isCognitoEnabled && (
            <button
              onClick={handleSignOut}
              className={`flex items-center gap-3 w-full px-3 py-2 text-sm text-slate-400 hover:text-red-400 hover:bg-white/5 rounded-xl transition-all duration-200 ${
                collapsed ? 'justify-center' : ''
              }`}
              title={collapsed ? 'Sign Out' : undefined}
              aria-label="Sign out"
            >
              <LogOut className="w-4 h-4 shrink-0" />
              {!collapsed && <span>Sign Out</span>}
            </button>
          )}

          {!isCognitoEnabled && !collapsed && (
            <div className="px-3 py-1 text-xs text-slate-500">
              Mock Auth Mode
            </div>
          )}
        </div>
      </aside>

      {/* Main content */}
      <div
        className={`transition-all duration-300 ease-in-out ${
          collapsed ? 'lg:pl-[72px]' : 'lg:pl-64'
        }`}
      >
        <main className="p-4 sm:p-6 lg:p-8 max-w-[1600px] mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
