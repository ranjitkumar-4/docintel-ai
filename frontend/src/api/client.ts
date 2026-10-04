import {
  DocumentInfo,
  DocumentDetail,
  InvestigationResult,
  ConflictItem,
  DashboardStats,
  SystemSettings
} from '../types';

const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const API_BASE = `${API_ORIGIN}/api`;

export interface HealthStatus {
  status: 'healthy' | 'degraded';
  backend_online: boolean;
  operational: boolean;
  indexed_chunks: number;
  total_documents: number;
  ocr_available: boolean;
  vector_store_ready: boolean;
  vector_store_error: string | null;
  persistence_error: string | null;
  embedding_profile: {
    embedding_provider: string;
    embedding_model: string;
    embedding_dimension: number;
  } | null;
  reset_enabled: boolean;
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE}/dashboard/stats`);
  if (!res.ok) throw new Error('Failed to load dashboard statistics');
  return res.json();
}

export async function fetchDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function fetchDocumentDetail(docId: string): Promise<DocumentDetail> {
  const res = await fetch(`${API_BASE}/documents/${docId}`);
  if (!res.ok) throw new Error('Failed to fetch document detail');
  return res.json();
}

export async function uploadDocuments(
  files: File[],
  onProgressStep?: (step: string) => void
): Promise<DocumentInfo[]> {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }

  onProgressStep?.('Uploading files to server...');
  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(errorData.detail || 'Upload failed');
  }

  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${docId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete document');
}

export async function reindexDocument(docId: string): Promise<DocumentInfo> {
  const res = await fetch(`${API_BASE}/documents/${docId}/reindex`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to re-index document');
  return res.json();
}

export async function seedDemoDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${API_BASE}/documents/seed-demo`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to seed demo documents');
  return res.json();
}

export async function askQuestion(
  question: string,
  documentIds?: string[]
): Promise<InvestigationResult> {
  const res = await fetch(`${API_BASE}/investigation/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      document_ids: documentIds && documentIds.length > 0 ? documentIds : undefined,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Investigation failed' }));
    throw new Error(errorData.detail || 'Investigation failed');
  }

  return res.json();
}

export async function fetchInvestigationHistory(): Promise<InvestigationResult[]> {
  const res = await fetch(`${API_BASE}/investigation/history`);
  if (!res.ok) throw new Error('Failed to load history');
  return res.json();
}

export async function fetchInvestigationById(id: string): Promise<InvestigationResult> {
  const res = await fetch(`${API_BASE}/investigation/${id}`);
  if (!res.ok) throw new Error('Failed to load investigation');
  return res.json();
}

export async function shareInvestigation(id: string): Promise<{ investigation_id: string; share_url: string }> {
  const res = await fetch(`${API_BASE}/investigation/${id}/share`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to generate share link');
  return res.json();
}

export async function fetchConflicts(): Promise<ConflictItem[]> {
  const res = await fetch(`${API_BASE}/conflicts`);
  if (!res.ok) throw new Error('Failed to load conflicts');
  return res.json();
}

export async function resolveConflict(conflictId: string, status: 'resolved' | 'unresolved'): Promise<ConflictItem> {
  const res = await fetch(`${API_BASE}/conflicts/${conflictId}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error('Failed to resolve conflict');
  return res.json();
}

export async function fetchSettings(): Promise<SystemSettings> {
  const res = await fetch(`${API_BASE}/settings`);
  if (!res.ok) throw new Error('Failed to fetch settings');
  return res.json();
}

export async function updateSettings(settings: Partial<SystemSettings>): Promise<void> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to update settings');
}

export async function resetDatabase(): Promise<void> {
  const res = await fetch(`${API_BASE}/system/reset`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to reset system');
}
