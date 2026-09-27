import {
  ArrowLeft,
  CheckCircle2,
  FileSearch,
  Loader2,
  Pencil,
  RefreshCw,
  Save,
  ShieldCheck,
  XCircle,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Link, useParams } from "react-router-dom";

import {
  getDocumentFields,
  getDocumentPageImage,
  getDocumentPages,
  getValidation,
  reviewField,
  runDocumentPipeline,
  validateDocument,
} from "../services/api";

import type {
  ExtractedField,
  ValidationRunResponse,
} from "../types/api";

import {
  ProcessingPipeline,
  TrustIndicator,
} from "../components/ui/DocumentWorkspace";

/* -------------------------------------------------------------------------- */
/* HELPERS                                                                    */
/* -------------------------------------------------------------------------- */

function prettyField(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function fieldStatus(value: string | null | undefined) {
  const status = String(value || "").toUpperCase();

  if (
    status === "PASS" ||
    status === "ACCEPTED" ||
    status === "VERIFIED"
  ) {
    return "success" as const;
  }

  if (
    status === "WARNING" ||
    status === "REVIEW"
  ) {
    return "warning" as const;
  }

  if (
    status === "FAIL" ||
    status === "REJECTED"
  ) {
    return "danger" as const;
  }

  return "neutral" as const;
}

/**
 * BhoomiAI confidence values should normally be 0..1.
 *
 * Some legacy/backend responses may contain percentage-style values such
 * as 97.33. Normalize those values so the UI never displays 9733%.
 */
function normalizeConfidence(
  value: number | null | undefined,
) {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return null;
  }

  if (value > 1) {
    return value / 100;
  }

  return value;
}

function confidenceLabel(
  value: number | null | undefined,
) {
  const normalized = normalizeConfidence(value);

  if (normalized === null) {
    return "Unavailable";
  }

  return `${Math.round(normalized * 100)}%`;
}

/* -------------------------------------------------------------------------- */
/* EVIDENCE BOUNDING BOX                                                      */
/* -------------------------------------------------------------------------- */

type EvidenceBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

function getEvidenceBox(
  field: ExtractedField,
): EvidenceBox | null {
  const evidence = field.evidence_bbox;

  if (!evidence) {
    return null;
  }

  /*
   * Support the different evidence formats that may exist in the backend:
   *
   * {
   *   x, y, width, height
   * }
   *
   * {
   *   left, top, right, bottom
   * }
   *
   * {
   *   bbox: {...}
   * }
   *
   * {
   *   bounding_box: {...}
   * }
   *
   * [x1, y1, x2, y2]
   */

  if (Array.isArray(evidence)) {
    if (evidence.length < 4) {
      return null;
    }

    const values = evidence.slice(0, 4).map(Number);

    if (values.some((value) => !Number.isFinite(value))) {
      return null;
    }

    const [x1, y1, x2, y2] = values;

    if (x2 <= x1 || y2 <= y1) {
      return null;
    }

    return {
      x: x1,
      y: y1,
      width: x2 - x1,
      height: y2 - y1,
    };
  }

  if (
    typeof evidence !== "object" ||
    evidence === null
  ) {
    return null;
  }

  const raw = evidence as Record<string, unknown>;

  const nested =
    raw.bbox ??
    raw.bounding_box ??
    raw.bbox_xyxy ??
    raw;

  if (Array.isArray(nested)) {
    if (nested.length < 4) {
      return null;
    }

    const values = nested.slice(0, 4).map(Number);

    if (values.some((value) => !Number.isFinite(value))) {
      return null;
    }

    const [x1, y1, x2, y2] = values;

    if (x2 <= x1 || y2 <= y1) {
      return null;
    }

    return {
      x: x1,
      y: y1,
      width: x2 - x1,
      height: y2 - y1,
    };
  }

  if (
    typeof nested !== "object" ||
    nested === null
  ) {
    return null;
  }

  const source = nested as Record<string, unknown>;

  const x = Number(
    source.x ??
      source.left ??
      source.x1 ??
      0,
  );

  const y = Number(
    source.y ??
      source.top ??
      source.y1 ??
      0,
  );

  let width = Number(
    source.width ??
      source.w ??
      0,
  );

  let height = Number(
    source.height ??
      source.h ??
      0,
  );

  const right = source.right ?? source.x2;
  const bottom = source.bottom ?? source.y2;

  if (
    width <= 0 &&
    right !== undefined
  ) {
    width = Number(right) - x;
  }

  if (
    height <= 0 &&
    bottom !== undefined
  ) {
    height = Number(bottom) - y;
  }

  if (
    !Number.isFinite(x) ||
    !Number.isFinite(y) ||
    !Number.isFinite(width) ||
    !Number.isFinite(height) ||
    width <= 0 ||
    height <= 0
  ) {
    return null;
  }

  return {
    x,
    y,
    width,
    height,
  };
}

