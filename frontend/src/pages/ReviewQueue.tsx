import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileSearch,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getWorkspaceNotifications } from "../services/api";
import type { WorkspaceNotification } from "../types/api";

function severity(status: string) {
  const value = status.toUpperCase();

  if (value === "FAIL" || value === "REJECTED") {
    return {
      label: "High attention",
      className: "bg-[#FBF0F0] text-[#A55757] border-[#EBD5D5]",
      icon: ShieldAlert,
    };
  }

  return {
    label: "Review",
    className: "bg-[#FBF6E9] text-[#96733A] border-[#EEE1BE]",
    icon: AlertTriangle,
  };
}

export default function ReviewQueue() {
  const [items, setItems] = useState<WorkspaceNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    try {
      setLoading(true);
      setError("");

      const response = await getWorkspaceNotifications();
      setItems(response.items || []);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load the review queue.",
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
            Human verification
          </p>

          <h1 className="mt-1 text-[30px] font-semibold tracking-[-0.04em] text-[#21362D]">
            Review Queue
          </h1>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#74857D]">
            Review fields that validation has surfaced as uncertain,
            conflicting or requiring human attention.
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

      <section className="rounded-2xl border border-[#DDE6E2] bg-white shadow-[0_8px_30px_rgba(32,55,45,0.045)]">
        <div className="flex items-center justify-between border-b border-[#E8EFEC] px-5 py-4 sm:px-6">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.13em] text-[#71847B]">
              Queue
            </p>
            <h2 className="mt-1 text-lg font-semibold text-[#2C4339]">
              Fields requiring attention
            </h2>
          </div>

          <span className="rounded-full bg-[#FBF6E9] px-2.5 py-1 text-[10px] font-bold text-[#96733A]">
            {items.length} items
          </span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-sm text-[#84928C]">
            Loading review queue�
          </div>
        ) : !items.length ? (
          <div className="p-14 text-center">
            <CheckCircle2 className="mx-auto h-9 w-9 text-[#5B876E]" />
            <h3 className="mt-3 text-sm font-semibold text-[#53675E]">
              Nothing requires attention
            </h3>
            <p className="mt-1 text-xs text-[#89958F]">
              The workspace currently has no notification items to review.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[#E8EFEC]">
            {items.map((item) => {
              const meta = severity(item.validation_status);
              const Icon = meta.icon;

              return (
                <div
                  key={item.id}
                  className="flex flex-col gap-4 px-5 py-5 transition hover:bg-[#FCFDFC] sm:flex-row sm:items-center sm:px-6"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#FBF6E9] text-[#96733A]">
                    <Icon className="h-4 w-4" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold capitalize text-[#3D5148]">
                      {item.field_name.replace(/_/g, " ")}
                    </p>

                    <p className="mt-1 truncate text-xs text-[#74857D]">
                      {item.document_filename}
                    </p>

                    <div className="mt-2 flex flex-wrap gap-2">
                      <span
                        className={[
                          "rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase",
                          meta.className,
                        ].join(" ")}
                      >
                        {meta.label}
                      </span>

                      <span className="rounded-full bg-[#F3F6F5] px-2 py-0.5 text-[9px] font-bold text-[#74857D]">
                        {item.validation_status}
                      </span>

                      {item.page_number && (
                        <span className="rounded-full bg-[#F3F6F5] px-2 py-0.5 text-[9px] font-bold text-[#74857D]">
                          Page {item.page_number}
                        </span>
                      )}
                    </div>
                  </div>

                  <Link
                    to={`/documents/${item.document_id}`}
                    className="inline-flex w-fit items-center gap-1.5 rounded-lg bg-[#315F4D] px-3 py-2 text-[11px] font-bold text-white hover:bg-[#274F3F]"
                  >
                    <FileSearch className="h-3.5 w-3.5" />
                    Review
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
