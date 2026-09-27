import {
  CheckCircle2,
  CircleAlert,
  Clock3,
  FileText,
  ShieldCheck,
} from "lucide-react";

type PipelineStatus = "complete" | "active" | "warning" | "pending";

type PipelineStep = {
  label: string;
  description: string;
  status: PipelineStatus;
};

const icons = {
  complete: CheckCircle2,
  active: Clock3,
  warning: CircleAlert,
  pending: FileText,
};

export function ProcessingPipeline({
  steps,
}: {
  steps: PipelineStep[];
}) {
  return (
    <div className="grid gap-2 md:grid-cols-4">
      {steps.map((step, index) => {
        const Icon = icons[step.status];

        const tone =
          step.status === "complete"
            ? "border-[#D8E9DE] bg-[#F4FAF6] text-[#3D795B]"
            : step.status === "warning"
              ? "border-[#EEE0C1] bg-[#FCF8EF] text-[#96733C]"
              : step.status === "active"
                ? "border-[#D5E6E3] bg-[#F1F7F6] text-[#39706D]"
                : "border-[#E4EAE7] bg-[#FAFBFA] text-[#82908A]";

        return (
          <div key={step.label} className="relative">
            <div className={`rounded-xl border p-3 ${tone}`}>
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4 shrink-0" />
                <span className="text-xs font-bold">{step.label}</span>
              </div>

              <p className="mt-1.5 pl-6 text-[10px] leading-4 opacity-80">
                {step.description}
              </p>
            </div>

            {index < steps.length - 1 && (
              <div className="absolute -right-1.5 top-1/2 hidden h-px w-3 bg-[#DCE5E1] md:block" />
            )}
          </div>
        );
      })}
    </div>
  );
}

export function TrustIndicator({
  confidence,
  status,
}: {
  confidence: number | null | undefined;
  status: string | null | undefined;
}) {
  const value =
    confidence === null || confidence === undefined
      ? null
      : Math.round(
          (confidence > 1 ? confidence / 100 : confidence) * 100,
        );

  const review =
    status === "REVIEW" ||
    status === "WARNING" ||
    status === "FAIL";

  return (
    <div className="flex items-center gap-3 rounded-xl border border-[#DDE8E3] bg-[#F8FBF9] px-3.5 py-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#E6F2EA] text-[#3B795A]">
        <ShieldCheck className="h-4 w-4" />
      </div>

      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#72837C]">
          {review ? "Review recommended" : "Trust signal"}
        </p>

        <p className="mt-0.5 text-xs font-semibold text-[#30483D]">
          {value === null ? "Confidence unavailable" : `${value}% confidence`}
        </p>
      </div>
    </div>
  );
}
