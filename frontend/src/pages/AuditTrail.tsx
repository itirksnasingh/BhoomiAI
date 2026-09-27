import {
  CheckCircle2,
  Clock3,
  FileText,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState } from "react";

import { getWorkspaceSummary } from "../services/api";
import type { WorkspaceRecentDocument } from "../types/api";

function prettyStatus(status: string) {
  return status.replace(/_/g, " ");
}

export default function AuditTrail() {
  const [documents, setDocuments] = useState<WorkspaceRecentDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    try {
      setLoading(true);
      setError("");

      const summary = await getWorkspaceSummary();
      setDocuments(summary.recent_documents || []);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load audit activity.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="bhoomi-page space-y-7">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#648072]">
            Traceability
          </p>

          <h1 className="mt-1 text-[30px] font-semibold tracking-[-0.04em] text-[#21362D]">
            Audit Trail
          </h1>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#74857D]">
            A chronological workspace view of recently registered documents
            and their current processing state.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex w-fit items-center gap-2 rounded-xl border border-[#D7E3DE] bg-white px-3.5 py-2.5 text-xs font-bold text-[#4A6F60] hover:bg-[#F7FAF8]"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-[#EBD5D5] bg-[#FBF3F3] p-4 text-xs text-[#A55757]">
          {error}
        </div>
      )}

      <section className="rounded-2xl border border-[#DDE6E2] bg-white p-5 shadow-[0_8px_30px_rgba(32,55,45,0.045)] sm:p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#EDF5F0] text-[#4B7863]">
            <ShieldCheck className="h-5 w-5" />
          </div>

          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.13em] text-[#71847B]">
              Activity
            </p>

            <h2 className="mt-1 text-lg font-semibold text-[#2C4339]">
              Recent document activity
            </h2>
          </div>
        </div>

        {loading ? (
          <div className="py-12 text-center text-sm text-[#84928C]">
            Loading activity�
          </div>
        ) : !documents.length ? (
          <div className="py-12 text-center">
            <Clock3 className="mx-auto h-8 w-8 text-[#AAB7B1]" />
            <p className="mt-3 text-sm font-semibold text-[#53675E]">
              No recent activity
            </p>
          </div>
        ) : (
          <div className="mt-7 ml-2 border-l border-[#DDE7E2] pl-6">
            <div className="space-y-7">
              {documents.map((document) => (
                <div key={document.id} className="relative">
                  <span className="absolute -left-[33px] top-0.5 flex h-5 w-5 items-center justify-center rounded-full border-4 border-white bg-[#5B826E]">
                    <span className="h-1.5 w-1.5 rounded-full bg-white" />
                  </span>

                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <FileText className="h-3.5 w-3.5 text-[#6A8177]" />

                        <p className="truncate text-sm font-semibold text-[#3D5148]">
                          {document.original_filename}
                        </p>
                      </div>

                      <p className="mt-1 text-xs text-[#7D8C85]">
                        Document status:{" "}
                        <span className="font-semibold text-[#596D64]">
                          {prettyStatus(document.status)}
                        </span>
                      </p>

                      <p className="mt-1 text-[10px] text-[#9AA59F]">
                        {new Date(document.created_at).toLocaleString(
                          "en-IN",
                          {
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          },
                        )}
                      </p>
                    </div>

                    <CheckCircle2 className="hidden h-4 w-4 text-[#5B876E] sm:block" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
