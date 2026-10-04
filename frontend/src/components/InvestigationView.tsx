import React, { useState } from 'react';
import {
  SearchCode,
  Send,
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  HelpCircle,
  Copy,
  Check,
  Share2,
  FileText,
  ExternalLink,
  Loader2,
  Filter,
  CheckCircle2,
  ArrowRight,
  Info,
} from 'lucide-react';
import {
  DocumentInfo,
  InvestigationResult,
  SourceReference,
} from '../types';
import { askQuestion } from '../api/client';

interface InvestigationViewProps {
  documents: DocumentInfo[];
  currentInvestigation: InvestigationResult | null;
  setCurrentInvestigation: (inv: InvestigationResult | null) => void;
  onOpenSourceInspector: (source: SourceReference) => void;
  onOpenShareModal: (inv: InvestigationResult) => void;
}

const SUGGESTED_PROMPTS = [
  {
    label: 'Leave Allowance (Conflict Test)',
    prompt: 'How many paid leaves can an employee take per year?',
    badge: 'Tests Conflict Detection',
  },
  {
    label: 'Probation Period',
    prompt: 'What is the probation period for new employees?',
  },
  {
    label: 'Remote Work Stipend',
    prompt: 'What is the home office setup stipend for remote work?',
  },
  {
    label: 'Pet Policy (Uncertainty Test)',
    prompt: 'What is the policy for bringing pets into the office?',
    badge: 'Tests Uncertainty Handling',
  },
  {
    label: 'Security & Passwords',
    prompt: 'What are the password requirements and rotation schedule?',
  },
];

