import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  X,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Check,
} from 'lucide-react';
import { DocumentInfo } from '../types';
import { uploadDocuments } from '../api/client';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (newDocs: DocumentInfo[]) => void;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedDocs, setProcessedDocs] = useState<DocumentInfo[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = (files: File[]) => {
    setErrorMessage(null);
    setSelectedFiles((prev) => [...prev, ...files]);
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleStartUpload = async () => {
    if (selectedFiles.length === 0) return;
    setIsProcessing(true);
    setErrorMessage(null);

    try {
      const results = await uploadDocuments(selectedFiles);
      setProcessedDocs(results);
      onUploadSuccess(results);
    } catch (err: any) {
      setErrorMessage(err.message || 'An error occurred during document processing.');
    } finally {
      setIsProcessing(false);
    }
  };

  const resetModal = () => {
    setSelectedFiles([]);
    setProcessedDocs([]);
    setErrorMessage(null);
    setIsProcessing(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden border border-slate-200 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Upload Documents</h2>
            <p className="text-xs text-slate-500">
              Add documents to your intelligent knowledge base for cross-checking and RAG.
            </p>
          </div>
          <button
            onClick={resetModal}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Drag & Drop Area */}
          {processedDocs.length === 0 && (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
                isDragging
                  ? 'border-blue-500 bg-blue-50/50 ring-4 ring-blue-500/10'
                  : 'border-slate-300 hover:border-slate-400 bg-slate-50/30'
              }`}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.jpg,.jpeg,.png"
                className="hidden"
                onChange={handleFileInputChange}
              />
              <div className="w-12 h-12 mx-auto rounded-full bg-blue-100 text-blue-600 flex items-center justify-center mb-3">
                <UploadCloud className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-800">
                Drag & drop files here
              </h3>
              <p className="text-xs text-slate-500 mt-1">or</p>
              <button
                type="button"
                className="mt-2 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-md border border-blue-200 transition-colors"
              >
                Browse Files
              </button>
              <p className="text-[11px] font-medium text-slate-400 mt-4 tracking-wider">
                PDF • DOCX • TXT • JPG • JPEG • PNG (max 25 MB each; legacy DOC is unsupported)
              </p>
            </div>
          )}

          {/* Error Banner */}
          {errorMessage && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2.5 text-rose-800 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Backend processing status */}
          {isProcessing && (
            <div className="p-4 bg-blue-50/60 border border-blue-200/80 rounded-xl flex items-center gap-2 text-xs font-semibold text-blue-900">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-700" />
              <span>Backend is extracting and indexing {selectedFiles.length} file(s). Final status will be shown per file.</span>
            </div>
          )}

          {/* Selected File Queue */}
          {selectedFiles.length > 0 && processedDocs.length === 0 && (
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              <div className="flex items-center justify-between text-xs font-medium text-slate-500 px-1">
                <span>Selected files ({selectedFiles.length})</span>
                <button
                  onClick={() => setSelectedFiles([])}
                  className="text-slate-400 hover:text-slate-600 text-[11px]"
                >
                  Clear all
                </button>
              </div>
              {selectedFiles.map((file, idx) => (
                <div
                  key={`${file.name}-${idx}`}
                  className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg border border-slate-200/80 text-xs"
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <FileText className="w-4 h-4 text-slate-500 shrink-0" />
                    <span className="font-medium text-slate-800 truncate">{file.name}</span>
                    <span className="text-[11px] text-slate-400 shrink-0">
                      ({(file.size / 1024).toFixed(1)} KB)
                    </span>
                  </div>
                  {!isProcessing && (
                    <button
                      onClick={() => removeFile(idx)}
                      className="text-slate-400 hover:text-rose-500 p-1 rounded"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Processed Results Summary */}
          {processedDocs.length > 0 && (
            <div className="space-y-3">
              {(() => {
                const succeeded = processedDocs.filter((doc) => doc.upload_status === 'SUCCESS').length;
                const partial = processedDocs.filter((doc) => doc.upload_status === 'PARTIAL').length;
                const failed = processedDocs.filter((doc) => doc.upload_status === 'FAILED').length;
                const hasFailures = failed > 0 || partial > 0;
                return (
                  <div className={`flex items-center gap-2 font-semibold text-xs p-3 rounded-xl border ${
                    hasFailures
                      ? 'text-amber-800 bg-amber-50 border-amber-200'
                      : 'text-emerald-700 bg-emerald-50 border-emerald-200'
                  }`}>
                    {hasFailures ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
                    <span>
                      {succeeded} indexed successfully
                      {partial > 0 ? `, ${partial} partially indexed` : ''}
                      {failed > 0 ? `, ${failed} failed` : ''}.
                    </span>
                  </div>
                );
              })()}
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {processedDocs.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-3 bg-white rounded-lg border border-slate-200 flex items-center justify-between text-xs shadow-xs"
                  >
                    <div className="space-y-0.5">
                      <div className="font-semibold text-slate-900">{doc.filename}</div>
                      <div className="flex items-center gap-3 text-slate-500 text-[11px]">
                        <span className="uppercase font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                          {doc.file_type}
                        </span>
                        {doc.upload_status !== 'FAILED' && (
                          <>
                            <span>{doc.pages} page(s)</span>
                            <span>{doc.chunks_count} chunks</span>
                            <span>{doc.text_extracted_chars.toLocaleString()} chars</span>
                          </>
                        )}
                      </div>
                      {doc.error_message && (
                        <p className={`pt-1 text-[11px] ${
                          doc.upload_status === 'FAILED' ? 'text-rose-700' : 'text-amber-700'
                        }`}>{doc.error_message}</p>
                      )}
                    </div>
                    <span className={`flex items-center gap-1 font-medium text-xs px-2 py-1 rounded-md border ${
                      doc.upload_status === 'SUCCESS'
                        ? 'text-emerald-700 bg-emerald-50 border-emerald-200/50'
                        : doc.upload_status === 'PARTIAL'
                        ? 'text-amber-700 bg-amber-50 border-amber-200/50'
                        : 'text-rose-700 bg-rose-50 border-rose-200/50'
                    }`}>
                      {doc.upload_status === 'SUCCESS'
                        ? <Check className="w-3.5 h-3.5" />
                        : <AlertCircle className="w-3.5 h-3.5" />}
                      {doc.upload_status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3">
          {processedDocs.length > 0 ? (
            <button
              onClick={resetModal}
              className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm shadow-blue-500/20"
            >
              Done
            </button>
          ) : (
            <>
              <button
                onClick={resetModal}
                disabled={isProcessing}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-200/70 rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleStartUpload}
                disabled={selectedFiles.length === 0 || isProcessing}
                className="flex items-center gap-2 px-5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm shadow-blue-500/20 transition-all disabled:opacity-50"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <span>Upload & Index ({selectedFiles.length})</span>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
