import { useEffect, useState } from "react";

interface ScanMeta {
  id: string;
  filename: string;
  target: string;
  timestamp: number;
  finding_count: number;
  severity_summary: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
}

interface Props {
  onSelect: (scanId: string) => void;
  activeScanId?: string;
}

export default function ScanHistory({ onSelect, activeScanId }: Props) {
  const [history, setHistory] = useState<ScanMeta[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/history")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load audit records");
        return res.json();
      })
      .then((data) => {
        setHistory(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error connecting to history module:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="w-64 border-2 border-black bg-charcoal/95 p-4 font-mono text-[10px] text-silver/45 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] tracking-wider">
        // SYNCING_MATRIX_INDEX...
      </div>
    );
  }

  return (
    <div className="w-64 flex flex-col gap-3 shrink-0 self-start lg:sticky lg:top-4 lg:z-30">
      {/* Title block formatted exactly like your main filter labels */}
      <div className="border-2 border-black bg-charcoal/40 px-3 py-2 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
        <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-silver-bright">
          // Session Index
        </h3>
      </div>

      <div className="flex flex-col gap-3 max-h-[70vh] overflow-y-auto pr-1">
        {history.length === 0 ? (
          <div className="border-2 border-dashed border-silver-bright/10 bg-charcoal/40 p-4 text-center">
            <p className="text-[11px] font-mono text-silver/35 uppercase tracking-wider">No archived logs</p>
          </div>
        ) : (
          history.map((scan) => {
            const isSelected = activeScanId === scan.id;
            const formattedDate = new Date(scan.timestamp * 1000).toLocaleDateString(undefined, {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            });

            return (
              <button
                key={scan.id}
                onClick={() => onSelect(scan.id)}
                className={`
                  w-full text-left p-3 transition-all duration-150 border-2 border-black font-mono relative cursor-pointer
                  shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none
                  ${isSelected
                    ? "bg-silver-bright text-black font-bold border-silver-bright"
                    : "bg-charcoal text-silver/70 hover:text-silver-bright hover:border-silver-bright/30"
                  }
                `}
              >
                {/* Visual marker bar matching your findings rows */}
                <span className={`absolute inset-y-0 left-0 w-1 ${isSelected ? 'bg-black' : 'bg-silver/20'}`} />

                <div className="pl-2 space-y-1">
                  <div className="text-sm font-black uppercase tracking-tight truncate">
                    {scan.target}
                  </div>

                  <div className="text-[10px] opacity-60 tracking-normal">
                    {formattedDate}
                  </div>

                  <div className="flex items-center justify-between gap-2 pt-2">
                    <span className={`text-[9px] px-1.5 py-0.5 border uppercase font-bold ${
                      isSelected ? "border-black/30 bg-black/5" : "border-silver-bright/10 bg-charcoal-dark"
                    }`}>
                      {scan.finding_count} hits
                    </span>

                    {scan.severity_summary.critical > 0 && (
                      <span className="px-1.5 py-0.5 bg-rag-red text-black font-black text-[9px] shadow-[2px_2px_0px_rgba(0,0,0,1)]">
                        CRIT
                      </span>
                    )}
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}