export const InvestigationView: React.FC<InvestigationViewProps> = ({
  documents,
  currentInvestigation,
  setCurrentInvestigation,
  onOpenSourceInspector,
  onOpenShareModal,
}) => {
  const [question, setQuestion] = useState('');
  const [selectedDocId, setSelectedDocId] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedAnswer, setCopiedAnswer] = useState(false);
  const [copiedSources, setCopiedSources] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleAsk = async (queryText?: string) => {
    const q = (queryText || question).trim();
    if (!q || isLoading) return;

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const docFilter = selectedDocId === 'ALL' ? undefined : [selectedDocId];
      const result = await askQuestion(q, docFilter);
      setCurrentInvestigation(result);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to complete investigation. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyAnswer = () => {
    if (!currentInvestigation) return;
    navigator.clipboard.writeText(currentInvestigation.answer);
    setCopiedAnswer(true);
    setTimeout(() => setCopiedAnswer(false), 2000);
  };

  const handleCopySources = () => {
    if (!currentInvestigation || currentInvestigation.sources.length === 0) return;
    const sourcesText = currentInvestigation.sources
      .map(
        (s, idx) =>
          `[Source ${idx + 1}] ${s.filename} (Page ${s.page_number}${s.page_number_approximate ? ', approximate' : ''}, Chunk: ${s.chunk_id}, Relevance: ${(s.relevance_score * 100).toFixed(1)}%):\n${s.text}`
      )
      .join('\n\n');
    navigator.clipboard.writeText(sourcesText);
    setCopiedSources(true);
    setTimeout(() => setCopiedSources(false), 2000);
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      {/* Header Intro */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="p-2 rounded-xl bg-blue-100 text-blue-700">
            <SearchCode className="w-5 h-5" />
          </span>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
            Document Investigation
          </h2>
        </div>
        <p className="text-xs text-slate-500">
          Ask natural-language questions across your uploaded documents. DocIntel AI cites exact sections,
          detects conflicting policy claims, and reports uncertainty when information is missing.
        </p>
      </div>

      {/* Scope Selector & Query Input Bar */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
        {/* Document Scope Filter */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2 text-slate-600 font-semibold">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span>Investigation Scope:</span>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="bg-slate-50 border border-slate-200 text-slate-800 rounded-lg px-3 py-1.5 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="ALL">All Uploaded Documents ({documents.length})</option>
              {documents.filter((d) => d.status === 'indexed' && d.chunks_count > 0).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename} ({d.file_type.toUpperCase()})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Input Bar */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Ask anything about your documents..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
            className="flex-1 bg-slate-50 border border-slate-300 rounded-xl px-4 py-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
          />
          <button
            onClick={() => handleAsk()}
            disabled={!question.trim() || isLoading}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/20 transition-all active:scale-95 disabled:pointer-events-none"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Investigating...</span>
              </>
            ) : (
              <>
                <span>Ask Question</span>
                <Send className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>

        {/* Suggested Queries Chips */}
        <div className="space-y-1.5 pt-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
            Suggested Investigation Prompts:
          </span>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_PROMPTS.map((item) => (
              <button
                key={item.label}
                onClick={() => {
                  setQuestion(item.prompt);
                  handleAsk(item.prompt);
                }}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 transition-colors text-left disabled:opacity-50"
              >
                <span>{item.label}</span>
                {item.badge && (
                  <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 border border-amber-200">
                    {item.badge}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stepped Loading State */}
      {isLoading && (
        <div className="p-6 bg-white rounded-2xl border border-blue-200 shadow-sm flex items-center gap-2 text-xs font-semibold text-blue-900 animate-in fade-in duration-200">
          <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
          <span>Retrieving evidence and preparing a grounded response…</span>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Investigation Results Display */}
      {currentInvestigation && !isLoading && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {/* Question Summary Bar */}
          <div className="bg-slate-100/80 rounded-xl px-5 py-3 border border-slate-200/80 flex items-center justify-between text-xs">
            <div className="space-y-0.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Investigation Query
              </span>
              <p className="font-bold text-slate-900 text-sm">"{currentInvestigation.question}"</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onOpenShareModal(currentInvestigation)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-200/80 rounded-lg border border-slate-300 transition-colors shadow-2xs"
              >
                <Share2 className="w-3.5 h-3.5 text-slate-600" />
                <span>Share Investigation</span>
              </button>
            </div>
          </div>

          {/* CASE A: CONFLICT DETECTED BANNER */}
          {currentInvestigation.conflict_detected && (
            <div className="p-6 bg-gradient-to-br from-amber-50 to-orange-50 border-2 border-amber-300 rounded-2xl shadow-sm space-y-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-amber-500 text-white shadow-md shadow-amber-500/20">
                    <ShieldAlert className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-extrabold text-amber-950 text-base">
                      ⚠ CONFLICT DETECTED
                    </h3>
                    <p className="text-xs text-amber-800 font-medium">
                      Conflicting information was found across your official documents.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 text-xs font-bold rounded-lg bg-amber-200 text-amber-900 border border-amber-300">
                    Confidence: LOW
                  </span>
                </div>
              </div>

              {/* Side-by-side or stacked conflicting sources */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                {currentInvestigation.conflicting_sources.map((src, idx) => (
                  <div
                    key={`${src.document_name}-${idx}`}
                    className="p-4 bg-white/90 border border-amber-200 rounded-xl space-y-2 shadow-2xs"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-amber-950 truncate max-w-[200px]">
                        {src.document_name}
                      </span>
                      <span className="text-[11px] font-semibold bg-amber-100 text-amber-800 px-2 py-0.5 rounded">
                        Page {src.page_number}{src.page_number_approximate ? ' (approx.)' : ''}
                      </span>
                    </div>
                    <blockquote className="text-xs text-slate-700 italic border-l-2 border-amber-500 pl-2 py-0.5 leading-relaxed">
                      "{src.statement}"
                    </blockquote>
                  </div>
                ))}
              </div>

              {/* Recommendation Callout */}
              <div className="p-3 bg-white/80 border border-amber-200/90 rounded-xl flex items-start gap-2.5 text-xs text-amber-900">
                <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold block">Investigator Recommendation:</span>
                  <span>{currentInvestigation.recommendation}</span>
                </div>
              </div>
            </div>
          )}

          {/* CASE B: UNCERTAINTY / NOT FOUND BOX */}
          {currentInvestigation.is_uncertain_or_not_found && (
            <div className="p-8 bg-slate-50 border-2 border-dashed border-slate-300 rounded-2xl text-center space-y-4">
              <div className="w-12 h-12 mx-auto rounded-full bg-slate-200 text-slate-600 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-900">⚠ Information Not Found</h3>
                <p className="text-xs text-slate-600 max-w-md mx-auto leading-relaxed">
                  {currentInvestigation.answer}
                </p>
                {currentInvestigation.uncertainty_reason && (
                  <p className="text-[11px] text-slate-500 max-w-md mx-auto">
                    {currentInvestigation.uncertainty_reason}
                  </p>
                )}
              </div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-200 text-slate-700 text-xs font-semibold">
                <span>Confidence: NOT FOUND · LOW</span>
                <span>• Strict Grounding Active</span>
              </div>
            </div>
          )}

          {/* CASE C: NORMAL ANSWER CARD */}
          {!currentInvestigation.is_uncertain_or_not_found && !currentInvestigation.conflict_detected && (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    ANSWER
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-slate-400">Confidence:</span>
                  <span
                    className={`px-2.5 py-0.5 text-xs font-bold uppercase rounded-lg border ${
                      currentInvestigation.confidence === 'HIGH'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : currentInvestigation.confidence === 'MEDIUM'
                        ? 'bg-blue-50 text-blue-700 border-blue-200'
                        : 'bg-rose-50 text-rose-700 border-rose-200'
                    }`}
                  >
                    {currentInvestigation.confidence}
                  </span>
                </div>
              </div>

              {/* Formatted Answer text */}
              <div className="text-slate-800 text-sm leading-relaxed whitespace-pre-wrap font-medium">
                {currentInvestigation.answer}
              </div>

              <div className="text-xs text-slate-500 pt-2 border-t border-slate-100">
                <span className="font-semibold text-slate-700">Grounded Rationale: </span>
                {currentInvestigation.confidence_reason}
              </div>
            </div>
          )}

          {/* Action Buttons: Copy Answer, Copy Sources */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleCopyAnswer}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 rounded-xl border border-slate-200 shadow-2xs transition-colors"
            >
              {copiedAnswer ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-emerald-700">✓ Copied Answer</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Answer</span>
                </>
              )}
            </button>

            {currentInvestigation.sources.length > 0 && (
              <button
                onClick={handleCopySources}
                className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 rounded-xl border border-slate-200 shadow-2xs transition-colors"
              >
                {copiedSources ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="text-emerald-700">✓ Copied Sources</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy Sources</span>
                  </>
                )}
              </button>
            )}
          </div>

          {/* SOURCES SECTION */}
          {currentInvestigation.sources.length > 0 && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-blue-600" />
                  <span>Supporting Sources ({currentInvestigation.sources.length})</span>
                </h4>
                <span className="text-[11px] text-slate-400">Click any source to inspect chunk details</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {currentInvestigation.sources.map((source, idx) => (
                  <div
                    key={`${source.chunk_id}-${idx}`}
                    onClick={() => onOpenSourceInspector(source)}
                    className="p-4 bg-white rounded-xl border border-slate-200 hover:border-blue-400 hover:shadow-md transition-all cursor-pointer group space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2 truncate">
                        <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 font-bold text-[11px] flex items-center justify-center shrink-0">
                          {idx + 1}
                        </span>
                        <span className="font-bold text-xs text-slate-900 group-hover:text-blue-600 truncate transition-colors">
                          {source.filename}
                        </span>
                      </div>
                      <span className="text-[10px] font-semibold bg-slate-100 text-slate-600 px-2 py-0.5 rounded shrink-0">
                        Page {source.page_number}{source.page_number_approximate ? ' (approx.)' : ''}
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed italic">
                      "{source.text}"
                    </p>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-[10px] text-slate-400 font-mono">
                      <span>Chunk: {source.chunk_id.split('_').slice(-2).join('_')}</span>
                      <span className="text-blue-600 font-semibold group-hover:underline flex items-center gap-1">
                        Inspect <ExternalLink className="w-2.5 h-2.5" />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
