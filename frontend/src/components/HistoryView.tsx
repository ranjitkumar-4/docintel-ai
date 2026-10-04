import React, { useState } from 'react';
import {
  History,
  Search,
  Clock,
  ChevronRight,
  ShieldAlert,
  ShieldCheck,
  HelpCircle,
  FileText,
  Trash2,
} from 'lucide-react';
import { InvestigationResult } from '../types';

interface HistoryViewProps {
  investigations: InvestigationResult[];
  onSelectInvestigation: (inv: InvestigationResult) => void;
  onNavigateInvestigation: () => void;
}

export const HistoryView: React.FC<HistoryViewProps> = ({
  investigations,
  onSelectInvestigation,
  onNavigateInvestigation,
}) => {
  const [search, setSearch] = useState('');
  const [filterConflict, setFilterConflict] = useState<'ALL' | 'CONFLICT' | 'GROUNDED'>('ALL');

  const filtered = investigations.filter((inv) => {
    const matchesSearch =
      inv.question.toLowerCase().includes(search.toLowerCase()) ||
      inv.answer.toLowerCase().includes(search.toLowerCase());

    if (filterConflict === 'CONFLICT') return matchesSearch && inv.conflict_detected;
    if (filterConflict === 'GROUNDED') return matchesSearch && !inv.conflict_detected && !inv.is_uncertain_or_not_found;
    return matchesSearch;
  });

  return (
    <div className="p-8 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <span className="p-2 rounded-xl bg-blue-100 text-blue-700">
              <History className="w-5 h-5" />
            </span>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Investigation History
            </h2>
          </div>
          <p className="text-xs text-slate-500">
            Log of previously conducted document queries, citations, confidence scores, and conflict analyses.
          </p>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <div className="relative w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search history..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>
        </div>
      </div>

      {/* History Items */}
      {filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center space-y-3">
          <HelpCircle className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="text-sm font-bold text-slate-800">No investigation records found</h3>
          <p className="text-xs text-slate-400">
            Ask questions in the Investigation tab to build an audit trail of grounded findings.
          </p>
          <button
            onClick={onNavigateInvestigation}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-xs"
          >
            Start an Investigation
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((inv) => (
            <div
              key={inv.id}
              onClick={() => onSelectInvestigation(inv)}
              className="bg-white rounded-2xl border border-slate-200 hover:border-blue-400 hover:shadow-md p-5 transition-all cursor-pointer group flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="space-y-2 max-w-2xl">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-bold text-sm text-slate-900 group-hover:text-blue-600 transition-colors">
                    "{inv.question}"
                  </span>
                </div>

                <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                  {inv.answer}
                </p>

                <div className="flex items-center gap-3 text-[11px] text-slate-400">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(inv.created_at).toLocaleString([], {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    {inv.sources.length} sources
                  </span>
                  <span>•</span>
                  <span className="font-mono text-[10px]">{inv.processing_time_ms}ms</span>
                </div>
              </div>

              {/* Status and Action */}
              <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                {inv.conflict_detected ? (
                  <span className="flex items-center gap-1 px-2.5 py-1 text-xs font-bold rounded-lg bg-amber-100 text-amber-900 border border-amber-300">
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                    Conflict
                  </span>
                ) : inv.is_uncertain_or_not_found ? (
                  <span className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
                    Not Found
                  </span>
                ) : (
                  <span className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-100 text-emerald-800 border border-emerald-200">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    Grounded
                  </span>
                )}

                <span
                  className={`px-2.5 py-1 text-[11px] font-bold uppercase rounded-lg border ${
                    inv.confidence === 'HIGH'
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : inv.confidence === 'MEDIUM'
                      ? 'bg-blue-50 text-blue-700 border-blue-200'
                      : 'bg-rose-50 text-rose-700 border-rose-200'
                  }`}
                >
                  {inv.confidence}
                </span>

                <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-blue-600 group-hover:translate-x-1 transition-all" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
