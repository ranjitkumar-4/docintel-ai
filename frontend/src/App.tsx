import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DashboardView } from './components/DashboardView';
import { DocumentsView } from './components/DocumentsView';
import { InvestigationView } from './components/InvestigationView';
import { ConflictsView } from './components/ConflictsView';
import { HistoryView } from './components/HistoryView';
import { SettingsView } from './components/SettingsView';
import { DocumentUploadModal } from './components/DocumentUploadModal';
import { SourceInspectorDrawer } from './components/SourceInspectorDrawer';
import { ShareModal } from './components/ShareModal';
import {
  DocumentInfo,
  DashboardStats,
  ConflictItem,
  InvestigationResult,
  SourceReference,
} from './types';
import {
  fetchDashboardStats,
  fetchDocuments,
  fetchConflicts,
  fetchInvestigationHistory,
  seedDemoDocuments,
  fetchHealth,
  fetchInvestigationById,
  HealthStatus,
} from './api/client';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [investigations, setInvestigations] = useState<InvestigationResult[]>([]);
  const [stats, setStats] = useState<DashboardStats>({
    documents_count: 0,
    indexed_sections_count: 0,
    questions_asked_count: 0,
    conflicts_detected_count: 0,
    recent_investigations: [],
  });

  const [currentInvestigation, setCurrentInvestigation] = useState<InvestigationResult | null>(null);
  const [inspectedSource, setInspectedSource] = useState<SourceReference | null>(null);
  const [sharedInvestigation, setSharedInvestigation] = useState<InvestigationResult | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    loadAllData();
    checkUrlHashForInvestigation();
  }, []);

  const loadAllData = async () => {
    const results = await Promise.allSettled([
      fetchDashboardStats(),
      fetchDocuments(),
      fetchConflicts(),
      fetchInvestigationHistory(),
      fetchHealth(),
    ]);
    const [statsResult, docsResult, conflictsResult, historyResult, healthResult] = results;
    const errors = results
      .filter((result): result is PromiseRejectedResult => result.status === 'rejected')
      .map((result) => result.reason instanceof Error ? result.reason.message : 'Unknown API error');

    if (statsResult.status === 'fulfilled') setStats(statsResult.value);
    if (docsResult.status === 'fulfilled') setDocuments(docsResult.value);
    if (conflictsResult.status === 'fulfilled') setConflicts(conflictsResult.value);
    if (historyResult.status === 'fulfilled') setInvestigations(historyResult.value);
    setHealth(healthResult.status === 'fulfilled' ? healthResult.value : null);
    setLoadError(errors.length ? `Some project data could not be loaded: ${errors.join('; ')}` : null);
  };

  const checkUrlHashForInvestigation = async () => {
    const hash = window.location.hash;
    if (hash.startsWith('#investigation-')) {
      const invId = hash.replace('#investigation-', '');
      try {
        const inv = await fetchInvestigationById(invId);
        if (inv) {
          setCurrentInvestigation(inv);
          setCurrentTab('investigation');
        }
      } catch (err) {
        console.error('Failed to load shared investigation from hash:', err);
      }
    }
  };

  const handleSeedDemo = async () => {
    setIsSeeding(true);
    try {
      await seedDemoDocuments();
      await loadAllData();
    } catch (err: any) {
      alert(`Error loading sample documents: ${err.message}`);
    } finally {
      setIsSeeding(false);
    }
  };

  const handleSelectInvestigation = (inv?: InvestigationResult) => {
    if (inv) setCurrentInvestigation(inv);
    setCurrentTab('investigation');
  };

  const handleInvestigateTopic = (_topic: string) => {
    setCurrentTab('investigation');
  };

  const getPageTitle = () => {
    switch (currentTab) {
      case 'dashboard':
        return 'Intelligence Dashboard';
      case 'documents':
        return 'Document Library';
      case 'investigation':
        return 'Document Investigation';
      case 'conflicts':
        return 'Policy Conflicts';
      case 'history':
        return 'Investigation History';
      case 'settings':
        return 'System Settings';
      default:
        return 'DocIntel AI';
    }
  };

  const getPageSubtitle = () => {
    switch (currentTab) {
      case 'dashboard':
        return 'Holistic overview of indexed documents, conflict alerts, and recent investigations';
      case 'documents':
        return 'Manage and inspect multi-format documents, vector chunks, and parsing statuses';
      case 'investigation':
        return 'Natural-language queries with grounded source citations and conflict detection';
      case 'conflicts':
        return 'Review contradicting statements identified across multiple official documents';
      case 'history':
        return 'Audit trail of past investigations, citations, and confidence analyses';
      case 'settings':
        return 'Configure the LLM backend, chunking strategy, and vector storage';
      default:
        return undefined;
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 font-sans">
      {/* Persistent Left Sidebar */}
      <Sidebar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        conflictsCount={conflicts.filter((c) => c.status === 'unresolved').length}
        backendOnline={health !== null}
        vectorReady={health?.vector_store_ready ?? false}
        ocrAvailable={health?.ocr_available ?? false}
        totalChunks={stats.indexed_sections_count}
      />

      {/* Main App Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <Header
          title={getPageTitle()}
          subtitle={getPageSubtitle()}
          onOpenUpload={() => setIsUploadOpen(true)}
          onSeedDemo={handleSeedDemo}
          isSeeding={isSeeding}
          backendOnline={health !== null}
          onRefresh={loadAllData}
        />

        {/* Tab Views */}
        {health && !health.vector_store_ready && (
          <div role="alert" className="mx-8 mt-4 p-3 rounded-lg border border-rose-200 bg-rose-50 text-xs text-rose-800">
            Vector database unavailable: {health.vector_store_error || 'The configured embedding index is not ready.'}
          </div>
        )}
        {loadError && (
          <div role="alert" className="mx-8 mt-4 p-3 rounded-lg border border-rose-200 bg-rose-50 text-xs text-rose-800">
            {loadError}
          </div>
        )}
        {health?.persistence_error && (
          <div role="alert" className="mx-8 mt-4 p-3 rounded-lg border border-amber-200 bg-amber-50 text-xs text-amber-800">
            Saved document state could not be fully restored: {health.persistence_error}
          </div>
        )}
        {health?.backend_online && !health.ocr_available && (
          <div role="status" className="mx-8 mt-4 p-3 rounded-lg border border-amber-200 bg-amber-50 text-xs text-amber-800">
            OCR Unavailable — install Tesseract on the backend host to process JPG/JPEG/PNG and scanned PDF pages.
          </div>
        )}
        <main className="flex-1 overflow-y-auto">
          {currentTab === 'dashboard' && (
            <DashboardView
              stats={stats}
              onOpenUpload={() => setIsUploadOpen(true)}
              onOpenInvestigation={handleSelectInvestigation}
              onNavigateTab={(tab) => setCurrentTab(tab)}
              onSeedDemo={handleSeedDemo}
              isSeeding={isSeeding}
              backendOnline={health !== null}
            />
          )}

          {currentTab === 'documents' && (
            <DocumentsView
              documents={documents}
              onRefresh={loadAllData}
              onOpenUpload={() => setIsUploadOpen(true)}
            />
          )}

          {currentTab === 'investigation' && (
            <InvestigationView
              documents={documents}
              currentInvestigation={currentInvestigation}
              setCurrentInvestigation={setCurrentInvestigation}
              onOpenSourceInspector={(src) => setInspectedSource(src)}
              onOpenShareModal={(inv) => setSharedInvestigation(inv)}
            />
          )}

          {currentTab === 'conflicts' && (
            <ConflictsView
              conflicts={conflicts}
              onRefresh={loadAllData}
              onInvestigateTopic={handleInvestigateTopic}
            />
          )}

          {currentTab === 'history' && (
            <HistoryView
              investigations={investigations}
              onSelectInvestigation={handleSelectInvestigation}
              onNavigateInvestigation={() => setCurrentTab('investigation')}
            />
          )}

          {currentTab === 'settings' && (
            <SettingsView
              onSettingsChanged={loadAllData}
              onSeedDemo={handleSeedDemo}
              isSeeding={isSeeding}
            />
          )}
        </main>
      </div>

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={() => {
          loadAllData();
        }}
      />

      {/* Slide-over Source Inspector Drawer */}
      <SourceInspectorDrawer
        source={inspectedSource}
        onClose={() => setInspectedSource(null)}
      />

      {/* Share Investigation Modal */}
      <ShareModal
        investigation={sharedInvestigation}
        onClose={() => setSharedInvestigation(null)}
      />
    </div>
  );
};

export default App;