/* -------------------------------------------------------------------------- */
/* SOURCE EVIDENCE VIEWER                                                     */
/* -------------------------------------------------------------------------- */

function SourceEvidenceViewer({
  pageNumber,
  imageUrl,
  imageLoading,
  imageError,
  evidence,
  fieldName,
  zoom,
  onZoomIn,
  onZoomOut,
}: {
  pageNumber: number | null;
  imageUrl: string | null;
  imageLoading: boolean;
  imageError: string;
  evidence: ExtractedField | null;
  fieldName: string | null;
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
}) {
  const bbox = evidence
    ? getEvidenceBox(evidence)
    : null;

  const imageRef =
    useRef<HTMLImageElement | null>(null);

  const [naturalSize, setNaturalSize] =
    useState({
      width: 0,
      height: 0,
    });

  function handleImageLoad() {
    const image = imageRef.current;

    if (!image) {
      return;
    }

    setNaturalSize({
      width: image.naturalWidth,
      height: image.naturalHeight,
    });
  }

  const bboxStyle =
    bbox &&
    naturalSize.width > 0 &&
    naturalSize.height > 0
      ? {
          left: `${(bbox.x / naturalSize.width) * 100}%`,
          top: `${(bbox.y / naturalSize.height) * 100}%`,
          width: `${(bbox.width / naturalSize.width) * 100}%`,
          height: `${(bbox.height / naturalSize.height) * 100}%`,
        }
      : null;

  return (
    <div className="overflow-hidden rounded-2xl border border-[#DDE7E2] bg-[#EEF2F0] shadow-inner">
      <div className="flex items-center justify-between gap-3 border-b border-[#D8E3DE] bg-white px-4 py-3">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#71847B]">
            Source evidence
          </p>

          <p className="mt-0.5 truncate text-xs font-semibold text-[#344940]">
            {fieldName
              ? prettyField(fieldName)
              : "Select a field"}

            {pageNumber
              ? ` · Page ${pageNumber}`
              : ""}
          </p>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onZoomOut}
            disabled={zoom <= 0.8}
            aria-label="Zoom out"
            className="rounded-lg border border-[#DCE6E1] bg-white p-2 text-[#60786D] transition hover:bg-[#F5F9F7] disabled:opacity-40"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </button>

          <span className="min-w-[48px] text-center text-[10px] font-bold text-[#71847B]">
            {Math.round(zoom * 100)}%
          </span>

          <button
            type="button"
            onClick={onZoomIn}
            disabled={zoom >= 2}
            aria-label="Zoom in"
            className="rounded-lg border border-[#DCE6E1] bg-white p-2 text-[#60786D] transition hover:bg-[#F5F9F7] disabled:opacity-40"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="relative flex min-h-[460px] max-h-[720px] items-center justify-center overflow-auto p-5">
        {imageLoading ? (
          <div className="flex flex-col items-center gap-3 text-[#74877E]">
            <Loader2 className="h-6 w-6 animate-spin" />

            <p className="text-xs font-medium">
              Loading source page…
            </p>
          </div>
        ) : imageError ? (
          <div className="max-w-sm rounded-xl border border-[#EBD5D5] bg-white p-5 text-center">
            <XCircle className="mx-auto h-6 w-6 text-[#A55757]" />

            <p className="mt-3 text-xs font-semibold text-[#704848]">
              Source preview unavailable
            </p>

            <p className="mt-1 text-[10px] leading-4 text-[#89958F]">
              {imageError}
            </p>
          </div>
        ) : !imageUrl ? (
          <div className="max-w-sm text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-[#648072] shadow-sm">
              <FileSearch className="h-6 w-6" />
            </div>

            <p className="mt-4 text-sm font-semibold text-[#52665D]">
              Select an extracted field
            </p>

            <p className="mt-1 text-xs leading-5 text-[#89958F]">
              BhoomiAI will open the corresponding
              source page and highlight the evidence
              region when coordinates are available.
            </p>
          </div>
        ) : (
          <div
            className="relative shrink-0 origin-center transition-transform duration-150"
            style={{
              transform: `scale(${zoom})`,
            }}
          >
            <img
              ref={imageRef}
              src={imageUrl}
              alt={
                pageNumber
                  ? `Document source page ${pageNumber}`
                  : "Document source page"
              }
              onLoad={handleImageLoad}
              className="block max-h-[650px] max-w-[900px] rounded-lg bg-white shadow-[0_10px_35px_rgba(35,52,45,0.14)]"
            />

            {bboxStyle && (
              <div
                className="pointer-events-none absolute border-2 border-[#2F7358] bg-[#4B9A7620] shadow-[0_0_0_3px_rgba(255,255,255,0.75)]"
                style={bboxStyle}
              >
                <span className="absolute -top-6 left-[-2px] whitespace-nowrap rounded-md bg-[#2F7358] px-2 py-1 text-[9px] font-bold text-white shadow-sm">
                  {fieldName
                    ? prettyField(fieldName)
                    : "Evidence"}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-[#D8E3DE] bg-white px-4 py-3">
        <div className="flex items-center gap-2">
          <span
            className={[
              "h-2 w-2 rounded-full",
              bboxStyle
                ? "bg-[#3E8A68]"
                : "bg-[#A9B5AF]",
            ].join(" ")}
          />

          <span className="text-[10px] font-medium text-[#71847B]">
            {bboxStyle
              ? "Evidence region linked"
              : "No bounding box available"}
          </span>
        </div>

        {pageNumber && (
          <span className="text-[10px] font-bold text-[#6D8077]">
            Page {pageNumber}
          </span>
        )}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* PAGE                                                                       */
/* -------------------------------------------------------------------------- */

export default function DocumentDetails() {
  const { documentId } =
    useParams<{ documentId: string }>();

  const [fields, setFields] =
    useState<ExtractedField[]>([]);

  const [validation, setValidation] =
    useState<ValidationRunResponse | null>(null);

  const [pages, setPages] = useState<
    Array<{
      id: string;
      document_id: string;
      page_number: number;
    }>
  >([]);

  const [pageImages, setPageImages] =
    useState<Record<string, string>>({});

  const [selectedFieldId, setSelectedFieldId] =
    useState<string | null>(null);

  const [selectedPageId, setSelectedPageId] =
    useState<string | null>(null);

  const [zoom, setZoom] = useState(1);

  const [loading, setLoading] = useState(true);
  const [imageLoading, setImageLoading] =
    useState(false);
  const [extracting, setExtracting] =
    useState(false);
  const [validating, setValidating] =
    useState(false);

  const [editingId, setEditingId] =
    useState<string | null>(null);

  const [editValue, setEditValue] = useState("");
  const [reason, setReason] = useState("");

  const [savingId, setSavingId] =
    useState<string | null>(null);

  const [error, setError] = useState("");
  const [imageError, setImageError] =
    useState("");
  const [message, setMessage] = useState("");

  /* ---------------------------------------------------------------------- */
  /* LOAD DOCUMENT                                                          */
  /* ---------------------------------------------------------------------- */

  async function loadDocument() {
    if (!documentId) {
      setError("Document ID is missing.");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError("");

      const [
        fieldResponse,
        validationResponse,
        pageResponse,
      ] = await Promise.all([
        getDocumentFields(documentId),
        getValidation(documentId).catch(
          () => null,
        ),
        getDocumentPages(documentId).catch(
          () => [],
        ),
      ]);

      setFields(fieldResponse);
      setValidation(validationResponse);
      setPages(pageResponse);

      setSelectedFieldId((current) => {
        if (
          current &&
          fieldResponse.some(
            (field) => field.id === current,
          )
        ) {
          return current;
        }

        return fieldResponse[0]?.id || null;
      });

      setSelectedPageId((current) => {
        if (
          current &&
          pageResponse.some(
            (page) => page.id === current,
          )
        ) {
          return current;
        }

        return pageResponse[0]?.id || null;
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load this document.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDocument();
  }, [documentId]);

  /* ---------------------------------------------------------------------- */
  /* SELECTED FIELD                                                         */
  /* ---------------------------------------------------------------------- */

  const selectedField = useMemo(
    () =>
      fields.find(
        (field) => field.id === selectedFieldId,
      ) ||
      fields[0] ||
      null,
    [fields, selectedFieldId],
  );

  /* ---------------------------------------------------------------------- */
  /* SELECTED PAGE                                                          */
  /* ---------------------------------------------------------------------- */

  const selectedPage = useMemo(() => {
    if (selectedField?.document_page_id) {
      const attached = pages.find(
        (page) =>
          page.id ===
          selectedField.document_page_id,
      );

      if (attached) {
        return attached;
      }
    }

    return (
      pages.find(
        (page) => page.id === selectedPageId,
      ) ||
      pages[0] ||
      null
    );
  }, [
    pages,
    selectedField,
    selectedPageId,
  ]);

  useEffect(() => {
    if (selectedField?.document_page_id) {
      setSelectedPageId(
        selectedField.document_page_id,
      );
    }
  }, [selectedField?.document_page_id]);

  /* ---------------------------------------------------------------------- */
  /* SOURCE IMAGE                                                            */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    if (!documentId || !selectedPage) {
      return;
    }

    if (pageImages[selectedPage.id]) {
      return;
    }

    let cancelled = false;

    async function loadImage() {
      try {
        setImageLoading(true);
        setImageError("");

        const blob =
          await getDocumentPageImage(
            documentId!,
            selectedPage!.id,
          );

        if (cancelled) {
          return;
        }

        const url =
          URL.createObjectURL(blob);

        setPageImages((current) => ({
          ...current,
          [selectedPage!.id]: url,
        }));
      } catch (err) {
        if (cancelled) {
          return;
        }

        setImageError(
          err instanceof Error
            ? err.message
            : "Unable to load source page.",
        );
      } finally {
        if (!cancelled) {
          setImageLoading(false);
        }
      }
    }

    void loadImage();

    return () => {
      cancelled = true;
    };
  }, [
    documentId,
    selectedPage?.id,
    pageImages,
  ]);

  /* ---------------------------------------------------------------------- */
  /* CLEAN OBJECT URLS                                                       */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    return () => {
      Object.values(pageImages).forEach(
        (url) => {
          URL.revokeObjectURL(url);
        },
      );
    };
  }, [pageImages]);

  /* ---------------------------------------------------------------------- */
  /* ZOOM                                                                    */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    setZoom(1);
  }, [
    selectedFieldId,
    selectedPageId,
  ]);

  /* ---------------------------------------------------------------------- */
  /* FULL PIPELINE                                                           */
  /* ---------------------------------------------------------------------- */

  async function handleReextract() {
    if (!documentId) {
      return;
    }

    try {
      setExtracting(true);
      setError("");
      setMessage("");

      /*
       * IMPORTANT:
       *
       * Do not call extractDocument() here.
       *
       * Extraction-only requires a completed OCR run. The full pipeline
       * creates the OCR run first and then performs extraction/evidence.
       */
      await runDocumentPipeline(
        documentId,
      );

      /*
       * Refresh validation after the pipeline.
       *
       * If the pipeline already produced validation, this is still safe
       * because the validation endpoint simply recalculates the current
       * extracted state.
       */
      try {
        await validateDocument(
          documentId,
        );
      } catch {
        // Processing succeeded even if validation refresh failed.
      }

      setMessage(
        "Document processing completed. OCR, extraction, evidence and validation have been refreshed.",
      );

      /*
       * Clear cached page images so the workspace displays the newest
       * source-page artifacts if processing regenerated them.
       */
      Object.values(pageImages).forEach(
        (url) => {
          URL.revokeObjectURL(url);
        },
      );

      setPageImages({});

      await loadDocument();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Document processing failed.",
      );
    } finally {
      setExtracting(false);
    }
  }

  /* ---------------------------------------------------------------------- */
  /* VALIDATION                                                              */
  /* ---------------------------------------------------------------------- */

  async function handleValidate() {
    if (!documentId) {
      return;
    }

    try {
      setValidating(true);
      setError("");
      setMessage("");

      await validateDocument(
        documentId,
      );

      setMessage(
        "Validation completed.",
      );

      await loadDocument();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Validation failed.",
      );
    } finally {
      setValidating(false);
    }
  }

  /* ---------------------------------------------------------------------- */
  /* FIELD CORRECTION                                                        */
  /* ---------------------------------------------------------------------- */

  async function handleCorrection(
    field: ExtractedField,
  ) {
    if (!editValue.trim()) {
      setError(
        "Enter a corrected value before saving.",
      );
      return;
    }

    try {
      setSavingId(field.id);
      setError("");
      setMessage("");

      await reviewField(
        field.id,
        "EDIT",
        editValue.trim(),
        reason.trim() || undefined,
      );

      setEditingId(null);
      setEditValue("");
      setReason("");

      setMessage(
        `${prettyField(field.field_name)} was corrected and sent through review.`,
      );

      await loadDocument();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to save correction.",
      );
    } finally {
      setSavingId(null);
    }
  }

  /* ---------------------------------------------------------------------- */
  /* SUMMARY                                                                 */
  /* ---------------------------------------------------------------------- */

  const passCount = fields.filter(
    (field) =>
      field.validation_status?.toUpperCase() ===
      "PASS",
  ).length;

  const reviewCount = fields.filter(
    (field) =>
      [
        "WARNING",
        "REVIEW",
        "FAIL",
      ].includes(
        String(
          field.validation_status || "",
        ).toUpperCase(),
      ),
  ).length;

  const averageConfidence = useMemo(() => {
    const values = fields
      .map((field) =>
        normalizeConfidence(
          field.confidence,
        ),
      )
      .filter(
        (value): value is number =>
          value !== null,
      );

    if (!values.length) {
      return null;
    }

    return (
      values.reduce(
        (sum, value) =>
          sum + value,
        0,
      ) / values.length
    );
  }, [fields]);

  /* ---------------------------------------------------------------------- */
  /* PIPELINE STATUS                                                         */
  /* ---------------------------------------------------------------------- */

  const pipeline = [
    {
      label: "Document",
      description: "Uploaded and stored",
      status: "complete" as const,
    },
    {
      label: "OCR",
      description:
        "Text and evidence generated",
      status: fields.length
        ? ("complete" as const)
        : ("pending" as const),
    },
    {
      label: "Extraction",
      description: `${fields.length} fields available`,
      status: fields.length
        ? ("complete" as const)
        : ("pending" as const),
    },
    {
      label: "Validation",
      description: validation
        ? "Validation results available"
        : "Awaiting validation",
      status: validation
        ? reviewCount
          ? ("warning" as const)
          : ("complete" as const)
        : ("pending" as const),
    },
  ];

  const imageUrl = selectedPage
    ? pageImages[selectedPage.id] ||
      null
    : null;

  /* ---------------------------------------------------------------------- */
  /* RENDER                                                                  */
  /* ---------------------------------------------------------------------- */

  return (
    <div className="bhoomi-page space-y-6">
      {/* HEADER ------------------------------------------------------------ */}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <Link
            to="/documents"
            className="mb-3 inline-flex items-center gap-1.5 text-xs font-semibold text-[#668078] transition hover:text-[#315F4D]"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to documents
          </Link>

          <p className="text-[10px] font-bold uppercase tracking-[0.17em] text-[#648072]">
            Document workspace
          </p>

          <h1 className="mt-1 max-w-3xl truncate text-[27px] font-semibold tracking-[-0.035em] text-[#21362D]">
            {documentId ||
              "Document"}
          </h1>

          <p className="mt-1 text-xs text-[#84928C]">
            Evidence-linked extraction,
            source verification and human
            review
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() =>
              void handleReextract()
            }
            disabled={extracting}
            className="inline-flex items-center gap-2 rounded-xl border border-[#D7E3DE] bg-white px-3.5 py-2.5 text-xs font-bold text-[#4A6F60] shadow-sm transition hover:-translate-y-0.5 hover:bg-[#F7FAF8] disabled:opacity-50"
          >
            <RefreshCw
              className={[
                "h-3.5 w-3.5",
                extracting
                  ? "animate-spin"
                  : "",
              ].join(" ")}
            />

            {extracting
              ? "Processing…"
              : "Run processing"}
          </button>

          <button
            type="button"
            onClick={() =>
              void handleValidate()
            }
            disabled={
              validating ||
              !fields.length
            }
            className="inline-flex items-center gap-2 rounded-xl bg-[#315F4D] px-3.5 py-2.5 text-xs font-bold text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-[#274F3F] disabled:opacity-50"
          >
            <ShieldCheck className="h-3.5 w-3.5" />

            {validating
              ? "Validating…"
              : "Run validation"}
          </button>
        </div>
      </div>

      {/* MESSAGES ---------------------------------------------------------- */}

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

      {/* PIPELINE ---------------------------------------------------------- */}

      <ProcessingPipeline
        steps={pipeline}
      />

      {/* CONTENT ----------------------------------------------------------- */}

      {loading ? (
        <div className="rounded-2xl border border-[#DDE6E2] bg-white p-12 text-center text-sm text-[#84928C]">
          Loading document workspace…
        </div>
      ) : (
        <>
          {/* SOURCE + SELECTED EVIDENCE ----------------------------------- */}

          <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
            <section className="overflow-hidden rounded-2xl border border-[#DDE6E2] bg-white shadow-[0_8px_30px_rgba(32,55,45,0.045)]">
              <div className="flex items-center justify-between gap-4 border-b border-[#E8EFEC] px-5 py-4 sm:px-6">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.13em] text-[#71847B]">
                    Evidence workspace
                  </p>

                  <h2 className="mt-1 text-sm font-semibold text-[#33483F]">
                    Source document
                  </h2>
                </div>

                <span className="rounded-full bg-[#EEF4F1] px-2.5 py-1 text-[9px] font-bold uppercase tracking-[0.08em] text-[#527465]">
                  Private source
                </span>
              </div>

              {/* PAGE TABS ------------------------------------------------ */}

              {pages.length > 0 && (
                <div className="flex items-center gap-2 overflow-x-auto border-b border-[#E8EFEC] bg-[#FAFCFB] px-4 py-2.5">
                  {pages.map(
                    (page) => {
                      const active =
                        selectedPage?.id ===
                        page.id;

                      return (
                        <button
                          key={page.id}
                          type="button"
                          onClick={() => {
                            setSelectedPageId(
                              page.id,
                            );

                            setSelectedFieldId(
                              (current) => {
                                const matching =
                                  fields.find(
                                    (field) =>
                                      field.document_page_id ===
                                      page.id,
                                  );

                                return (
                                  matching?.id ||
                                  current
                                );
                              },
                            );
                          }}
                          className={[
                            "shrink-0 rounded-lg border px-3 py-1.5 text-[10px] font-bold transition",
                            active
                              ? "border-[#BFD7CA] bg-[#EAF4EE] text-[#315F4D]"
                              : "border-[#E2EAE6] bg-white text-[#71847B] hover:border-[#CBDDD3] hover:bg-[#F5F9F7]",
                          ].join(" ")}
                        >
                          Page{" "}
                          {
                            page.page_number
                          }
                        </button>
                      );
                    },
                  )}
                </div>
              )}

              <div className="p-4 sm:p-5">
                <SourceEvidenceViewer
                  pageNumber={
                    selectedPage?.page_number ||
                    null
                  }
                  imageUrl={
                    imageUrl
                  }
                  imageLoading={
                    imageLoading
                  }
                  imageError={
                    imageError
                  }
                  evidence={
                    selectedField
                  }
                  fieldName={
                    selectedField?.field_name ||
                    null
                  }
                  zoom={zoom}
                  onZoomIn={() =>
                    setZoom(
                      (value) =>
                        Math.min(
                          2,
                          value +
                            0.2,
                        ),
                    )
                  }
                  onZoomOut={() =>
                    setZoom(
                      (value) =>
                        Math.max(
                          0.8,
                          value -
                            0.2,
                        ),
                    )
                  }
                />
              </div>
            </section>

            {/* SELECTED EVIDENCE ------------------------------------------ */}

            <div className="space-y-5">
              <section className="rounded-2xl border border-[#DDE6E2] bg-white p-5 shadow-[0_8px_30px_rgba(32,55,45,0.045)]">
                <p className="text-[10px] font-bold uppercase tracking-[0.13em] text-[#71847B]">
                  Selected evidence
                </p>

                <h2 className="mt-1 text-lg font-semibold text-[#2C4339]">
                  {selectedField
                    ? prettyField(
                        selectedField.field_name,
                      )
                    : "No field selected"}
                </h2>

                <p className="mt-2 break-words text-sm font-medium leading-6 text-[#4E6259]">
                  {selectedField?.value ||
                    "Select an extracted field to inspect its evidence."}
                </p>

                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  <div className="rounded-xl border border-[#E3EBE7] bg-[#FAFCFB] p-3">
                    <p className="text-[9px] font-bold uppercase tracking-[0.08em] text-[#7B8B84]">
                      Confidence
                    </p>

                    <p className="mt-1 text-sm font-semibold text-[#33483F]">
                      {confidenceLabel(
                        selectedField?.confidence,
                      )}
                    </p>
                  </div>

                  <div className="rounded-xl border border-[#E3EBE7] bg-[#FAFCFB] p-3">
                    <p className="text-[9px] font-bold uppercase tracking-[0.08em] text-[#7B8B84]">
                      Verification
                    </p>

                    <p className="mt-1 text-sm font-semibold text-[#33483F]">
                      {selectedField?.validation_status ||
                        "Not validated"}
                    </p>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-[#E8EFEC] pt-4">
                  <span className="text-[10px] text-[#82908A]">
                    {selectedField?.evidence_bbox
                      ? "Bounding box linked"
                      : "No bounding box recorded"}
                  </span>

                  {selectedPage && (
                    <span className="text-[10px] font-bold text-[#567266]">
                      Page{" "}
                      {
                        selectedPage.page_number
                      }
                    </span>
                  )}
                </div>
              </section>

              <TrustIndicator
                confidence={
                  averageConfidence
                }
                status={
                  reviewCount
                    ? "REVIEW"
                    : passCount
                      ? "PASS"
                      : null
                }
              />
            </div>
          </div>

          {/* EXTRACTED INFORMATION -------------------------------------- */}

          <section className="overflow-hidden rounded-2xl border border-[#DDE6E2] bg-white shadow-[0_8px_30px_rgba(32,55,45,0.045)]">
            <div className="flex items-center justify-between gap-4 border-b border-[#E8EFEC] px-5 py-4 sm:px-6">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.13em] text-[#71847B]">
                  Extracted information
                </p>

                <h2 className="mt-1 text-lg font-semibold text-[#2C4339]">
                  Land record fields
                </h2>
              </div>

              <span className="rounded-full bg-[#F1F5F3] px-2.5 py-1 text-[10px] font-bold text-[#6C7E76]">
                {fields.length} fields
              </span>
            </div>

            {!fields.length ? (
              <div className="p-12 text-center">
                <FileSearch className="mx-auto h-8 w-8 text-[#AAB7B1]" />

                <p className="mt-3 text-sm font-semibold text-[#53675E]">
                  No extracted fields
                </p>

                <p className="mt-1 text-xs leading-5 text-[#89958F]">
                  Run document processing to
                  populate the verification
                  workspace.
                </p>
              </div>
            ) : (
              <div className="grid gap-3 p-4 sm:grid-cols-2 sm:p-5 lg:grid-cols-3">
                {fields.map(
                  (field) => {
                    const selected =
                      selectedFieldId ===
                      field.id;

                    const editing =
                      editingId ===
                      field.id;

                    const tone =
                      fieldStatus(
                        field.validation_status,
                      );

                    return (
                      <div
                        key={field.id}
                        className={[
                          "rounded-2xl border p-4 transition-all duration-150",
                          selected
                            ? "border-[#AFCFBD] bg-[#F4FAF6] shadow-[0_8px_24px_rgba(49,95,77,0.08)]"
                            : "border-[#E1E9E5] bg-white hover:-translate-y-0.5 hover:border-[#C8DAD1] hover:shadow-[0_8px_22px_rgba(32,55,45,0.05)]",
                        ].join(" ")}
                      >
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedFieldId(
                              field.id,
                            );

                            if (
                              field.document_page_id
                            ) {
                              setSelectedPageId(
                                field.document_page_id,
                              );
                            }
                          }}
                          className="w-full text-left"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#71847B]">
                                {prettyField(
                                  field.field_name,
                                )}
                              </p>

                              <p className="mt-2 break-words text-sm font-semibold leading-5 text-[#293E35]">
                                {field.value ||
                                  "No value extracted"}
                              </p>
                            </div>

                            <span
                              className={[
                                "shrink-0 rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase",
                                tone ===
                                "success"
                                  ? "border-[#D7EBDD] bg-[#EDF7F1] text-[#39785B]"
                                  : tone ===
                                      "warning"
                                    ? "border-[#EEE1BE] bg-[#FBF6E9] text-[#96733A]"
                                    : tone ===
                                        "danger"
                                      ? "border-[#EBD5D5] bg-[#FBF0F0] text-[#A55757]"
                                      : "border-[#E1E8E5] bg-[#F3F6F5] text-[#65756E]",
                              ].join(" ")}
                            >
                              {field.validation_status ||
                                "UNVALIDATED"}
                            </span>
                          </div>

                          <div className="mt-4 flex items-center justify-between gap-2 text-[10px] text-[#84928C]">
                            <span>
                              {confidenceLabel(
                                field.confidence,
                              )}{" "}
                              confidence
                            </span>

                            <span>
                              {field.evidence_bbox
                                ? "Evidence linked"
                                : "No evidence"}
                            </span>
                          </div>
                        </button>

                        {/* CORRECTION ------------------------------------- */}

                        {editing ? (
                          <div className="mt-4 rounded-xl border border-[#DCE7E2] bg-[#FAFCFB] p-3">
                            <label className="block text-[10px] font-bold uppercase tracking-[0.08em] text-[#71847B]">
                              Corrected value
                            </label>

                            <input
                              value={
                                editValue
                              }
                              onChange={(
                                event,
                              ) =>
                                setEditValue(
                                  event
                                    .target
                                    .value,
                                )
                              }
                              className="mt-2 w-full rounded-lg border border-[#D5E0DB] bg-white px-3 py-2.5 text-sm text-[#344940] outline-none transition focus:border-[#719584] focus:ring-2 focus:ring-[#DCEBE2]"
                            />

                            <label className="mt-3 block text-[10px] font-bold uppercase tracking-[0.08em] text-[#71847B]">
                              Reason
                            </label>

                            <textarea
                              value={
                                reason
                              }
                              onChange={(
                                event,
                              ) =>
                                setReason(
                                  event
                                    .target
                                    .value,
                                )
                              }
                              rows={2}
                              className="mt-2 w-full resize-none rounded-lg border border-[#D5E0DB] bg-white px-3 py-2.5 text-sm text-[#344940] outline-none transition focus:border-[#719584] focus:ring-2 focus:ring-[#DCEBE2]"
                            />

                            <div className="mt-3 flex justify-end gap-2">
                              <button
                                type="button"
                                onClick={() => {
                                  setEditingId(
                                    null,
                                  );
                                  setEditValue(
                                    "",
                                  );
                                  setReason(
                                    "",
                                  );
                                }}
                                className="rounded-lg px-3 py-2 text-[11px] font-bold text-[#73827C] transition hover:bg-white"
                              >
                                Cancel
                              </button>

                              <button
                                type="button"
                                disabled={
                                  savingId ===
                                  field.id
                                }
                                onClick={() =>
                                  void handleCorrection(
                                    field,
                                  )
                                }
                                className="inline-flex items-center gap-1.5 rounded-lg bg-[#315F4D] px-3 py-2 text-[11px] font-bold text-white transition hover:bg-[#274F3F] disabled:opacity-50"
                              >
                                {savingId ===
                                field.id ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                  <Save className="h-3.5 w-3.5" />
                                )}

                                Save correction
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="mt-3 flex justify-end">
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedFieldId(
                                  field.id,
                                );

                                setEditingId(
                                  field.id,
                                );

                                setEditValue(
                                  field.value ||
                                    "",
                                );
                              }}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-[#DCE6E1] bg-white px-2.5 py-1.5 text-[10px] font-bold text-[#59746A] transition hover:bg-[#F5F9F7]"
                            >
                              <Pencil className="h-3 w-3" />
                              Correct
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  },
                )}
              </div>
            )}

            {/* VALIDATION RESULTS ---------------------------------------- */}

            {validation?.results?.length ? (
              <div className="border-t border-[#E8EFEC] bg-[#FAFCFB] px-5 py-4 sm:px-6">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-[#4A7962]" />

                  <p className="text-xs font-semibold text-[#40564C]">
                    Validation results
                  </p>
                </div>

                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  {validation.results
                    .slice(0, 8)
                    .map((result) => (
                      <div
                        key={`${result.field_name}-${result.rule_name}-${result.status}`}
                        className="rounded-lg border border-[#E3EBE7] bg-white px-3 py-2.5"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-[11px] font-semibold text-[#53675E]">
                            {prettyField(
                              result.rule_name,
                            )}
                          </p>

                          <span className="shrink-0 text-[9px] font-bold uppercase text-[#6B7D75]">
                            {result.status}
                          </span>
                        </div>

                        {result.message && (
                          <p className="mt-1 text-[10px] leading-4 text-[#87948E]">
                            {result.message}
                          </p>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            ) : null}
          </section>
        </>
      )}
    </div>
  );
}
