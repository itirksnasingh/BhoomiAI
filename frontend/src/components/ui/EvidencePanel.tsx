import {
  Brackets,
  CheckCircle2,
  FileSearch,
  MapPin,
  ScanText,
} from "lucide-react";

type EvidencePanelProps = {
  fieldName: string;
  value: string | null;
  confidence: number | null;
  validationStatus: string | null;
  evidence?: Record<string, unknown> | null;
};

function prettyField(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function confidenceText(value: number | null) {
  if (value === null || value === undefined) return "Unavailable";
  return `${Math.round((value > 1 ? value / 100 : value) * 100)}%`;
}

export function EvidencePanel({
  fieldName,
  value,
  confidence,
  validationStatus,
  evidence,
}: EvidencePanelProps) {
  const bbox =
    evidence?.bbox ??
    evidence?.bbox_xyxy ??
    evidence?.bounding_box ??
    null;

  const sourceText =
    typeof evidence?.text === "string"
      ? evidence.text
      : typeof evidence?.ocr_text === "string"
        ? evidence.ocr_text
        : value;

  return (
    <div className="rounded-2xl border border-[#DCE7E2] bg-[#FAFCFB] p-4">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#EAF3EE] text-[#4A7663]">
          <FileSearch className="h-4 w-4" />
        </div>

        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#71847B]">
            Evidence
          </p>

          <h3 className="mt-1 text-sm font-semibold text-[#294037]">
            {prettyField(fieldName)}
          </h3>

          <p className="mt-0.5 break-words text-sm text-[#53675E]">
            {value || "No extracted value"}
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        <div className="rounded-xl border border-[#E4EBE8] bg-white p-3">
          <div className="flex items-center gap-2 text-[#6E8178]">
            <ScanText className="h-3.5 w-3.5" />
            <span className="text-[10px] font-bold uppercase tracking-[0.08em]">
              OCR text
            </span>
          </div>

          <p className="mt-2 line-clamp-2 text-xs text-[#42574E]">
            {sourceText || "Unavailable"}
          </p>
        </div>

        <div className="rounded-xl border border-[#E4EBE8] bg-white p-3">
          <div className="flex items-center gap-2 text-[#6E8178]">
            <MapPin className="h-3.5 w-3.5" />
            <span className="text-[10px] font-bold uppercase tracking-[0.08em]">
              Source region
            </span>
          </div>

          <p className="mt-2 break-all text-xs text-[#42574E]">
            {bbox ? JSON.stringify(bbox) : "Bounding box unavailable"}
          </p>
        </div>

        <div className="rounded-xl border border-[#E4EBE8] bg-white p-3">
          <div className="flex items-center gap-2 text-[#6E8178]">
            <Brackets className="h-3.5 w-3.5" />
            <span className="text-[10px] font-bold uppercase tracking-[0.08em]">
              Verification
            </span>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-[#4B805F]" />
            <span className="text-xs font-semibold text-[#42574E]">
              {validationStatus || "Not validated"}
            </span>
          </div>

          <p className="mt-1 text-[10px] text-[#84928C]">
            Confidence: {confidenceText(confidence)}
          </p>
        </div>
      </div>

      <p className="mt-3 text-[10px] leading-4 text-[#84928C]">
        Evidence is derived from the extraction record. Source-region
        highlighting will use the stored document-page coordinates when
        available.
      </p>
    </div>
  );
}
