import React, { useState, useMemo } from "react";
import { calculateReportDiff, Finding } from "../utils/reportDiff";

interface ReportDiffViewProps {
  oldScanFindings: Finding[];
  newScanFindings: Finding[];
}

export const ReportDiffView: React.FC<ReportDiffViewProps> = ({
  oldScanFindings,
  newScanFindings,
}) => {
  const [activeTab, setActiveTab] = useState<
    "added" | "fixed" | "severityChanged"
  >("added");

  // useMemo ensures we don't recalculate on every basic re-render
  const diffs = useMemo(() => {
    return calculateReportDiff(oldScanFindings, newScanFindings);
  }, [oldScanFindings, newScanFindings]);

  const severityBadges: Record<string, string> = {
    CRITICAL: "bg-rag-red text-black border-rag-red",
    HIGH: "bg-rag-amber text-black border-rag-amber",
    MEDIUM: "bg-rag-blue text-black border-rag-blue",
    LOW: "bg-silver-bright text-black border-silver-bright",
    INFO: "bg-charcoal-dark text-silver border-silver/15",
    critical: "bg-rag-red text-black border-rag-red",
    high: "bg-rag-amber text-black border-rag-amber",
    medium: "bg-rag-blue text-black border-rag-blue",
    low: "bg-silver-bright text-black border-silver-bright",
    info: "bg-charcoal-dark text-silver border-silver/15",
  };

  return (
    <div className="w-full bg-charcoal border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-6 my-4">
      <h3 className="text-2xl font-black text-silver-bright mb-2 uppercase tracking-tighter italic">
        Scan Comparison Report
      </h3>
      <p className="text-sm font-mono text-silver/40 mb-6 uppercase tracking-widest">
        Tracking status changes between your selected scans.
      </p>

      {/* Tabs Layout Navigation */}
      <div className="flex border-b-4 border-black mb-4">
        <button
          onClick={() => setActiveTab("added")}
          className={`py-3 px-6 font-black text-sm uppercase tracking-widest border-b-4 transition-colors ${
            activeTab === "added"
              ? "border-rag-red text-rag-red bg-rag-red/10"
              : "border-transparent text-silver/40 hover:text-silver-bright"
          }`}
        >
          New Findings ({diffs.added.length})
        </button>
        <button
          onClick={() => setActiveTab("fixed")}
          className={`py-3 px-6 font-black text-sm uppercase tracking-widest border-b-4 transition-colors ${
            activeTab === "fixed"
              ? "border-rag-green text-rag-green bg-rag-green/10"
              : "border-transparent text-silver/40 hover:text-silver-bright"
          }`}
        >
          Fixed / Closed ({diffs.fixed.length})
        </button>
        <button
          onClick={() => setActiveTab("severityChanged")}
          className={`py-3 px-6 font-black text-sm uppercase tracking-widest border-b-4 transition-colors ${
            activeTab === "severityChanged"
              ? "border-rag-amber text-rag-amber bg-rag-amber/10"
              : "border-transparent text-silver/40 hover:text-silver-bright"
          }`}
        >
          Severity Changes ({diffs.severityChanged.length})
        </button>
      </div>

      {/* Content Rendering Box */}
      <div className="space-y-3">
        {activeTab === "added" &&
          (diffs.added.length === 0 ? (
            <div className="border-4 border-dashed border-silver-bright/10 bg-charcoal/40 p-8 text-center">
              <p className="text-sm font-mono uppercase tracking-widest text-silver/40">
                No new vulnerabilities introduced in this scan.
              </p>
            </div>
          ) : (
            diffs.added.map((f) => (
              <div
                key={f.id}
                className="flex justify-between items-start p-4 bg-rag-red/10 border-l-4 border-rag-red border-r border-silver-bright/10"
              >
                <div className="flex-1">
                  <h4 className="text-sm font-black uppercase text-silver-bright">
                    {f.title}
                  </h4>
                  <p className="text-xs font-mono text-silver/40 uppercase tracking-widest mt-1">
                    Target: {f.target || "Global scope"} // Category:{" "}
                    {f.category || "Uncategorized"}
                  </p>
                </div>
                <span
                  className={`text-xs font-black px-3 py-1 border-2 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${severityBadges[f.severity] || "bg-charcoal-dark text-silver border-silver/15"}`}
                >
                  {f.severity.toUpperCase()}
                </span>
              </div>
            ))
          ))}

        {activeTab === "fixed" &&
          (diffs.fixed.length === 0 ? (
            <div className="border-4 border-dashed border-silver-bright/10 bg-charcoal/40 p-8 text-center">
              <p className="text-sm font-mono uppercase tracking-widest text-silver/40">
                No vulnerabilities were resolved compared to last scan.
              </p>
            </div>
          ) : (
            diffs.fixed.map((f) => (
              <div
                key={f.id}
                className="flex justify-between items-start p-4 bg-rag-green/10 border-l-4 border-rag-green border-r border-silver-bright/10"
              >
                <div className="flex-1">
                  <h4 className="text-sm font-black uppercase text-silver/50 line-through">
                    {f.title}
                  </h4>
                  <p className="text-xs font-mono text-silver/30 uppercase tracking-widest mt-1">
                    Resolved successfully
                  </p>
                </div>
                <span className="text-xs font-black px-3 py-1 border-2 border-rag-green bg-rag-green text-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                  FIXED
                </span>
              </div>
            ))
          ))}

        {activeTab === "severityChanged" &&
          (diffs.severityChanged.length === 0 ? (
            <div className="border-4 border-dashed border-silver-bright/10 bg-charcoal/40 p-8 text-center">
              <p className="text-sm font-mono uppercase tracking-widest text-silver/40">
                No changes in vulnerability severities encountered.
              </p>
            </div>
          ) : (
            diffs.severityChanged.map(
              ({ finding, oldSeverity, newSeverity }) => (
                <div
                  key={finding.id}
                  className="flex justify-between items-start p-4 bg-rag-amber/10 border-l-4 border-rag-amber border-r border-silver-bright/10"
                >
                  <div className="flex-1">
                    <h4 className="text-sm font-black uppercase text-silver-bright">
                      {finding.title}
                    </h4>
                    <p className="text-xs font-mono text-silver/40 uppercase tracking-widest mt-1">
                      Target: {finding.target || "Global Scope"} // Category:{" "}
                      {finding.category || "Uncategorized"}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2 text-xs font-black">
                    <span
                      className={`px-3 py-1 border-2 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${severityBadges[oldSeverity]}`}
                    >
                      {oldSeverity.toUpperCase()}
                    </span>
                    <span className="text-silver/40 font-mono">→</span>
                    <span
                      className={`px-3 py-1 border-2 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${severityBadges[newSeverity]}`}
                    >
                      {newSeverity.toUpperCase()}
                    </span>
                  </div>
                </div>
              ),
            )
          ))}
      </div>
    </div>
  );
};
