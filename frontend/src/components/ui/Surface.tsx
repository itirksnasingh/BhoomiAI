import type { ReactNode } from "react";

type SurfaceProps = {
  children: ReactNode;
  className?: string;
};

export function Surface({ children, className = "" }: SurfaceProps) {
  return (
    <section
      className={[
        "rounded-2xl border border-[#DDE6E2] bg-white",
        "shadow-[0_8px_30px_rgba(32,55,45,0.045)]",
        className,
      ].join(" ")}
    >
      {children}
    </section>
  );
}

type SectionHeadingProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
};

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}: SectionHeadingProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && (
          <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.16em] text-[#648072]">
            {eyebrow}
          </p>
        )}

        <h2 className="text-[20px] font-semibold tracking-[-0.025em] text-[#21362D]">
          {title}
        </h2>

        {description && (
          <p className="mt-1 max-w-2xl text-sm leading-6 text-[#72837C]">
            {description}
          </p>
        )}
      </div>

      {action}
    </div>
  );
}

export function Divider() {
  return <div className="h-px bg-[#E8EFEC]" />;
}
