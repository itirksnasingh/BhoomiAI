import type {
  AuditHistory,
  DocumentRecord,
  ExtractedField,
  ExtractionSummary,
  LoginResponse,
  ProcessDocumentResponse,
  ReviewFieldResponse,
  UploadedDocument,
  User,
  ValidationRunResponse,
  ValidationSummary,
  WorkspaceAudit,
  WorkspaceNotifications,
  WorkspaceSummary,
} from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "bhoomiai_access_token";
const USER_KEY = "bhoomiai_user";

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") || "";

  let data: unknown;

  if (contentType.includes("application/json")) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    if (typeof data === "object" && data !== null && "detail" in data) {
      const detail = (data as { detail?: unknown }).detail;

      if (typeof detail === "string") {
        throw new Error(detail);
      }

      if (Array.isArray(detail)) {
        throw new Error(
          detail
            .map((item) =>
              typeof item === "object" &&
              item !== null &&
              "msg" in item
                ? String((item as { msg: unknown }).msg)
                : String(item),
            )
            .join(", "),
        );
      }
    }

    if (typeof data === "object" && data !== null && "message" in data) {
      const message = (data as { message?: unknown }).message;

      if (typeof message === "string") {
        throw new Error(message);
      }
    }

    if (typeof data === "string" && data.trim()) {
      throw new Error(data);
    }

    throw new Error(`Request failed with status ${response.status}`);
  }

  return data as T;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as User;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function authHeaders(): HeadersInit {
  const token = getToken();

  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...authHeaders(),
      ...(init.headers || {}),
    },
  });

  if (response.status === 401) {
    logout();
    window.dispatchEvent(new Event("bhoomiai:unauthorized"));
  }

  return parseResponse<T>(response);
}

/* -------------------------------------------------------------------------- */
/* AUTH                                                                       */
/* -------------------------------------------------------------------------- */

export async function login(
  email: string,
  password: string,
): Promise<{ token: LoginResponse; user: User }> {
  const token = await request<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: email.trim(),
      password,
    }),
  });

  localStorage.setItem(TOKEN_KEY, token.access_token);

  try {
    const user = await getCurrentUser();

    return {
      token,
      user,
    };
  } catch (error) {
    logout();
    throw error;
  }
}

export async function getCurrentUser(): Promise<User> {
  const user = await request<User>("/api/v1/auth/me");

  localStorage.setItem(USER_KEY, JSON.stringify(user));

  return user;
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);

    return response.ok;
  } catch {
    return false;
  }
}

/* -------------------------------------------------------------------------- */
/* WORKSPACE                                                                  */
/* -------------------------------------------------------------------------- */

export async function getWorkspaceSummary(): Promise<WorkspaceSummary> {
  return request<WorkspaceSummary>("/api/v1/workspace/summary");
}

export async function getWorkspaceNotifications(): Promise<WorkspaceNotifications> {
  return request<WorkspaceNotifications>(
    "/api/v1/workspace/notifications",
  );
}

export async function getWorkspaceAudit(): Promise<WorkspaceAudit> {
  return request<WorkspaceAudit>("/api/v1/workspace/audit");
}

/* -------------------------------------------------------------------------- */
/* DOCUMENTS                                                                  */
/* -------------------------------------------------------------------------- */

export async function uploadDocument(
  file: File,
): Promise<UploadedDocument> {
  const formData = new FormData();

  formData.append("file", file);

  return request<UploadedDocument>("/api/v1/documents/upload", {
    method: "POST",
    body: formData,
  });
}

/**
 * Full document processing pipeline.
 *
 * This is the preferred entry point for the Document Workspace because
 * extraction requires a completed OCR run.
 *
 * Pipeline:
 * ingestion → OCR → classification → extraction → evidence
 */
export async function runDocumentPipeline(
  documentId: string,
): Promise<Record<string, unknown>> {
  if (!documentId) {
    throw new Error("Document ID is missing.");
  }

  return request<Record<string, unknown>>(
    `/api/v1/documents/${documentId}/run`,
    {
      method: "POST",
    },
  );
}

/**
 * Lower-level document processing endpoint.
 *
 * Kept for screens/workflows that specifically need the page-processing
 * operation without invoking the full pipeline.
 */
export async function processDocument(
  documentId: string,
): Promise<ProcessDocumentResponse> {
  if (!documentId) {
    throw new Error("Document ID is missing.");
  }

  return request<ProcessDocumentResponse>(
    `/api/v1/documents/${documentId}/process`,
    {
      method: "POST",
    },
  );
}

/**
 * Extraction-only endpoint.
 *
 * Do not use this as the primary "Re-extract" action unless OCR has
 * already completed successfully.
 */
