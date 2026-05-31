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
      <div className="text-muted-foreground text-sm p-4">
        No past scans found.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 p-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground px-2 mb-1">
        Scan History
      </h3>
      {history.map((scan) => (
        <button
          key={scan.task_id}
          onClick={() => onSelect(scan.task_id)}
          className={`text-left rounded-md px-3 py-2 text-sm transition-colors ${
            activeTaskId === scan.task_id
              ? "bg-primary text-primary-foreground"
              : "hover:bg-muted"
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
