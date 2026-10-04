import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldAlert,
  SearchCode,
  Check,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { ConflictItem } from '../types';
import { resolveConflict } from '../api/client';

interface ConflictsViewProps {
  conflicts: ConflictItem[];
  onRefresh: () => void;
  onInvestigateTopic: (topic: string) => void;
}

export const ConflictsView: React.FC<ConflictsViewProps> = ({
  conflicts,
  onRefresh,
  onInvestigateTopic,
}) => {
  const [filter, setFilter] = useState<'ALL' | 'unresolved' | 'resolved'>('ALL');
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const filteredConflicts = conflicts.filter((c) => {
    if (filter === 'ALL') return true;
    return c.status === filter;
  });

  const handleToggleResolve = async (conflictId: string, currentStatus: string) => {
    try {
      setResolvingId(conflictId);
      const newStatus = currentStatus === 'resolved' ? 'unresolved' : 'resolved';
      await resolveConflict(conflictId, newStatus);
      onRefresh();
    } catch (e: any) {
      alert(`Error updating conflict status: ${e.message}`);
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-6xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <span className="p-2 rounded-xl bg-amber-100 text-amber-700">
              <AlertTriangle className="w-5 h-5" />
            </span>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Cross-Document Conflicts
            </h2>
          </div>
          <p className="text-xs text-slate-500">
            Detected contradictions across multiple documents. Review differing statements and flag resolution.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl self-start sm:self-auto">
          {[
            { id: 'ALL', label: `All (${conflicts.length})` },
            { id: 'unresolved', label: `Unresolved (${conflicts.filter((c) => c.status === 'unresolved').length})` },
            { id: 'resolved', label: `Resolved (${conflicts.filter((c) => c.status === 'resolved').length})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id as any)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                filter === tab.id
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Total Conflicts Count Card */}
      <div className="p-6 bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-transparent border border-amber-200 rounded-2xl flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-amber-500 text-white rounded-xl shadow-md shadow-amber-500/20">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-bold text-amber-900 uppercase tracking-wider block">
              Total Conflicts
            </span>
            <span className="text-3xl font-extrabold text-slate-900">
              {conflicts.length}
            </span>
          </div>
        </div>
        <p className="text-xs text-slate-500 max-w-sm hidden md:block">
          DocIntel AI systematically cross-references dates, leave allowances, numeric thresholds, and policies
          to safeguard compliance.
        </p>
      </div>

      {/* Conflict Cards Grid */}
      {filteredConflicts.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center space-y-3">
          <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />
          <h3 className="text-sm font-bold text-slate-800">No conflicts found in this category</h3>
          <p className="text-xs text-slate-400">
            All document assertions match or have been marked as resolved.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredConflicts.map((c) => (
            <div
              key={c.id}
              className={`bg-white rounded-2xl border transition-all p-6 shadow-xs ${
                c.status === 'resolved'
                  ? 'border-emerald-200 bg-emerald-50/20'
                  : 'border-amber-200/80 hover:shadow-md'
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 pb-4 mb-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-slate-900 text-base">{c.topic}</span>
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                        c.status === 'resolved'
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                          : 'bg-amber-100 text-amber-800 border-amber-300'
                      }`}
                    >
                      {c.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Confidence: <span className="font-bold text-rose-600 uppercase">{c.confidence}</span> •
                    Detected {new Date(c.detected_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onInvestigateTopic(c.topic)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200 transition-colors"
                  >
                    <SearchCode className="w-3.5 h-3.5" />
                    <span>View Conflict</span>
                  </button>

                  <button
                    onClick={() => handleToggleResolve(c.id, c.status)}
                    disabled={resolvingId === c.id}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                      c.status === 'resolved'
                        ? 'bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-300'
                        : 'bg-emerald-600 text-white hover:bg-emerald-700 border-emerald-600 shadow-2xs'
                    }`}
                  >
                    {c.status === 'resolved' ? (
                      <>
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Mark Unresolved</span>
                      </>
                    ) : (
                      <>
                        <Check className="w-3.5 h-3.5" />
                        <span>Mark Resolved</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Side-by-side statements comparison */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Doc A */}
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-900">{c.document_a_name}</span>
                    <span className="text-[10px] font-semibold bg-white border border-slate-200 px-2 py-0.5 rounded text-slate-600">
                      Page {c.document_a_page}{c.document_a_page_approximate ? ' (approx.)' : ''}
                    </span>
                  </div>
                  <blockquote className="text-xs text-slate-700 italic border-l-2 border-blue-500 pl-2 py-1 leading-relaxed bg-white/60 rounded-r">
                    "{c.document_a_statement}"
                  </blockquote>
                </div>

                {/* Doc B */}
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-900">{c.document_b_name}</span>
                    <span className="text-[10px] font-semibold bg-white border border-slate-200 px-2 py-0.5 rounded text-slate-600">
                      Page {c.document_b_page}{c.document_b_page_approximate ? ' (approx.)' : ''}
                    </span>
                  </div>
                  <blockquote className="text-xs text-slate-700 italic border-l-2 border-amber-500 pl-2 py-1 leading-relaxed bg-white/60 rounded-r">
                    "{c.document_b_statement}"
                  </blockquote>
                </div>
              </div>

              {c.recommendation && (
                <div className="mt-4 p-3 bg-amber-50/70 border border-amber-200/80 rounded-xl text-xs text-amber-900 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>{c.recommendation}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
