import {
  ArrowRight,
  CheckCircle2,
  FileText,
  Loader2,
  UploadCloud,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import {
  getWorkspaceSummary,
  processDocument,
  uploadDocument,
} from "../services/api";

import type { WorkspaceRecentDocument } from "../types/api";

function statusTone(status: string) {
  const value = status.toUpperCase();

  if (
    value === "PROCESSED" ||
    value === "COMPLETED" ||
    value === "VERIFIED"
  ) {
    return "text-[#39785B] bg-[#EDF7F1] border-[#D7EBDD]";
  }

  if (value === "FAILED" || value === "ERROR") {
    return "text-[#A55757] bg-[#FBF0F0] border-[#EBD5D5]";
  }

  return "text-[#96733A] bg-[#FBF6E9] border-[#EEE1BE]";
}

export default function Documents() {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [documents, setDocuments] = useState<WorkspaceRecentDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadDocuments() {
    try {
      setLoading(true);
      const summary = await getWorkspaceSummary();
      setDocuments(summary.recent_documents || []);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load documents.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDocuments();
  }, []);

  async function handleUpload(file: File | undefined) {
    if (!file) return;

    try {
      setUploading(true);
      setError("");
      setMessage("");

      const result = await uploadDocument(file);

        setMessage((result.filename || file.name) + " uploaded successfully. Document is ready for processing.");

      

      await loadDocuments();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Document upload failed.",
      );
    } finally {
      setUploading(false);

      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  }

  async function handleProcess(documentId: string) {
    try {
      setProcessingId(documentId);
      setError("");
      setMessage("");

      await processDocument(documentId);

      setMessage("OCR processing completed for the selected document.");
      await loadDocuments();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Document processing failed.",
      );
    } finally {
      setProcessingId(null);
    }
  }

  return (
    <div className="bhoomi-page space-y-7">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#648072]">
          Document workspace
        </p>

        <h1 className="mt-1 text-[30px] font-semibold tracking-[-0.04em] text-[#21362D]">
          Documents
        </h1>

        <p className="mt-2 max-w-2xl text-sm leading-6 text-[#74857D]">
          Upload land records, start processing and open each document's
          verification workspace.
        </p>
      </div>

      <div
        onClick={() => !uploading && inputRef.current?.click()}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          void handleUpload(event.dataTransfer.files?.[0]);
        }}
        className={[
          "group cursor-pointer rounded-2xl border-2 border-dashed",
          "border-[#C9DBD2] bg-[#F8FBF9] px-6 py-10 text-center",
          "transition hover:border-[#7EA38F] hover:bg-[#F4F9F6]",
          uploading ? "pointer-events-none opacity-70" : "",
        ].join(" ")}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff"
          className="hidden"
          onChange={(event) => {
            void handleUpload(event.target.files?.[0]);
          }}
        />

        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[#E8F2EC] text-[#477660] transition group-hover:scale-105">
          {uploading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <UploadCloud className="h-5 w-5" />
          )}
        </div>

        <h2 className="mt-4 text-sm font-semibold text-[#33483F]">
          {uploading ? "Uploading documentÃƒÂ¯Ã‚Â¿Ã‚Â½" : "Upload a land document"}
        </h2>

        <p className="mx-auto mt-1 max-w-md text-xs leading-5 text-[#82908A]">
          Drop a PDF or supported image here, or click to browse your files.
        </p>

        <p className="mt-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-[#9AA7A1]">
          PDF ÃƒÂ¯Ã‚Â¿Ã‚Â½ PNG ÃƒÂ¯Ã‚Â¿Ã‚Â½ JPG ÃƒÂ¯Ã‚Â¿Ã‚Â½ JPEG ÃƒÂ¯Ã‚Â¿Ã‚Â½ TIFF
        </p>
      </div>

      {message && (
        <div className="flex items-start gap-3 rounded-xl border border-[#D8E9DE] bg-[#F3FAF5] p-4 text-xs text-[#39785B]">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{message}</span>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-[#EBD5D5] bg-[#FBF3F3] p-4 text-xs text-[#A55757]">
          <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <section className="overflow-hidden rounded-2xl border border-[#DDE6E2] bg-white shadow-[0_8px_30px_rgba(32,55,45,0.045)]">
        <div className="flex items-center justify-between gap-4 border-b border-[#E8EFEC] px-5 py-5 sm:px-6">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.13em] text-[#71847B]">
              Workspace
            </p>
            <h2 className="mt-1 text-lg font-semibold text-[#2C4339]">
              Recent documents
            </h2>
          </div>

          <span className="rounded-full bg-[#F1F5F3] px-2.5 py-1 text-[10px] font-bold text-[#6C7E76]">
            {documents.length} shown
          </span>
        </div>

        {loading ? (
          <div className="p-10 text-center text-sm text-[#84928C]">
            Loading documentsÃƒÂ¯Ã‚Â¿Ã‚Â½
          </div>
        ) : !documents.length ? (
          <div className="p-12 text-center">
            <FileText className="mx-auto h-8 w-8 text-[#AAB7B1]" />
            <p className="mt-3 text-sm font-semibold text-[#53675E]">
              No documents available
            </p>
            <p className="mt-1 text-xs text-[#89958F]">
              Upload your first document above.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[#E8EFEC]">
            {documents.map((document) => {
              const processing = processingId === document.id;

              return (
                <div
                  key={document.id}
                  className="flex flex-col gap-4 px-5 py-4 transition hover:bg-[#FCFDFC] sm:flex-row sm:items-center sm:px-6"
                >
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#F0F5F2] text-[#58776A]">
                      <FileText className="h-4 w-4" />
                    </div>

                    <div className="min-w-0">
                      <Link
                        to={`/documents/${document.id}`}
                        className="block truncate text-sm font-semibold text-[#344940] hover:text-[#315F4D]"
                      >
                        {document.original_filename}
                      </Link>

                      <p className="mt-1 text-[10px] text-[#89958F]">
                        Added{" "}
                        {new Date(document.created_at).toLocaleDateString(
                          "en-IN",
                          {
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                          },
                        )}
                      </p>
                    </div>
                  </div>

                  <span
                    className={[
                      "w-fit rounded-full border px-2.5 py-1",
                      "text-[10px] font-bold uppercase tracking-[0.05em]",
                      statusTone(document.status),
                    ].join(" ")}
                  >
                    {document.status.replace(/_/g, " ")}
                  </span>

                  <div className="flex items-center gap-2">
                    {document.status.toUpperCase() !== "PROCESSED" && (
                      <button
                        type="button"
                        disabled={processing}
                        onClick={() => void handleProcess(document.id)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-[#D6E3DD] bg-white px-3 py-2 text-[11px] font-bold text-[#47725F] hover:bg-[#F4F9F6] disabled:opacity-50"
                      >
                        {processing && (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        )}
                        {processing ? "Processing" : "Process"}
                      </button>
                    )}

                    <Link
                      to={`/documents/${document.id}`}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-[#315F4D] px-3 py-2 text-[11px] font-bold text-white hover:bg-[#274F3F]"
                    >
                      Open
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
