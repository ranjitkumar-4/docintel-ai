export interface DocumentChunk {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number;
  text: string;
  file_type: string;
  metadata?: Record<string, any>;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  file_type: string;
  file_path: string;
  file_size_bytes: number;
  pages: number;
  chunks_count: number;
  text_extracted_chars: number;
  status: 'uploading' | 'extracting' | 'chunking' | 'indexing' | 'indexed' | 'failed';
  upload_status: 'SUCCESS' | 'FAILED' | 'PARTIAL';
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentInfo {
  chunks: DocumentChunk[];
}

export interface SourceReference {
  document_id: string;
  filename: string;
  page_number: number;
  chunk_id: string;
  text: string;
  file_type: string;
  relevance_score: number;
  page_number_approximate?: boolean;
}

export interface ConflictingSource {
  document_name: string;
  page_number: number;
  statement: string;
  chunk_id?: string;
  page_number_approximate?: boolean;
}

export interface InvestigationResult {
  id: string;
  question: string;
  answer: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'NOT FOUND';
  confidence_reason: string;
  uncertainty_reason?: string;
  sources: SourceReference[];
  conflict_detected: boolean;
  conflict_topic?: string;
  conflict_summary?: string;
  conflicting_sources: ConflictingSource[];
  recommendation?: string;
  is_uncertain_or_not_found: boolean;
  processing_time_ms: number;
  created_at: string;
}

export interface ConflictItem {
  id: string;
  topic: string;
  document_a_name: string;
  document_a_page: number;
  document_a_page_approximate?: boolean;
  document_a_statement: string;
  document_b_name: string;
  document_b_page: number;
  document_b_page_approximate?: boolean;
  document_b_statement: string;
  confidence: string;
  status: 'unresolved' | 'resolved';
  recommendation?: string;
  investigation_id?: string;
  detected_at: string;
}

export interface DashboardStats {
  documents_count: number;
  indexed_sections_count: number;
  questions_asked_count: number;
  conflicts_detected_count: number;
  recent_investigations: InvestigationResult[];
}

export interface SystemSettings {
  llm_provider: string;
  has_openai_key: boolean;
  has_gemini_key: boolean;
  chunk_size: number;
  chunk_overlap: number;
  embedding_model: string;
  similarity_threshold: number;
  embedding_provider: string;
  embedding_dimension: number | null;
  vector_store_ready: boolean;
  vector_store_error: string | null;
  reset_enabled: boolean;
}