export async function extractDocument(
  documentId: string,
): Promise<ExtractionSummary> {
  if (!documentId) {
    throw new Error("Document ID is missing.");
  }

  return request<ExtractionSummary>(
    `/api/v1/documents/${documentId}/extract`,
    {
      method: "POST",
    },
  );
}

export async function getDocumentFields(
  documentId: string,
): Promise<ExtractedField[]> {
  if (!documentId) {
    throw new Error("Document ID is missing.");
  }

  return request<ExtractedField[]>(
    `/api/v1/documents/${documentId}/fields`,
  );
}

/* -------------------------------------------------------------------------- */
/* VALIDATION                                                                 */
/* -------------------------------------------------------------------------- */

export async function validateDocument(
  documentId: string,
): Promise<ValidationRunResponse> {
  if (!documentId) {
    throw new Error("Document ID is missing.");
  }

  return request<ValidationRunResponse>(
    `/api/v1/documents/${documentId}/validate`,
    {
      method: "POST",
    },
  );
}

export async function getValidation(
  documentId: string,
): Promise<ValidationSummary> {
  if (!documentId) {
    throw new Error("Document ID is missing.");
  }

  return request<ValidationSummary>(
    `/api/v1/documents/${documentId}/validation`,
  );
}

/* -------------------------------------------------------------------------- */
/* REVIEW                                                                     */
/* -------------------------------------------------------------------------- */

export async function reviewField(
  fieldId: string,
  action: string,
  newValue?: string,
  reason?: string,
): Promise<ReviewFieldResponse> {
  if (!fieldId) {
    throw new Error("Field ID is missing.");
  }

  return request<ReviewFieldResponse>(
    `/api/v1/documents/fields/${fieldId}/review`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        action,
        new_value: newValue ?? null,
        reason: reason ?? null,
      }),
    },
  );
}

/* -------------------------------------------------------------------------- */
/* AUDIT                                                                      */
/* -------------------------------------------------------------------------- */

export async function getAuditHistory(
  documentId: string,
): Promise<AuditHistory> {
  if (!documentId) {
    throw new Error("Document ID is missing.");
  }

  return request<AuditHistory>(
    `/api/v1/documents/${documentId}/audit`,
  );
}

/* -------------------------------------------------------------------------- */
/* DOCUMENT RECORD ADAPTER                                                    */
/* -------------------------------------------------------------------------- */

export function uploadedToDocumentRecord(
  document: UploadedDocument,
): DocumentRecord {
  return {
    id: document.document_id,
    original_filename: document.filename,
    status: document.status,
    created_at: new Date().toISOString(),
  };
}

/* -------------------------------------------------------------------------- */
/* DOCUMENT PAGES / SOURCE EVIDENCE                                           */
/* -------------------------------------------------------------------------- */

export interface DocumentPageSummary {
  id: string;
  document_id: string;
  page_number: number;
}

export async function getDocumentPages(
  documentId: string,
): Promise<DocumentPageSummary[]> {
  if (!documentId) {
    throw new Error("Document ID is missing.");
  }

  return request<DocumentPageSummary[]>(
    `/api/v1/documents/${documentId}/pages`,
  );
}

/**
 * Fetch a protected source-page image.
 *
 * The backend intentionally returns the image as a Blob instead of exposing
 * the storage path directly.
 */
export async function getDocumentPageImage(
  documentId: string,
  pageId: string,
): Promise<Blob> {
  if (!documentId || !pageId) {
    throw new Error("Document or page ID is missing.");
  }

  const response = await fetch(
    `${API_BASE_URL}/api/v1/documents/${documentId}/pages/${pageId}/image`,
    {
      headers: {
        Accept: "image/*",
        ...authHeaders(),
      },
    },
  );

  if (response.status === 401) {
    logout();
    window.dispatchEvent(new Event("bhoomiai:unauthorized"));
  }

  if (!response.ok) {
    let message =
      `Source page request failed with status ${response.status}`;

    try {
      const contentType =
        response.headers.get("content-type") || "";

      if (contentType.includes("application/json")) {
        const data = await response.json();

        if (
          typeof data === "object" &&
          data !== null &&
          "detail" in data
        ) {
          const detail = (data as { detail?: unknown }).detail;

          if (typeof detail === "string") {
            message = detail;
          } else if (Array.isArray(detail)) {
            message = detail
              .map((item) =>
                typeof item === "object" &&
                item !== null &&
                "msg" in item
                  ? String((item as { msg: unknown }).msg)
                  : String(item),
              )
              .join(", ");
          }
        }
      }
    } catch {
      // Keep the fallback error message.
    }

    throw new Error(message);
  }

  return response.blob();
}