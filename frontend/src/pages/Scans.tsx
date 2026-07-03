import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence, type Variants } from "framer-motion";
import { API_BASE, deleteTask, clearAllTasks, bulkDeleteTasks, startTask, ExecutionContext } from "../api";
import { routePath } from "../routes";
import {
  parseDateSafe,
  formatLocaleDate,
  formatLocaleTime,
} from "../utils/date";
import { ConfirmModal } from "../components/ConfirmModal";
import Pagination from "../components/Pagination";

interface Task {
  task_id: string;
  plugin_id: string;
  tool: string;
  target: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  scan_phase?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  error_message?: string;
  inputs?: any;
  preset?: string;
  execution_context?: ExecutionContext;
  queue_position?: number;
  pending_count?: number;
}

const statusFilters = [
  { value: "all", label: "ALL_OPERATIONS" },
  { value: "running", label: "ACTIVE_EXECUTION" },
  { value: "completed", label: "TERMINATED_SUCCESS" },
  { value: "failed", label: "SYSTEM_FAILURE" },
  { value: "cancelled", label: "MANUAL_ABORT" },
];

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { type: "spring", stiffness: 200, damping: 20 },
  },
};

export default function Scans() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const PAGE_LIMIT = 10;

  // Modal state for confirm dialogs
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
    type: "danger" | "warning" | "info";
  }>({
    isOpen: false,
    title: "",
    message: "",
    onConfirm: () => {},
    type: "warning",
  });

  // Ref so the visibilitychange handler always sees the current timer id
  const pollingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestSeqRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  function scheduleNextPoll() {
    pollingTimerRef.current = setTimeout(async () => {
      await loadTasks();
      if (!abortRef.current?.signal.aborted) {
        scheduleNextPoll();
      }
    }, 5000);
  }

  function startPolling() {
    stopPolling();
    scheduleNextPoll();
  }

  function stopPolling() {
    if (pollingTimerRef.current !== null) {
      clearTimeout(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
  }

  useEffect(() => {
    loadTasks();
    startPolling();

    function handleVisibilityChange() {
      if (document.visibilityState === "hidden") {
        stopPolling();
      } else {
        abortRef.current?.abort();
        abortRef.current = new AbortController();
        loadTasks();
        startPolling();
      }
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      stopPolling();
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [filter, page]);

  async function loadTasks() {
    const requestSeq = requestSeqRef.current + 1;
    requestSeqRef.current = requestSeq;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const params = new URLSearchParams();
      if (filter !== "all") params.set("status", filter);
      params.set("page", String(page));
      params.set("per_page", String(PAGE_LIMIT));

      const res = await fetch(`${API_BASE}/tasks?${params.toString()}`, {
        signal: controller.signal,
      });
      if (!res.ok) {
        throw new Error(`Failed to load tasks: ${res.status}`);
      }
      const data = await res.json();
      if (requestSeq !== requestSeqRef.current) return;

      setTasks([...(data.tasks || [])]);
      if (data.pagination?.total_items !== undefined) {
        setTotal(data.pagination.total_items);
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      console.error("Failed to load tasks:", err);
    } finally {
      if (requestSeq === requestSeqRef.current) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  }

  function handleFilterChange(value: string) {
    setFilter(value);
    setPage(1);
  }

  async function handleRescan(task: Task) {
    try {
      const data = await startTask(
        task.plugin_id,
        task.inputs || {},
        true,
        task.preset,
        task.execution_context,
      );
      if (data.task_id) {
        navigate(routePath.task(data.task_id));
      }
    } catch (err) {
      console.error("Rescan failed:", err);
    }
  }

  async function handleTaskDelete(taskId: string) {
    setModalState({
      isOpen: true,
      title: "Delete Scan Record",
      message: "Are you sure you want to delete this scan record? This will also remove associated findings and reports.",
      type: "danger",
      onConfirm: async () => {
        try {
          await deleteTask(taskId);
          setTasks((prev) => prev.filter((t) => t.task_id !== taskId));
          if (expandedId === taskId) setExpandedId(null);
          setModalState(prev => ({ ...prev, isOpen: false }));
        } catch (err) {
          console.error("Failed to delete task:", err);
          alert("Failed to delete task. It might still be running.");
          setModalState(prev => ({ ...prev, isOpen: false }));
        }
      },
    });
  }

  async function handleClearAll() {
    setModalState({
      isOpen: true,
      title: "CRITICAL OPERATION",
      message: "CRITICAL: Are you sure you want to PURGE ALL RECORDS? This will wipe all scan history, findings, assets, and reports. This action is irreversible.",
      type: "danger",
      onConfirm: async () => {
        try {
          await clearAllTasks();
          setTasks([]);
          setSelectedIds([]);
          setExpandedId(null);
          setModalState(prev => ({ ...prev, isOpen: false }));
        } catch (err) {
          console.error("Failed to clear history:", err);
          alert("Failed to clear history. Ensure no tasks are currently running.");
          setModalState(prev => ({ ...prev, isOpen: false }));
        }
      },
    });
  }

  async function handleBulkDelete() {
    if (selectedIds.length === 0) return;
    setModalState({
      isOpen: true,
      title: "Bulk Delete Records",
      message: `Are you sure you want to delete ${selectedIds.length} selected scan records?`,
      type: "danger",
      onConfirm: async () => {
        try {
          await bulkDeleteTasks(selectedIds);
          setTasks((prev) => prev.filter((t) => !selectedIds.includes(t.task_id)));
          setSelectedIds([]);
          setModalState(prev => ({ ...prev, isOpen: false }));
        } catch (err) {
          console.error("Bulk delete failed:", err);
          alert("Failed to delete some tasks. Ensure they are not currently running.");
          setModalState(prev => ({ ...prev, isOpen: false }));
        }
      },
    });
  }

  function toggleSelection(taskId: string, e: React.MouseEvent) {
    e.stopPropagation();
    setSelectedIds((prev) =>
      prev.includes(taskId)
        ? prev.filter((id) => id !== taskId)
        : [...prev, taskId],
    );
  }

  function toggleSelectAll() {
    if (selectedIds.length === tasks.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(tasks.map((t) => t.task_id));
    }
  }

  function formatDuration(seconds?: number) {
    if (!seconds) return null;
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  }

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
      {/* Neo-Brutalist Header */}
      <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10">
        <div className="space-y-4">
          <div className="bg-rag-blue text-black px-4 py-1 text-xs font-black uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            Operational_Registry_v10.1
          </div>
          <h1 className="text-6xl md:text-8xl font-black text-silver-bright uppercase tracking-tighter leading-none italic">
            Operational{" "}
            <span
              className="text-transparent stroke-white"
              style={{ WebkitTextStroke: "1px var(--accent-silver-bright)" }}
            >
              Registry
            </span>
          </h1>
          <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic flex items-center gap-4">
            Total_Registry_Keys: {total} // SYSTEM_STATUS:{" "}
            {loading ? "SYNCING..." : "SYNCED"}
            <span
              className={`w-2 h-2 rounded-full ${loading ? "bg-rag-amber animate-pulse" : "bg-rag-green"}`}
            ></span>
          </p>
        </div>

        <div className="flex items-center gap-12 border-l-4 border-silver-bright/10 pl-12 hidden lg:flex">
          <div className="text-right">
            <span className="text-[10px] font-black text-silver/40 uppercase tracking-[0.3em] block mb-2 italic">
              Integrity_Check
            </span>
            <span className="text-xs font-mono text-rag-green uppercase font-black">
              OPSEC_CLEARANCE_L5
            </span>
          </div>
        </div>
      </header>

      {/* Filtration Block */}
      <section className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col xl:flex-row justify-between items-center gap-12">
        <div className="flex flex-wrap items-center gap-4">
          <button
            onClick={toggleSelectAll}
            className={`px-6 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-2 flex items-center gap-3 ${
              selectedIds.length === tasks.length && tasks.length > 0
                ? "bg-rag-blue text-black border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]"
                : "bg-charcoal-dark text-silver/30 border-silver-bright/5 hover:border-silver-bright/20"
            }`}
          >
            <span className="material-symbols-outlined text-sm">
              {selectedIds.length === tasks.length && tasks.length > 0
                ? "check_box"
                : "check_box_outline_blank"}
            </span>
            Select_All
          </button>
          <div className="w-1 h-8 bg-black/40 mx-2 hidden md:block"></div>
          {statusFilters.map((f) => (
            <button
              key={f.value}
              onClick={() => handleFilterChange(f.value)}
              className={`px-6 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-2 flex items-center gap-2 ${
                filter === f.value
                  ? "bg-silver-bright text-black border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] -translate-x-0.5 -translate-y-0.5"
                  : "bg-charcoal-dark text-silver/30 border-silver-bright/5 hover:border-silver-bright/20"
              }`}
            >
              {f.label}
              {filter === f.value && <span className="w-1 h-3 bg-black"></span>}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-6">
          {tasks.length > 0 && (
            <button
              onClick={handleClearAll}
              className="px-6 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-2 bg-rag-red/10 text-rag-red border-rag-red/20 hover:bg-rag-red hover:text-black hover:border-black flex items-center gap-2 italic"
            >
              Purge_All_Records
              <span className="material-symbols-outlined text-sm">
                delete_forever
              </span>
            </button>
          )}
          <div className="flex items-center gap-4 text-[10px] font-mono text-silver/20 uppercase italic tracking-widest hidden sm:flex">
            Isolation_Protocol_Active //{" "}
            <span className="text-rag-blue">v4_stable</span>
          </div>
        </div>
      </section>

      {/* Timeline Operations Feed */}
      <section className="relative">
        {/* Vertical Timeline Cable */}
        <div className="absolute left-[39px] top-0 bottom-0 w-1 bg-silver-bright/5 hidden md:block"></div>

        <AnimatePresence mode="popLayout">
          {tasks.length > 0 ? (
            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              className="space-y-8"
            >
              {tasks.map((task) => {
                const createDate = parseDateSafe(task.created_at);
                const startDate = task.started_at
                  ? parseDateSafe(task.started_at)
                  : null;
                const endDate = task.completed_at
                  ? parseDateSafe(task.completed_at)
                  : null;

                return (
                  <motion.div
                    key={task.task_id}
                    variants={itemVariants}
                    layout
                    className={`relative group md:pl-20 transition-all`}
                  >
                    {/* Timeline Node */}
                    <div
                      className={`absolute left-[31px] top-12 w-5 h-5 border-4 border-black z-10 hidden md:block transition-all duration-500 ${
                        task.status === "completed"
                          ? "bg-rag-green shadow-[0_0_15px_rgba(34,197,94,0.3)]"
                          : task.status === "failed"
                            ? "bg-rag-red"
                            : task.status === "running"
                              ? "bg-rag-amber animate-pulse"
                              : "bg-silver/10"
                      }`}
                    ></div>

                    <div
                      className={`bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] transition-all cursor-pointer relative overflow-hidden group/card ${
                        expandedId === task.task_id
                          ? "border-rag-blue/40 shadow-[12px_12px_0px_0px_rgba(0,0,0,1)]"
                          : ""
                      }`}
                      onClick={() =>
                        setExpandedId(
                          expandedId === task.task_id ? null : task.task_id,
                        )
                      }
                    >
                      <div className="flex flex-col xl:flex-row justify-between gap-8">
                        <div className="flex-1 space-y-6">
                          <div className="flex flex-wrap items-center gap-4">
                            <div
                              onClick={(e) => toggleSelection(task.task_id, e)}
                              className={`w-10 h-10 border-4 border-black flex items-center justify-center transition-all ${
                                selectedIds.includes(task.task_id)
                                  ? "bg-rag-blue text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] -translate-x-1 -translate-y-1"
                                  : "bg-charcoal-dark text-silver/10 hover:border-rag-blue/40"
                              }`}
                            >
                              <span className="material-symbols-outlined text-base font-black">
                                {selectedIds.includes(task.task_id)
                                  ? "check"
                                  : "add"}
                              </span>
                            </div>
                            <span
                              className={`px-2 py-0.5 text-[9px] font-black uppercase italic border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${
                                task.status === "completed"
                                  ? "bg-rag-green text-black"
                                  : task.status === "failed"
                                    ? "bg-rag-red text-black"
                                    : "bg-charcoal-dark text-silver-bright/50"
                              }`}
                            >
                              {task.status}
                            </span>
                            {task.status === "queued" &&
                              task.queue_position && (
                                <span className="text-[9px] font-mono text-rag-amber uppercase tracking-widest">
                                  Queue #{task.queue_position}/
                                  {task.pending_count}
                                </span>
                              )}
                            <span className="text-[10px] font-mono text-silver/20 uppercase tracking-widest italic">
                              OP_ID_{task.task_id.split("-")[0].toUpperCase()}
                            </span>
                          </div>

                          <div className="space-y-2">
                            <h3 className="text-3xl font-black text-silver-bright uppercase tracking-tighter italic leading-none group-hover/card:text-rag-blue transition-colors">
                              {task.tool}
                            </h3>
                            <p className="text-xs font-mono text-silver/40 uppercase tracking-widest flex items-center gap-3">
                              <span className="material-symbols-outlined text-sm">
                                target
                              </span>
                              {task.target}
                            </p>
                          </div>
                        </div>

                        <div className="flex flex-row xl:flex-col items-center xl:items-end justify-between xl:justify-center gap-8 shrink-0">
                          <div className="text-left xl:text-right">
                            <p className="text-[8px] font-black uppercase text-silver/20 tracking-[0.3em] mb-1 italic">
                              Historical_Execution
                            </p>
                            <p className="text-xs font-mono text-silver-bright/80 uppercase">
                              {formatLocaleDate(createDate)} //{" "}
                              {formatLocaleTime(createDate)}
                            </p>
                          </div>
                          <div className="flex items-center gap-3">
                            {task.duration_seconds && (
                              <div className="bg-charcoal-dark border-2 border-black px-4 py-2 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
                                <p className="text-[10px] font-black font-mono text-rag-blue leading-none">
                                  {formatDuration(
                                    task.duration_seconds,
                                  )?.toUpperCase()}
                                </p>
                              </div>
                            )}
                            {(task.status === "completed" ||
                              task.status === "failed" ||
                              task.status === "cancelled") && (
                              <button
                                type="button"
                                aria-label={`Re-run ${task.tool} scan`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRescan(task);
                                }}
                                className="w-10 h-10 border-4 border-black bg-rag-blue text-black flex items-center justify-center transition-all hover:bg-rag-blue/80 active:translate-x-0.5 active:translate-y-0.5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] active:shadow-none"
                              >
                                <span className="material-symbols-outlined text-sm font-black">
                                  replay
                                </span>
                              </button>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Error Notification Panel */}
                      {task.status === "failed" && task.error_message && (() => {
                        const isTimeoutFailure =
                          task.error_message?.toLowerCase().includes("timeout") ||
                          task.error_message?.toLowerCase().includes("timed out");
                        return (
                          <div
                            className={`mt-6 border-4 border-black p-5 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] ${
                              isTimeoutFailure
                                ? "bg-rag-amber/10 border-l-rag-amber"
                                : "bg-rag-red/10 border-l-rag-red"
                            }`}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <div className="flex items-start gap-4">
                              <span
                                className={`material-symbols-outlined text-lg shrink-0 mt-0.5 ${
                                  isTimeoutFailure ? "text-rag-amber" : "text-rag-red"
                                }`}
                              >
                                {isTimeoutFailure ? "timer_off" : "error"}
                              </span>
                              <div className="space-y-2 min-w-0">
                                <p
                                  className={`text-[10px] font-black uppercase tracking-[0.3em] ${
                                    isTimeoutFailure ? "text-rag-amber" : "text-rag-red"
                                  }`}
                                >
                                  {isTimeoutFailure ? "SCAN_TIMEOUT_DETECTED" : "SCAN_FAILED"}
                                </p>
                                {isTimeoutFailure && (
                                  <p className="text-[10px] font-mono text-silver/60 uppercase tracking-widest">
                                    This scan exceeded its execution limit and was terminated automatically.
                                  </p>
                                )}
                                <p className="text-[10px] font-mono text-silver/50 break-words">
                                  {task.error_message}
                                </p>
                              </div>
                            </div>
                          </div>
                        );
                      })()}

                      {/* Expandable Details Block */}
                      <AnimatePresence>
                        {expandedId === task.task_id && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-12 pt-12 border-t-4 border-black flex flex-wrap items-center justify-between gap-4 w-full bg-charcoal-dark/20 -mx-8 -mb-8 p-8 border-dashed">
                              <div className="flex flex-wrap items-start gap-4">
                                <div className="space-y-4">
                                  <h5 className="text-[10px] font-black text-silver-bright uppercase tracking-[0.3em] italic flex items-center gap-3">
                                    <span className="w-1.5 h-3 bg-rag-blue"></span>{" "}
                                    Signal_Metadata
                                  </h5>
                                  <div className="space-y-2">
                                    <p className="text-[10px] font-mono text-silver/40">
                                      PLUGIN:{" "}
                                      <span className="text-silver-bright uppercase">
                                        {task.plugin_id}
                                      </span>
                                    </p>
                                    {task.status === 'running' && task.scan_phase && (
                                      <p className="text-[10px] font-mono text-rag-blue/80 uppercase tracking-widest">
                                        PHASE: {task.scan_phase.replace(/_/g, ' ')}
                                      </p>
                                    )}
                                    <p className="text-[10px] font-mono text-silver/40">
                                      SESSION:{" "}
                                      <span className="text-silver-bright uppercase">
                                        ENCRYPTED_VTX
                                      </span>
                                    </p>
                                  </div>
                                </div>

                                <div className="space-y-4">
                                  <h5 className="text-[10px] font-black text-silver-bright uppercase tracking-[0.3em] italic flex items-center gap-3">
                                    <span className="w-1.5 h-3 bg-rag-amber"></span>{" "}
                                    Time_Matrix
                                  </h5>
                                  <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1">
                                      <span className="text-[8px] text-silver/20 uppercase font-black tracking-widest">
                                        In_Lock
                                      </span>
                                      <span className="text-[10px] font-mono text-silver-bright block">
                                        {startDate
                                          ? formatLocaleTime(startDate)
                                          : "PENDING"}
                                      </span>
                                    </div>
                                    <div className="space-y-1">
                                      <span className="text-[8px] text-silver/20 uppercase font-black tracking-widest">
                                        Release
                                      </span>
                                      <span className="text-[10px] font-mono text-silver-bright block">
                                        {endDate
                                          ? formatLocaleTime(endDate)
                                          : "N/A"}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              </div>

                              <div className="flex flex-wrap items-center gap-3">
                                {(task.status === "completed" ||
                                  task.status === "failed" ||
                                  task.status === "cancelled") && (
                                  <button
                                    className="bg-rag-red/20 text-rag-red border-2 border-rag-red/20 hover:bg-rag-red hover:text-black hover:border-black px-6 py-4 text-[10px] font-black uppercase tracking-widest transition-all flex items-center gap-3 italic"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleTaskDelete(task.task_id);
                                    }}
                                  >
                                    Delete_Record
                                    <span className="material-symbols-outlined text-sm">
                                      delete
                                    </span>
                                  </button>
                                )}
                                {(task.status === "completed" ||
                                  task.status === "failed") && (
                                  <button
                                    className="bg-rag-blue text-black px-8 py-4 text-[10px] font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center gap-3 group/btn italic"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleRescan(task);
                                    }}
                                  >
                                    Rescan_Signal
                                    <span className="material-symbols-outlined text-sm group-hover/btn:translate-x-1 transition-transform">
                                      replay
                                    </span>
                                  </button>
                                )}
                                <button
                                  className="bg-silver-bright text-black px-8 py-4 text-[10px] font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center gap-3 group/btn italic"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    navigate(routePath.task(task.task_id));
                                  }}
                                >
                                  Open_Deep_Brief
                                  <span className="material-symbols-outlined text-sm group-hover/btn:translate-x-1 transition-transform">
                                    arrow_right_alt
                                  </span>
                                </button>
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          ) : (
            <div className="py-40 bg-charcoal/30 border-4 border-dashed border-silver-bright/5 text-center flex flex-col items-center gap-8">
              <span className="material-symbols-outlined text-silver/5 text-9xl">
                inventory_2
              </span>
              <div className="space-y-2">
                <p className="text-xl font-black text-silver/20 uppercase tracking-[0.4em] italic">
                  Archive Isolated
                </p>
                <p className="text-xs font-mono text-silver/10 uppercase tracking-widest">
                  No historical signal streams available for current selection
                </p>
              </div>
            </div>
          )}
        </AnimatePresence>
        {total > PAGE_LIMIT && (
          <Pagination
            page={page}
            total={total}
            limit={PAGE_LIMIT}
            loading={loading}
            onPrev={() => setPage((p) => p - 1)}
            onNext={() => setPage((p) => p + 1)}
          />
        )}
      </section>

      {/* Floating Bulk Action Bar */}
      <AnimatePresence>
        {selectedIds.length > 0 && (
          <motion.div
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            className="fixed bottom-12 left-1/2 -translate-x-1/2 z-50 w-full max-w-2xl px-6"
          >
            <div className="bg-black border-4 border-rag-blue p-6 shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] flex items-center justify-between gap-8">
              <div className="flex items-center gap-6">
                <div className="bg-rag-blue text-black px-4 py-2 text-xl font-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                  {selectedIds.length}
                </div>
                <div className="space-y-1">
                  <p className="text-[10px] font-black text-rag-blue uppercase tracking-widest italic">
                    Records_Selected_For_Pruning
                  </p>
                  <p className="text-[8px] font-mono text-silver/30 uppercase tracking-[0.2em]">
                    Bulk_Action_Protocol_v4_Active
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setSelectedIds([])}
                  className="px-6 py-3 text-[10px] font-black uppercase tracking-widest text-silver/40 hover:text-silver transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBulkDelete}
                  className="bg-rag-red text-black px-8 py-3 text-[10px] font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center gap-3 italic"
                >
                  Prune_Selected_Records
                  <span className="material-symbols-outlined text-sm">
                    delete_sweep
                  </span>
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Restricted Footer */}
      <footer className="pt-24 opacity-20 pointer-events-none select-none flex flex-col md:flex-row justify-between items-center gap-8 text-[9px] font-black uppercase tracking-[0.5em] italic">
        <div className="flex items-center gap-4">
          <span className="w-8 h-8 border-4 border-silver/20 flex items-center justify-center font-serif text-lg">
            S
          </span>
          SECUSCAN ARCHIVE INTEGRITY PROTOCOL v10.1
        </div>
        <div className="flex gap-2">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((i) => (
            <div key={i} className="w-1.5 h-3 bg-silver/20"></div>
          ))}
        </div>
      </footer>

      {/* Confirm Modal */}
      <ConfirmModal
        isOpen={modalState.isOpen}
        title={modalState.title}
        message={modalState.message}
        onConfirm={modalState.onConfirm}
        onCancel={() => setModalState(prev => ({ ...prev, isOpen: false }))}
        type={modalState.type}
      />
    </div>
  );
}
