import React from 'react';
import {
  LayoutDashboard,
  Files,
  SearchCode,
  AlertTriangle,
  History,
  Sliders,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  conflictsCount: number;
  backendOnline: boolean;
  vectorReady: boolean;
  ocrAvailable: boolean;
  totalChunks: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  setCurrentTab,
  conflictsCount,
  backendOnline,
  vectorReady,
  ocrAvailable,
  totalChunks,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'documents', label: 'Documents', icon: Files },
    { id: 'investigation', label: 'Investigation', icon: SearchCode, highlight: true },
    { id: 'conflicts', label: 'Conflicts', icon: AlertTriangle, badge: conflictsCount > 0 ? conflictsCount : undefined },
    { id: 'history', label: 'History', icon: History },
    { id: 'settings', label: 'Settings', icon: Sliders },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col justify-between shrink-0 h-screen sticky top-0 border-r border-slate-800">
      <div>
        {/* Brand Logo */}
        <div className="p-6 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/25">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-white tracking-tight text-lg">DocIntel AI</span>
                <span className="text-[10px] font-semibold uppercase tracking-wider bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/30">
                  v1.0
                </span>
              </div>
              <p className="text-xs text-slate-400">Document Investigator</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider px-3 mb-2">
            Investigation Platform
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/70'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    {item.badge}
                  </span>
                )}
                {item.highlight && !isActive && (
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* System Status Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/40">
        <div className="flex items-center justify-between text-xs mb-2">
          <span className="text-slate-400 font-medium">System Status</span>
          <span className="text-slate-400 font-mono text-[11px]">{totalChunks} chunks</span>
        </div>
        <div className={`space-y-1 text-[11px] font-medium px-2.5 py-2 rounded-md border ${
          backendOnline && vectorReady
            ? 'text-emerald-300 bg-emerald-950/40 border-emerald-800/50'
            : 'text-rose-300 bg-rose-950/40 border-rose-800/50'
        }`}>
          <div>Backend {backendOnline ? 'Online' : 'Offline'}</div>
          {backendOnline && <div>Vector database {vectorReady ? 'Ready' : 'Unavailable'}</div>}
          <div className={ocrAvailable ? 'text-emerald-300' : 'text-amber-300'}>
            OCR {ocrAvailable ? 'Available' : 'Unavailable'}
          </div>
        </div>
      </div>
    </aside>
  );
};
