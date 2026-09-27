import type { ReactNode } from "react";

export function EmptyPanel({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon?: ReactNode;
}) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center rounded-2xl border border-dashed border-[#D9E4DF] bg-[#FBFCFB] px-6 text-center">
      {icon && (
        <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-[#EEF5F1] text-[#557568]">
          {icon}
        </div>
      )}

      <h3 className="text-sm font-semibold text-[#33483F]">{title}</h3>
      <p className="mt-1 max-w-sm text-xs leading-5 text-[#82908A]">
        {description}
      </p>
    </div>
  );
}
