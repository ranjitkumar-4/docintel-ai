import React from 'react';
import {
  Files,
  Layers,
  HelpCircle,
  AlertTriangle,
  UploadCloud,
  ChevronRight,
  Sparkles,
  ArrowUpRight,
  ShieldAlert,
  ShieldCheck,
  Clock,
} from 'lucide-react';
import { DashboardStats, InvestigationResult } from '../types';

interface DashboardViewProps {
  stats: DashboardStats;
  onOpenUpload: () => void;
  onOpenInvestigation: (investigation?: InvestigationResult) => void;
  onNavigateTab: (tab: string) => void;
  onSeedDemo: () => void;
  isSeeding: boolean;
  backendOnline: boolean;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  stats,
  onOpenUpload,
  onOpenInvestigation,
  onNavigateTab,
  onSeedDemo,
  isSeeding,
  backendOnline,
}) => {
  const metricCards = [
    {
      label: 'Documents',
      value: stats.documents_count,
      icon: Files,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-100',
      tab: 'documents',
    },
    {
      label: 'Indexed Sections',
      value: stats.indexed_sections_count,
      icon: Layers,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-50',
      borderColor: 'border-indigo-100',
      tab: 'documents',
    },
    {
      label: 'Questions Asked',
      value: stats.questions_asked_count,
      icon: HelpCircle,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
      borderColor: 'border-emerald-100',
      tab: 'history',
    },
    {
      label: 'Conflicts Detected',
      value: stats.conflicts_detected_count,
      icon: AlertTriangle,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
      borderColor: 'border-amber-100',
      tab: 'conflicts',
      highlightBadge: stats.conflicts_detected_count > 0,
    },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Hero Quick Start Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 rounded-2xl p-8 text-white relative overflow-hidden shadow-xl">
        <div className="absolute right-0 top-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="max-w-2xl relative z-10 space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/20 text-blue-300 text-xs font-semibold border border-blue-400/20">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Document Intelligence & Conflict Verification</span>
          </div>
          <h2 className="text-3xl font-extrabold tracking-tight">
            Investigate Documents. Detect Conflicts. Ensure Truth.
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            DocIntel AI ingests PDFs, DOCX, TXT, and scanned image documents. It retrieves grounded citations,
            detects cross-document contradictions, and communicates uncertainty instead of hallucinating.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={onOpenUpload}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-500 hover:bg-blue-400 text-white rounded-xl text-xs font-bold shadow-lg shadow-blue-500/30 transition-all active:scale-95"
            >
              <UploadCloud className="w-4 h-4" />
              <span>+ Upload Documents</span>
            </button>
            <button
              onClick={() => onNavigateTab('investigation')}
              className="flex items-center gap-2 px-5 py-2.5 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-bold border border-white/20 transition-all"
            >
              <span>Start Investigation</span>
              <ArrowUpRight className="w-4 h-4" />
            </button>
            <button
              onClick={onSeedDemo}
              disabled={isSeeding || !backendOnline}
              className="flex items-center gap-2 px-4 py-2.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 rounded-xl text-xs font-bold border border-amber-400/30 transition-all disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4 text-amber-300" />
              <span>{isSeeding ? 'Seeding Demo Data...' : 'Seed Sample Documents'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4 Metric Cards */}
      {!backendOnline && (
        <div role="alert" className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-sm text-rose-800">
          Backend Offline — start the FastAPI service to upload, search, or load the demo corpus.
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {metricCards.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.label}
              onClick={() => onNavigateTab(card.tab)}
              className={`p-6 bg-white rounded-2xl border ${card.borderColor} shadow-xs hover:shadow-md transition-all duration-200 cursor-pointer group`}
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-xl ${card.bgColor} ${card.color}`}>
                  <Icon className="w-6 h-6" />
                </div>
                {card.highlightBadge && (
                  <span className="flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                    Needs Review
                  </span>
                )}
              </div>
              <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
                {card.value}
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs font-semibold text-slate-500">{card.label}</span>
                <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-600 group-hover:translate-x-0.5 transition-all" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Investigations Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900">Recent Investigations</h3>
            <p className="text-xs text-slate-500">Latest questions asked and their grounded findings</p>
          </div>
          <button
            onClick={() => onNavigateTab('history')}
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
          >
            <span>View All</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {stats.recent_investigations.length === 0 ? (
          <div className="p-12 text-center text-slate-400 space-y-3">
            <HelpCircle className="w-10 h-10 mx-auto text-slate-300" />
            <p className="text-sm font-medium text-slate-600">No investigations conducted yet.</p>
            <p className="text-xs text-slate-400">
              Upload documents or click "Seed Sample Documents" to begin asking natural-language questions.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {stats.recent_investigations.map((inv) => (
              <div
                key={inv.id}
                onClick={() => onOpenInvestigation(inv)}
                className="p-4 px-6 hover:bg-slate-50 flex items-center justify-between transition-colors cursor-pointer group"
              >
                <div className="space-y-1 max-w-xl">
                  <div className="font-semibold text-sm text-slate-800 group-hover:text-blue-600 transition-colors line-clamp-1">
                    "{inv.question}"
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(inv.created_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                    <span>•</span>
                    <span>{inv.sources.length} sources cited</span>
                    <span>•</span>
                    <span className="font-mono text-[10px] text-slate-400">
                      {inv.processing_time_ms}ms
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {/* Conflict Badge */}
                  {inv.conflict_detected ? (
                    <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-bold rounded-lg bg-amber-100 text-amber-800 border border-amber-300">
                      <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                      Conflict Detected
                    </span>
                  ) : inv.is_uncertain_or_not_found ? (
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-100 text-slate-600 border border-slate-200">
                      Not Found
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-100 text-emerald-800 border border-emerald-200">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                      Grounded
                    </span>
                  )}

                  {/* Confidence Badge */}
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

                  <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-600 group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
