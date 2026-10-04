import React from 'react';
import { UploadCloud, Sparkles, RefreshCw } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle?: string;
  onOpenUpload: () => void;
  onSeedDemo: () => void;
  isSeeding: boolean;
  backendOnline: boolean;
  onRefresh?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  subtitle,
  onOpenUpload,
  onSeedDemo,
  isSeeding,
  backendOnline,
  onRefresh,
}) => {
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between sticky top-0 z-10 shadow-xs">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
            title="Refresh data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}

        <button
          onClick={onSeedDemo}
          disabled={isSeeding || !backendOnline}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-300 transition-all disabled:opacity-50"
          title="Load sample documents with intentional conflicts"
        >
          <Sparkles className={`w-3.5 h-3.5 text-amber-600 ${isSeeding ? 'animate-spin' : ''}`} />
          <span>{isSeeding ? 'Indexing Demo...' : 'Load Sample Documents'}</span>
        </button>

        <button
          onClick={onOpenUpload}
          disabled={!backendOnline}
          className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm shadow-blue-500/30 transition-all active:scale-95"
        >
          <UploadCloud className="w-4 h-4" />
          <span>+ Upload Documents</span>
        </button>
      </div>
    </header>
  );
};
