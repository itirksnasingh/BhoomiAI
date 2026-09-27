export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
  user?: User;
}

export interface WorkspaceRecentDocument {
  id: string;
  original_filename: string;
  status: string;
  created_at: string;
}

export interface WorkspaceSummary {
  total_documents: number;
  processed_documents: number;
  pending_documents: number;
  failed_documents: number;
  fields_needing_review: number;
  validation_passed: number;
  validation_review: number;
  validation_failed: number;
  total_extracted_fields: number;
  average_confidence: number | null;
  recent_documents: WorkspaceRecentDocument[];
}

export interface WorkspaceNotification {
  id: string;
  type: string;
  severity: string;
  title: string;
  message: string;
  document_id: string;
  field_id: string;
  document_filename: string;
  field_name: string;
  validation_status: string;
  page_number: number | null;
  created_at: string;
}

export interface WorkspaceNotifications {
  total: number;
  unread: number;
  items: WorkspaceNotification[];
}

export interface UploadedDocument {
  document_id: string;
  document_file_id?: string;
  status: string;
  filename: string;
  file_size_bytes?: number;
  sha256?: string;
  pages_created?: number;
  message?: string;
}

export interface OCRRunSummary {
  ocr_run_id: string;
  status: string;
  engine: string;
  engine_version: string | null;
  language: string;
  confidence: number | null;
}

export interface ProcessDocumentResponse {
  document_id: string;
  status: string;
  ocr_runs: OCRRunSummary[];
}

export interface DocumentRecord {
  id: string;
  original_filename: string;
  status: string;
  created_at: string;
}

export interface ExtractedField {
  id: string;
  document_page_id: string;
  extraction_run_id: string | null;
  source_ocr_run_id: string | null;
  field_name: string;
  value: string | null;
  normalized_value: string | null;
  confidence: number | null;
  extraction_method: string;
  evidence_bbox: Record<string, unknown> | null;
  validation_status: string;
}

export interface ExtractionSummary {
  document_id: string;
  extraction_run_id: string;
  status: string;
  engine: string;
  engine_version: string | null;
  confidence: number | null;
  fields_extracted: number;
  fields: ExtractedField[];
}

export interface ValidationResult {
  id: string;
  validation_run_id: string;
  extracted_field_id: string;
  field_name: string;
  rule_name: string;
  status: string;
  message: string;
  confidence: number | null;
}

export interface ValidationSummary {
  document_id: string;
  validation_run_id: string;
  status: string;
  engine: string;
  engine_version: string | null;
  confidence: number | null;
  total_results: number;
  pass_count: number;
  warning_count: number;
  review_count: number;
  results: ValidationResult[];
}

export interface ValidationRunResponse {
  document_id: string;
  validation_run_id: string;
  status: string;
  engine: string;
  engine_version: string | null;
  confidence: number | null;
  total_results: number;
  results: Array<{
    field_name: string;
    rule_name: string;
    status: string;
    message: string;
    confidence: number | null;
  }>;
}

export interface ReviewFieldResponse {
  field_id: string;
  field_name: string;
  action: string;
  old_value: string | null;
  new_value: string | null;
  validation_status: string;
  reason: string | null;
  audit_log_id: string;
}

export interface AuditLog {
  id: string;
  document_id: string;
  document_filename?: string;
  extracted_field_id?: string | null;
  action: string;
  old_value?: string | null;
  new_value?: string | null;
  decision?: string | null;
  reason?: string | null;
  reviewer_id?: string | null;
  created_at: string;
}

export interface AuditHistory {
  document_id: string;
  total: number;
  logs: AuditLog[];
}

export interface WorkspaceAudit {
  total: number;
  items: AuditLog[];
}
