import React, { useState, useEffect } from 'react';
import {
  Sliders,
  Cpu,
  Database,
  Trash2,
  Sparkles,
  Check,
  AlertCircle,
  Save,
  Loader2,
} from 'lucide-react';
import { SystemSettings } from '../types';
import { fetchSettings, updateSettings, resetDatabase } from '../api/client';

interface SettingsViewProps {
  onSettingsChanged: () => void;
  onSeedDemo: () => void;
  isSeeding: boolean;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  onSettingsChanged,
  onSeedDemo,
  isSeeding,
}) => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [provider, setProvider] = useState('local');
  const [chunkSize, setChunkSize] = useState(500);
  const [chunkOverlap, setChunkOverlap] = useState(100);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await fetchSettings();
      setLoadError(null);
      setSettings(data);
      setProvider(data.llm_provider);
      setChunkSize(data.chunk_size);
      setChunkOverlap(data.chunk_overlap);
    } catch (e) {
      console.error(e);
      setLoadError(e instanceof Error ? e.message : 'Could not load system settings.');
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveSuccess(false);
    try {
      await updateSettings({
        llm_provider: provider,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
      });
      setSaveSuccess(true);
      onSettingsChanged();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (e: any) {
      alert(`Failed to save settings: ${e.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Are you sure you want to clear all indexed documents and history?')) {
      return;
    }
    setIsResetting(true);
    try {
      await resetDatabase();
      onSettingsChanged();
      alert('Knowledge base and vector index have been cleared.');
    } catch (e: any) {
      alert(`Reset error: ${e.message}`);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2.5">
          <span className="p-2 rounded-xl bg-blue-100 text-blue-700">
            <Sliders className="w-5 h-5" />
          </span>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">System Settings</h2>
        </div>
        <p className="text-xs text-slate-500">
          Configure the LLM generation backend, vector chunking strategies, and knowledge base. API credentials stay on the backend.
        </p>
      </div>

      <div className="space-y-5">
        {loadError && (
          <div role="alert" className="p-3 rounded-lg border border-rose-200 bg-rose-50 text-xs text-rose-800">
            Settings could not be loaded: {loadError}
          </div>
        )}
        {/* LLM Engine Configuration */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-5">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Cpu className="w-4 h-4 text-blue-600" />
            <h3 className="font-bold text-slate-900 text-sm">LLM Answer Generation Engine</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              {
                id: 'local',
                name: 'Local Grounded Engine',
                desc: 'Intelligent rule-based RAG synthesis with strict factual alignment. Zero API keys required.',
                badge: 'Hackathon Default',
              },
              {
                id: 'openai',
                name: 'OpenAI (GPT-4o Mini)',
                desc: 'Generates answers via OpenAI Chat Completions API with strict anti-hallucination grounding prompt.',
                badge: 'OpenAI API',
              },
              {
                id: 'gemini',
                name: 'Google Gemini',
                desc: 'Generates grounded answers via Google Gemini 1.5 Flash API.',
                badge: 'Gemini API',
              },
            ].map((opt) => {
              const keyAvailable =
                opt.id === 'local' ||
                (opt.id === 'openai' && settings?.has_openai_key) ||
                (opt.id === 'gemini' && settings?.has_gemini_key);
              return (
              <label
                key={opt.id}
                className={`p-4 rounded-xl border-2 transition-all flex flex-col justify-between ${
                  provider === opt.id
                    ? 'border-blue-600 bg-blue-50/50 shadow-xs'
                    : 'border-slate-200 hover:border-slate-300 bg-slate-50/30'
                } ${keyAvailable ? 'cursor-pointer' : 'cursor-not-allowed opacity-60'}`}
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-slate-900">{opt.name}</span>
                    <input
                      type="radio"
                      name="provider"
                      value={opt.id}
                      checked={provider === opt.id}
                      onChange={(e) => setProvider(e.target.value)}
                      disabled={!keyAvailable}
                      className="text-blue-600 focus:ring-blue-500"
                    />
                  </div>
                  <p className="text-[11px] text-slate-500 leading-relaxed">{opt.desc}</p>
                </div>
                <span className="text-[10px] font-semibold text-blue-700 bg-blue-100/60 self-start px-2 py-0.5 rounded mt-3">
                  {opt.badge}
                </span>
              </label>
            )})}
          </div>

          <p className="text-[11px] text-slate-500">
            External providers are enabled only when their API key is configured in the backend environment
            (<code>OPENAI_API_KEY</code> or <code>GEMINI_API_KEY</code>). Keys are never entered or returned by the frontend.
          </p>
        </div>

        {/* Chunking Settings */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Database className="w-4 h-4 text-indigo-600" />
            <h3 className="font-bold text-slate-900 text-sm">RAG & Chunking Parameters</h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700">Chunk Size (characters)</span>
                <span className="font-mono text-blue-600 font-bold">{chunkSize} chars</span>
              </div>
              <input
                type="range"
                min="200"
                max="1200"
                step="50"
                value={chunkSize}
                onChange={(e) => setChunkSize(Number(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <span className="text-[11px] text-slate-400">
                Determines granularity of vector segments stored in ChromaDB.
              </span>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700">Chunk Overlap (characters)</span>
                <span className="font-mono text-blue-600 font-bold">{chunkOverlap} chars</span>
              </div>
              <input
                type="range"
                min="20"
                max="300"
                step="20"
                value={chunkOverlap}
                onChange={(e) => setChunkOverlap(Number(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <span className="text-[11px] text-slate-400">
                Sliding window overlap to preserve semantic continuity across splits.
              </span>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex items-center justify-between">
          <div>
            {saveSuccess && (
              <span className="flex items-center gap-1.5 text-xs text-emerald-700 font-semibold bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-lg">
                <Check className="w-3.5 h-3.5" />
                <span>Settings saved successfully!</span>
              </span>
            )}
          </div>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/20 transition-all active:scale-95 disabled:opacity-50"
          >
            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            <span>Save Configuration</span>
          </button>
        </div>

        {/* Database Management & Demo Data */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Database className="w-4 h-4 text-slate-700" />
            <h3 className="font-bold text-slate-900 text-sm">Demo Data & Knowledge Base Actions</h3>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="space-y-1">
              <h4 className="font-bold text-slate-800 text-xs">Load Sample Documents</h4>
              <p className="text-[11px] text-slate-500">
                Generates Company Policy (20 leave days), Employee Handbook (18 leave days), Remote Work Guidelines,
                Security Compliance, and Office Notice PNG. Tesseract must be installed for image OCR.
              </p>
            </div>
            <button
              onClick={onSeedDemo}
              disabled={isSeeding}
              className="shrink-0 flex items-center gap-2 px-4 py-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-800 border border-amber-300 rounded-xl text-xs font-bold transition-all disabled:opacity-50"
            >
              <Sparkles className={`w-3.5 h-3.5 ${isSeeding ? 'animate-spin' : ''}`} />
              <span>{isSeeding ? 'Seeding...' : 'Load Sample Documents'}</span>
            </button>
          </div>

          <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="space-y-1">
              <h4 className="font-bold text-rose-700 text-xs">Clear Knowledge Base</h4>
              <p className="text-[11px] text-slate-500">
                Deletes all documents, vector embeddings from ChromaDB, and reset investigation history.
              </p>
            </div>
            <button
              onClick={handleReset}
              disabled={isResetting || !settings?.reset_enabled}
              title={settings?.reset_enabled ? 'Clear the local document library' : 'Disabled unless ALLOW_DESTRUCTIVE_RESET=true on the backend'}
              className="shrink-0 flex items-center gap-2 px-4 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-xs font-bold transition-all disabled:opacity-50"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>{isResetting ? 'Clearing...' : 'Clear Database'}</span>
            </button>
            {!settings?.reset_enabled && (
              <span className="text-[11px] text-slate-500">
                Reset disabled by backend configuration (safe default).
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
