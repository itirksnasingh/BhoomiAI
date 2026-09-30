import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  FileText,
  ShieldAlert,
  Upload,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  getWorkspaceNotifications,
  getWorkspaceSummary,
} from "../services/api";

import type {
  WorkspaceNotification,
  WorkspaceSummary,
} from "../types/api";

import { MetricCard } from "../components/ui/MetricCard";
import { SectionHeading, Surface } from "../components/ui/Surface";
import { StatusPill } from "../components/ui/StatusPill";

function formatDate(value: string) {
  try {
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function documentTone(status: string) {
  const value = status.toUpperCase();

  if (
    value === "PROCESSED" ||
    value === "VERIFIED" ||
    value === "COMPLETED"
  ) {
    return "success" as const;
  }

  if (
    value === "FAILED" ||
    value === "ERROR"
  ) {
    return "danger" as const;
  }

  if (
    value === "REVIEW" ||
    value === "REVIEW_REQUIRED"
  ) {
    return "warning" as const;
  }

  return "neutral" as const;
}

export default function Dashboard() {
  const [summary, setSummary] = useState<WorkspaceSummary | null>(null);
  const [notifications, setNotifications] = useState<WorkspaceNotification[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadDashboard() {
    try {
      setLoading(true);
      setError("");

      const [workspace, notificationResponse] = await Promise.all([
        getWorkspaceSummary(),
        getWorkspaceNotifications(),
      ]);

      setSummary(workspace);
      setNotifications(notificationResponse.items || []);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load workspace information.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  const averageConfidence =
    summary?.average_confidence === null ||
    summary?.average_confidence === undefined
      ? "..."
      : `${Math.round((summary.average_confidence > 1 ? summary.average_confidence / 100 : summary.average_confidence) * 100)}%`;

  return (
    <div className="bhoomi-page space-y-7">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#648072]">
            READ ... VERIFY ... TRUST
          </p>

          <h1 className="mt-1 text-[30px] font-semibold tracking-[-0.04em] text-[#21362D]">
            Land record intelligence
          </h1>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#74857D]">
            Monitor document processing, validation and records that need
            human attention from one workspace.
          </p>
        </div>

        <Link
          to="/documents"
          className="inline-flex w-fit items-center gap-2 rounded-xl bg-[#315F4D] px-4 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-[#274F3F]"
        >
          <Upload className="h-4 w-4" />
          Upload document
        </Link>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-2xl border border-[#EBD5D5] bg-[#FBF3F3] p-4 text-sm text-[#945151]">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-semibold">Workspace data unavailable</p>
            <p className="mt-1 text-xs leading-5">{error}</p>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Total documents"
          value={loading ? "..." : summary?.total_documents ?? "..."}
          detail="Documents registered in workspace"
          icon={<FileText className="h-4 w-4" />}
        />

        <MetricCard
          label="Processed"
          value={loading ? "..." : summary?.processed_documents ?? "..."}
          detail="Completed document processing"
          icon={<CheckCircle2 className="h-4 w-4" />}
          tone="green"
        />

        <MetricCard
          label="Needs review"
          value={loading ? "..." : summary?.fields_needing_review ?? "..."}
          detail="Fields requiring attention"
          icon={<ShieldAlert className="h-4 w-4" />}
          tone="amber"
        />

        <MetricCard
          label="Average confidence"
          value={loading ? "..." : averageConfidence}
          detail="Available extraction confidence"
          icon={<Clock3 className="h-4 w-4" />}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.45fr_0.85fr]">
        <Surface className="overflow-hidden">
          <div className="p-5 sm:p-6">
            <SectionHeading
              eyebrow="Workspace"
              title="Recent documents"
              description="The latest records entering the BhoomiAI pipeline."
              action={
                <Link
                  to="/documents"
                  className="inline-flex items-center gap-1 text-xs font-bold text-[#47725F] hover:text-[#315F4D]"
                >
                  View all
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              }
            />
          </div>

          <div className="border-t border-[#E8EFEC]">
            {loading ? (
              <div className="p-8 text-center text-sm text-[#84928C]">
                Loading workspace...
              </div>
            ) : !summary?.recent_documents?.length ? (
              <div className="p-8 text-center">
                <FileText className="mx-auto h-7 w-7 text-[#AAB7B1]" />
                <p className="mt-3 text-sm font-semibold text-[#53675E]">
                  No documents yet
                </p>
                <p className="mt-1 text-xs text-[#8A9791]">
                  Upload a land document to begin processing.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-[#E8EFEC]">
                {summary.recent_documents.map((document) => (
                  <Link
                    key={document.id}
                    to={`/documents/${document.id}`}
                    className="flex items-center gap-4 px-5 py-4 transition hover:bg-[#FAFCFB] sm:px-6"
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#F0F5F2] text-[#58776A]">
                      <FileText className="h-4 w-4" />
                    </div>

                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-[#33483F]">
                        {document.original_filename}
                      </p>

                      <p className="mt-1 text-[11px] text-[#89958F]">
                        {formatDate(document.created_at)}
                      </p>
                    </div>

                    <StatusPill status={documentTone(document.status)}>
                      {document.status.replace(/_/g, " ")}
                    </StatusPill>

                    <ArrowRight className="hidden h-4 w-4 text-[#B2BDB8] sm:block" />
                  </Link>
                ))}
              </div>
            )}
          </div>
        </Surface>

        <Surface>
          <div className="p-5 sm:p-6">
            <SectionHeading
              eyebrow="Attention"
              title="Review signals"
              description="Fields recently surfaced by validation."
            />
          </div>

          <div className="border-t border-[#E8EFEC]">
            {!notifications.length ? (
              <div className="p-8 text-center">
                <CheckCircle2 className="mx-auto h-7 w-7 text-[#5B876E]" />
                <p className="mt-3 text-sm font-semibold text-[#53675E]">
                  No active signals
                </p>
                <p className="mt-1 text-xs leading-5 text-[#89958F]">
                  The workspace has not reported any recent notification items.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-[#E8EFEC]">
                {notifications.slice(0, 6).map((item) => (
                  <Link
                    key={item.id}
                    to={`/documents/${item.document_id}`}
                    className="block px-5 py-4 transition hover:bg-[#FAFCFB] sm:px-6"
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#FBF6E9] text-[#96733A]">
                        <AlertTriangle className="h-3.5 w-3.5" />
                      </div>

                      <div className="min-w-0">
                        <p className="truncate text-xs font-semibold text-[#43574E]">
                          {item.field_name.replace(/_/g, " ")}
                        </p>

                        <p className="mt-1 truncate text-[11px] text-[#7F8E87]">
                          {item.document_filename}
                        </p>

                        <p className="mt-1 text-[10px] text-[#9AA59F]">
                          {item.validation_status}
                          {item.page_number
                            ? ` ... Page ${item.page_number}`
                            : ""}
                        </p>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </Surface>
      </div>

      <Surface className="p-5 sm:p-6">
        <SectionHeading
          eyebrow="Verification"
          title="Current workspace state"
          description="Only metrics returned by the backend are shown."
        />

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StateRow
            label="Pending documents"
            value={summary?.pending_documents}
            icon={<Clock3 className="h-4 w-4" />}
          />

          <StateRow
            label="Failed documents"
            value={summary?.failed_documents}
            icon={<XCircle className="h-4 w-4" />}
          />

          <StateRow
            label="Validation passed"
            value={summary?.validation_passed}
            icon={<CheckCircle2 className="h-4 w-4" />}
          />

          <StateRow
            label="Validation review"
            value={summary?.validation_review}
            icon={<AlertTriangle className="h-4 w-4" />}
          />
        </div>
      </Surface>
    </div>
  );
}

function StateRow({
  label,
  value,
  icon,
}: {
  label: string;
  value: number | undefined;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-[#E3EBE7] bg-[#FAFCFB] px-4 py-3">
      <div className="text-[#60796D]">{icon}</div>

      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#7B8B84]">
          {label}
        </p>

        <p className="mt-0.5 text-lg font-semibold text-[#33483F]">
          {value === undefined ? "..." : value}
        </p>
      </div>
    </div>
  );
}

