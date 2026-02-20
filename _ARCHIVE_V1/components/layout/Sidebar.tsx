'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Radio, Globe, FileText, Star, Settings } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

const navigation = [
  { name: 'Signal Feed', href: '/', icon: Radio },
  { name: 'Cockpit', href: '/cockpit', icon: Globe },
  { name: 'Briefings', href: '/briefings', icon: FileText },
  { name: 'Watchlist', href: '/watchlist', icon: Star },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full bg-gray-950 border-r border-gray-800">
      {/* Logo */}
      <div className="flex items-center h-16 px-6 border-b border-gray-800">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg" />
          <span className="text-xl font-bold text-gray-100">SHORT GRAVITY</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                isActive
                  ? 'bg-gray-800 text-gray-100'
                  : 'text-gray-400 hover:bg-gray-900 hover:text-gray-300'
              )}
            >
              <Icon className="w-5 h-5 mr-3" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800">
        <div className="text-xs text-gray-500">
          <div>v1.0.0-prototype</div>
          <div className="mt-1">Mock Data Active</div>
        </div>
      </div>
    </div>
  );
}
