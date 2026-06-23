import React from "react";
interface PaginationProps {
  page: number;
  total: number;
  limit: number;
  loading: boolean;
  onPrev: () => void;
  onNext: () => void;
}
export default function Pagination({
  page,
  total,
  limit,
  loading,
  onPrev,
  onNext,
}: PaginationProps) {
  const start = total === 0 ? 0 : (page - 1) * limit + 1;
  const end = Math.min(page * limit, total);
  const isFirst = page === 1;
  const isLast = end >= total;
  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-6 border-t-4 border-silver-bright/10 pt-8">
      <p
        aria-live="polite"
        aria-atomic="true"
        className="text-[10px] font-mono text-[var(--text-secondary)]/30 uppercase tracking-widest italic"
      >
        <span className="sr-only">
          {total === 0
            ? "No records found."
            : `Showing records ${start} to ${end} of ${total} total.`}
        </span>
        <span aria-hidden="true">
          Showing_Records:{" "}
          <span className="text-[var(--text-secondary)]-bright">
            {start}–{end}
          </span>{" "}
          // Total: <span className="text-rag-blue">{total}</span>
        </span>
      </p>
      <div className="flex items-center gap-4">
        <button
          onClick={onPrev}
          disabled={isFirst || loading}
          aria-disabled={isFirst || loading}
          aria-label="Go to previous page"
          className="px-6 py-3 text-[10px] font-black uppercase tracking-widest border-2 border-silver-bright/10 text-[var(--text-secondary)]/40 hover:border-rag-blue hover:text-rag-blue transition-all flex items-center gap-2 disabled:opacity-20 disabled:cursor-not-allowed italic"
        >
          <span className="material-symbols-outlined text-sm" aria-hidden="true">arrow_back</span>
          Prev_Page
        </button>
        <div
          aria-label={`Page ${page}`}
          className="bg-[var(--bg-primary)] border-2 border-black px-4 py-3 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]"
        >
          <span className="text-[10px] font-black font-mono text-rag-blue" aria-hidden="true">
            {page}
          </span>
        </div>
        <button
          onClick={onNext}
          disabled={isLast || loading}
          aria-disabled={isLast || loading}
          aria-label="Go to next page"
          className="px-6 py-3 text-[10px] font-black uppercase tracking-widest border-2 border-silver-bright/10 text-[var(--text-secondary)]/40 hover:border-rag-blue hover:text-rag-blue transition-all flex items-center gap-2 disabled:opacity-20 disabled:cursor-not-allowed italic"
        >
          Next_Page
          <span className="material-symbols-outlined text-sm" aria-hidden="true">
            arrow_forward
          </span>
        </button>
      </div>
    </div>
  );
}
