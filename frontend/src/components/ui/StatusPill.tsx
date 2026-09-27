import type { ReactNode } from "react";

type Status = "success" | "warning" | "danger" | "neutral" | "info";

const styles: Record<Status, string> = {
  success: "bg-[#EDF7F1] text-[#317454] border-[#D7EBDD]",
  warning: "bg-[#FBF6E9] text-[#96733A] border-[#EEE1BE]",
  danger: "bg-[#FBF0F0] text-[#A55757] border-[#EBD5D5]",
  neutral: "bg-[#F3F6F5] text-[#65756E] border-[#E1E8E5]",
  info: "bg-[#EEF5F5] text-[#39706D] border-[#D7E8E7]",
};

export function StatusPill({
  status,
  children,
  dot = true,
}: {
  status: Status;
  children: ReactNode;
  dot?: boolean;
}) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1",
        "text-[10px] font-bold uppercase tracking-[0.06em]",
        styles[status],
      ].join(" ")}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}
