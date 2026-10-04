import React, { useState } from 'react';
import { X, FileText, Bookmark, Copy, Check, Hash, Layers } from 'lucide-react';
import { SourceReference } from '../types';

interface SourceInspectorDrawerProps {
  source: SourceReference | null;
  onClose: () => void;
}

export const SourceInspectorDrawer: React.FC<SourceInspectorDrawerProps> = ({
  source,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);

  if (!source) return null;

  const handleCopyText = () => {
    navigator.clipboard.writeText(source.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/40 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-lg bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="p-6 border-b border-slate-200 flex items-start justify-between bg-slate-50/70">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1.5 bg-blue-100 text-blue-700 rounded-md">
                <FileText className="w-4 h-4" />
              </span>
              <h3 className="font-bold text-slate-900 text-base truncate max-w-xs">
                {source.filename}
              </h3>
            </div>
            <p className="text-xs text-slate-500">Source Section Inspection Panel</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="p-6 space-y-6 flex-1 overflow-y-auto">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl space-y-1">
              <div className="flex items-center gap-1.5 text-slate-400 text-xs font-medium">
                <Bookmark className="w-3.5 h-3.5" />
                <span>Page Reference</span>
              </div>
              <p className="text-sm font-bold text-slate-900">
                Page {source.page_number}{source.page_number_approximate ? ' (approx.)' : ''}
              </p>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl space-y-1">
              <div className="flex items-center gap-1.5 text-slate-400 text-xs font-medium">
                <Layers className="w-3.5 h-3.5" />
                <span>Relevance Score</span>
              </div>
              <p className="text-sm font-bold text-blue-600">
                {(source.relevance_score * 100).toFixed(1)}% match
              </p>
            </div>
          </div>

          {/* Chunk ID */}
          <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl space-y-1">
            <div className="flex items-center gap-1.5 text-slate-400 text-xs font-medium">
              <Hash className="w-3.5 h-3.5" />
              <span>Vector Chunk ID</span>
            </div>
            <p className="text-xs font-mono text-slate-700 break-all">{source.chunk_id}</p>
          </div>

          {/* Extracted Text Block */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Relevant Extracted Text
              </h4>
              <button
                onClick={handleCopyText}
                className="flex items-center gap-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-2.5 py-1 rounded-md transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="text-emerald-700">✓ Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy Text</span>
                  </>
                )}
              </button>
            </div>

            <div className="p-4 bg-slate-900 text-slate-100 rounded-xl font-mono text-xs leading-relaxed whitespace-pre-wrap selection:bg-blue-600 border border-slate-800 shadow-inner">
              {source.text}
            </div>
          </div>

          <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl text-xs text-blue-800 leading-relaxed">
            <span className="font-semibold block mb-0.5">Citation Integrity Guarantee</span>
            This text segment was directly retrieved from index chunk{' '}
            <code className="bg-blue-100/80 px-1 py-0.5 rounded font-mono text-[11px]">{source.chunk_id}</code>.
            The model strictly generated its response using this verified context.
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-100 transition-colors shadow-xs"
          >
            Close Panel
          </button>
        </div>
      </div>
    </div>
  );
};
