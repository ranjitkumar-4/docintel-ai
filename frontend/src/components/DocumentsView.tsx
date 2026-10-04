import React, { useState } from 'react';
import {
  Files,
  Search,
  Trash2,
  RefreshCw,
  Eye,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Calendar,
  Layers,
  FileCheck,
  X,
} from 'lucide-react';
import { DocumentInfo, DocumentDetail } from '../types';
import { deleteDocument, reindexDocument, fetchDocumentDetail } from '../api/client';

interface DocumentsViewProps {
  documents: DocumentInfo[];
  onRefresh: () => void;
  onOpenUpload: () => void;
}

export const DocumentsView: React.FC<DocumentsViewProps> = ({
  documents,
  onRefresh,
  onOpenUpload,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('ALL');
  const [activeDocDetail, setActiveDocDetail] = useState<DocumentDetail | null>(null);
  const [loadingDocId, setLoadingDocId] = useState<string | null>(null);

  const filteredDocs = documents.filter((doc) => {
    const matchesSearch = doc.filename.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFormat =
      selectedFormat === 'ALL' || doc.file_type.toUpperCase() === selectedFormat;
    return matchesSearch && matchesFormat;
  });

  const handleDelete = async (docId: string, filename: string) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}" and its vector chunks?`)) {
      return;
    }
    try {
      await deleteDocument(docId);
      onRefresh();
    } catch (e: any) {
      alert(`Error deleting document: ${e.message}`);
    }
  };

  const handleReindex = async (docId: string) => {
    try {
      setLoadingDocId(docId);
      await reindexDocument(docId);
      onRefresh();
    } catch (e: any) {
      alert(`Error re-indexing document: ${e.message}`);
    } finally {
      setLoadingDocId(null);
    }
  };

  const handleView = async (docId: string) => {
    try {
      setLoadingDocId(docId);
      const detail = await fetchDocumentDetail(docId);
      setActiveDocDetail(detail);
    } catch (e: any) {
      alert(`Error loading document preview: ${e.message}`);
    } finally {
      setLoadingDocId(null);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Filter and Actions Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Search */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search documents by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>

        {/* Format Filter Chips */}
        <div className="flex items-center gap-1.5 self-start sm:self-auto overflow-x-auto pb-1">
          {['ALL', 'PDF', 'DOCX', 'TXT', 'PNG'].map((fmt) => (
            <button
              key={fmt}
              onClick={() => setSelectedFormat(fmt)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                selectedFormat === fmt
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              {fmt}
            </button>
          ))}
        </div>
      </div>

      {/* Document Cards Grid */}
      {filteredDocs.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center space-y-4">
          <Files className="w-12 h-12 text-slate-300 mx-auto" />
          <div>
            <h3 className="text-sm font-bold text-slate-800">No documents found</h3>
            <p className="text-xs text-slate-400 mt-1">
              Upload your PDFs, DOCX, TXT, or scanned images to index them into ChromaDB.
            </p>
          </div>
          <button
            onClick={onOpenUpload}
            className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-semibold hover:bg-blue-700 shadow-sm"
          >
            Upload Documents
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredDocs.map((doc) => (
            <div
              key={doc.id}
              className="bg-white rounded-2xl border border-slate-200 shadow-xs hover:shadow-md transition-all p-5 flex flex-col justify-between"
            >
              <div className="space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5 truncate">
                    <div className="p-2 rounded-xl bg-blue-50 text-blue-600 shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="truncate">
                      <h4 className="font-bold text-slate-900 text-sm truncate" title={doc.filename}>
                        {doc.filename}
                      </h4>
                      <span className="text-[10px] uppercase font-mono font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                        {doc.file_type}
                      </span>
                    </div>
                  </div>

                  {/* Status Badge */}
                  {doc.status === 'indexed' && doc.upload_status === 'SUCCESS' ? (
                    <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full shrink-0">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      Indexed
                    </span>
                  ) : doc.status === 'indexed' && doc.upload_status === 'PARTIAL' ? (
                    <span className="flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full shrink-0">
                      <AlertCircle className="w-3 h-3 text-amber-600" />
                      Partially indexed
                    </span>
                  ) : doc.status === 'failed' ? (
                    <span className="flex items-center gap-1 text-[11px] font-semibold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-full shrink-0">
                      <AlertCircle className="w-3 h-3 text-rose-600" />
                      Failed
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[11px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full shrink-0">
                      <Loader2 className="w-3 h-3 text-blue-600 animate-spin" />
                      {doc.status}
                    </span>
                  )}
                </div>

                {doc.error_message && (
                  <p className={`text-[11px] leading-relaxed ${
                    doc.upload_status === 'FAILED' ? 'text-rose-700' : 'text-amber-700'
                  }`}>
                    {doc.error_message}
                  </p>
                )}

                {/* Metadata stats */}
                <div className="grid grid-cols-3 gap-2 py-2 border-y border-slate-100 text-xs">
                  <div>
                    <span className="text-[10px] text-slate-400 block font-medium">Pages</span>
                    <span className="font-bold text-slate-800">{doc.pages}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block font-medium">Chunks</span>
                    <span className="font-bold text-blue-600">{doc.chunks_count}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block font-medium">Size</span>
                    <span className="font-bold text-slate-800">
                      {(doc.file_size_bytes / 1024).toFixed(0)} KB
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1 text-[11px] text-slate-400">
                  <Calendar className="w-3 h-3" />
                  <span>
                    Uploaded {new Date(doc.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}
                  </span>
                </div>
              </div>

              {/* Actions Footer */}
              <div className="flex items-center justify-between pt-4 mt-3 border-t border-slate-100">
                <button
                  onClick={() => handleView(doc.id)}
                  disabled={loadingDocId === doc.id}
                  className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-blue-600 hover:bg-blue-50 px-2.5 py-1.5 rounded-lg transition-colors"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>View</span>
                </button>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleReindex(doc.id)}
                    disabled={loadingDocId === doc.id}
                    title="Re-extract and re-index vector embeddings"
                    className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loadingDocId === doc.id ? 'animate-spin' : ''}`} />
                  </button>
                  <button
                    onClick={() => handleDelete(doc.id, doc.filename)}
                    title="Delete document"
                    className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Document View / Inspection Modal */}
      {activeDocDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] flex flex-col border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="space-y-0.5">
                <h3 className="font-bold text-slate-900 text-sm">{activeDocDetail.filename}</h3>
                <p className="text-xs text-slate-500">
                  {activeDocDetail.pages} pages • {activeDocDetail.chunks_count} vector chunks •{' '}
                  {activeDocDetail.text_extracted_chars.toLocaleString()} characters extracted
                </p>
              </div>
              <button
                onClick={() => setActiveDocDetail(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Extracted Chunks in Vector Store ({activeDocDetail.chunks.length})
              </h4>
              <div className="space-y-3">
                {activeDocDetail.chunks.map((chunk, idx) => (
                  <div
                    key={chunk.chunk_id}
                    className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between font-mono text-[11px] text-slate-500">
                      <span className="font-semibold text-blue-700">Page {chunk.page_number}</span>
                      <span>Chunk #{idx + 1} ({chunk.chunk_id})</span>
                    </div>
                    <p className="text-slate-700 whitespace-pre-wrap leading-relaxed">{chunk.text}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setActiveDocDetail(null)}
                className="px-4 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-100"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
