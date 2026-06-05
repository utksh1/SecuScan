import { useEffect, useState } from "react";
import { getTasks } from "../api";

interface ScanMeta {
  task_id: string;
  tool_name: string;
  target: string;
  status: string;
  created_at: string;
  duration_seconds?: number;
}

interface Props {
  onSelect: (taskId: string) => void;
  activeTaskId?: string;
}

export function ScanHistory({ onSelect, activeTaskId }: Props) {
  const [history, setHistory] = useState<ScanMeta[]>([]);

  useEffect(() => {
    const params = new URLSearchParams({ per_page: "20", page: "1" });
    getTasks(params)
      .then((data: any) => setHistory(data.tasks || []))
      .catch(console.error);
  }, []);

  if (history.length === 0) {
    return (
      <div className="text-silver/40 text-xs font-mono uppercase tracking-[0.15em] p-4">
        No past scans found.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 p-2">
      <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-silver/40 px-2 mb-1">
  Load Past Scan
</h3>
      {history.map((scan) => (
        <button
          key={scan.task_id}
          onClick={() => onSelect(scan.task_id)}
          className={`text-left rounded-md px-3 py-2 text-sm transition-colors ${
  activeTaskId === scan.task_id
    ? "bg-silver-bright/10 text-silver-bright border-l-2 border-rag-red"
    : "text-silver/70 hover:bg-silver-bright/5 hover:text-silver-bright"
}`}
        >
          <div className="font-medium truncate">{scan.target || scan.tool_name}</div>
          <div className="text-xs text-muted-foreground flex gap-2 mt-0.5">
            <span>{new Date(scan.created_at).toLocaleDateString()}</span>
            <span>·</span>
            <span className={scan.status === "completed" ? "text-green-500" : scan.status === "failed" ? "text-red-500" : ""}>
              {scan.status}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}
