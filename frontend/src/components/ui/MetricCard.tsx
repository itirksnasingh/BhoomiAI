import type { ReactNode } from "react";
import { ArrowUpRight } from "lucide-react";

export function MetricCard({
  label,
  value,
  detail,
  icon,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  detail?: string;
  icon: ReactNode;
  tone?: "default" | "green" | "amber" | "red";
}) {
  const iconClasses = {
    default: "bg-[#F2F5F4] text-[#526A60]",
    green: "bg-[#EDF7F1] text-[#39785B]",
    amber: "bg-[#FBF6E9] text-[#94723D]",
    red: "bg-[#FBF0F0] text-[#A55757]",
  };

  return (
    <div className="rounded-2xl border border-[#DFE8E4] bg-white p-4 shadow-[0_5px_22px_rgba(31,57,47,0.035)]">
      <div className="flex items-start justify-between gap-3">
        <div
          className={[
            "flex h-9 w-9 items-center justify-center rounded-xl",
            iconClasses[tone],
          ].join(" ")}
        >
          {icon}
        </div>

        <ArrowUpRight className="h-4 w-4 text-[#A8B5AF]" />
      </div>

      <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.09em] text-[#7A8A83]">
        {label}
      </p>

      <p className="mt-1 text-[25px] font-semibold tracking-[-0.035em] text-[#23372F]">
        {value}
      </p>

      {detail && (
        <p className="mt-1 text-xs text-[#82908A]">
          {detail}
        </p>
      )}
    </div>
  );
}
