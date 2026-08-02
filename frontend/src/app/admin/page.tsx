"use client";

import { useState, useEffect, useRef } from "react";
import { Lock, Play, Zap, AlertCircle, CheckCircle2, LayoutDashboard, X, BarChart2 } from "lucide-react";
import { clsx } from "clsx";

type IngestStatus = {
  status: "idle" | "running" | "completed" | "failed";
  run_id: string | null;
  message: string;
  start_time?: number | null;
  logs?: { time: string; text: string }[];
};

type PipelineStats = {
  run_id: string;
  source: string;
  run_timestamp: string;
  raw_ingested: number;
  stage1_passed: number;
  stage2_tagged: number;
  relevant_embedded: number;
  irrelevant_discarded: number;
};

export default function AdminPage() {
  const [tokenInput, setTokenInput] = useState("");
  const [adminToken, setAdminToken] = useState<string>("");
  
  const [statusData, setStatusData] = useState<IngestStatus>({ status: "idle", run_id: null, message: "" });
  const [isPolling, setIsPolling] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);

  const [authError, setAuthError] = useState("");
  const [completedToast, setCompletedToast] = useState(false);
  
  const [showSummaryModal, setShowSummaryModal] = useState(false);
  const [runSummary, setRunSummary] = useState<PipelineStats[]>([]);
  
  const [logs, setLogs] = useState<{ time: string; text: string }[]>([]);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll terminal
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const getProgressPercentage = () => {
    if (statusData.status === "completed") return 100;
    if (statusData.status === "idle" || statusData.status === "failed") return 0;
    
    const msg = (statusData.message || "").toLowerCase();
    let base = 5;
    if (msg.includes("play_store")) base = 10;
    else if (msg.includes("app_store")) base = 30;
    else if (msg.includes("reddit")) base = 50;
    else if (msg.includes("youtube")) base = 70;
    
    let stageOffset = 0;
    if (msg.includes("filtering")) stageOffset = 5;
    else if (msg.includes("extracting")) stageOffset = 10;
    else if (msg.includes("embedding")) stageOffset = 15;
    
    return Math.min(base + stageOffset, 95);
  };

  // Hydrate token from sessionStorage on mount
  useEffect(() => {
    const stored = sessionStorage.getItem("adminToken");
    if (stored) {
      setAdminToken(stored);
      setTokenInput(stored);
    }
  }, []);

  // Initial status check
  useEffect(() => {
    fetch("/api/admin/ingest/status", {
      headers: { "Authorization": `Bearer ${sessionStorage.getItem("adminToken") || ""}` }
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch status");
        return res.json();
      })
      .then((data: IngestStatus) => {
        setStatusData(data);
        if (data.logs) setLogs(data.logs);
        if (data.start_time) setStartTime(data.start_time * 1000); // Python time.time() is in seconds
        
        if (data.status === "running") {
          setIsPolling(true);
        }
      })
      .catch((e) => console.error(e));
  }, []);

  // Polling logic
  useEffect(() => {
    if (!isPolling) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch("/api/admin/ingest/status", {
          headers: { "Authorization": `Bearer ${sessionStorage.getItem("adminToken") || ""}` }
        });
        if (!res.ok) throw new Error("Failed to fetch status");
        const data: IngestStatus = await res.json();
        setStatusData(data);
        if (data.logs) setLogs(data.logs);
        
        if (data.status === "completed" || data.status === "failed") {
          setIsPolling(false);
          if (data.status === "completed") {
            fetch("/api/stats")
              .then(res => res.json())
              .then((stats: PipelineStats[]) => {
                if (data.run_id) {
                  const currentRunStats = stats.filter(s => s.run_id.startsWith(data.run_id!));
                  setRunSummary(currentRunStats);
                  setShowSummaryModal(true);
                }
              })
              .catch(() => {});
          }
        }
      } catch (e) {
        console.error(e);
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [isPolling]);

  // Elapsed timer logic
  useEffect(() => {
    if (statusData.status === "running") {
      const startMs = statusData.start_time ? statusData.start_time * 1000 : (startTime || Date.now());
      if (!startTime && !statusData.start_time) setStartTime(startMs);
      
      const int = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startMs) / 1000));
      }, 1000);
      return () => clearInterval(int);
    } else if (statusData.status === "idle") {
      setStartTime(null);
      setElapsed(0);
    }
  }, [statusData.status, statusData.start_time, startTime]);

  const handleSaveToken = () => {
    sessionStorage.setItem("adminToken", tokenInput);
    setAdminToken(tokenInput);
    setAuthError("");
  };

  const triggerIngest = async (mode: "demo" | "full") => {
    setAuthError("");
    setCompletedToast(false);
    setShowSummaryModal(false);
    setLogs([]);

    try {
      const res = await fetch("/api/admin/ingest", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${sessionStorage.getItem("adminToken") || ""}`,
        },
        body: JSON.stringify({ mode }),
      });

      if (res.status === 401) {
        setAuthError("Invalid admin token");
        sessionStorage.removeItem("adminToken");
        setAdminToken("");
        setTokenInput("");
        return;
      }

      if (!res.ok) throw new Error("Failed to trigger pipeline");

      const data = await res.json();
      setStatusData({ status: "running", message: data.message || `Started ${mode} pipeline`, run_id: data.run_id });
      setIsPolling(true);
      setStartTime(Date.now());
      setElapsed(0);

    } catch (e: any) {
      setStatusData({ status: "failed", message: e.message || "Unknown error", run_id: null });
    }
  };

  const isControlsDisabled = statusData.status === "running";

  return (
    <div className="w-full max-w-[860px] mx-auto p-8 space-y-10">
      <div>
        <h1 className="text-[24px] font-sans font-bold text-ink mb-2">Admin Console</h1>
        <p className="text-[15px] font-sans text-ink-muted">
          Manage data ingestion and engine settings.
        </p>
      </div>

      {/* Ingestion Controls */}
      <div className="space-y-4">
        <h2 className="text-[18px] font-sans font-semibold text-ink">Data Ingestion</h2>

        
        {authError && (
          <div className="flex items-center space-x-2 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px] font-mono">
            <AlertCircle size={16} />
            <span>{authError}</span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Demo Run Card */}
          <div className={clsx("border rounded-lg p-6 transition-opacity", isControlsDisabled ? "opacity-50 border-surface bg-bg" : "border-surface bg-surface")}>
            <div className="flex items-center space-x-3 mb-2">
              <Zap size={20} className={isControlsDisabled ? "text-ink-muted" : "text-accent"} />
              <h3 className="text-[15px] font-sans font-semibold text-ink">Quick demo run</h3>
            </div>
            <p className="text-[13px] font-sans text-ink-muted mb-6 h-10">
              ~45s, capped at 20 items per source. Good for quick verification.
            </p>
            <button
              onClick={() => triggerIngest("demo")}
              disabled={isControlsDisabled}
              className="w-full bg-accent text-accent-ink font-medium font-sans text-[15px] py-2.5 rounded-[10px] hover:opacity-90 disabled:opacity-50 transition-opacity flex justify-center items-center space-x-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink"
            >
              <Play size={16} />
              <span>Run Demo</span>
            </button>
          </div>

          {/* Full Run Card */}
          <div className={clsx("border rounded-lg p-6 transition-opacity", isControlsDisabled ? "opacity-50 border-surface bg-bg" : "border-surface bg-surface")}>
            <div className="flex items-center space-x-3 mb-2">
              <LayoutDashboard size={20} className="text-ink-muted" />
              <h3 className="text-[15px] font-sans font-semibold text-ink">Full pipeline run</h3>
            </div>
            <p className="text-[13px] font-sans text-ink-muted mb-6 h-10">
              Long-running background job. Processes all sources with state-based pagination.
            </p>
            <button
              onClick={() => triggerIngest("full")}
              disabled={isControlsDisabled}
              className="w-full bg-transparent border-2 border-ink text-ink font-medium font-sans text-[15px] py-2.5 rounded-[10px] hover:bg-surface disabled:opacity-50 transition-colors flex justify-center items-center space-x-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <Play size={16} />
              <span>Run Full Pipeline</span>
            </button>
          </div>
        </div>
      </div>

      {/* Live Progress & Terminal */}
      {(statusData.status !== "idle" || logs.length > 0) && (
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4">
          
          {/* Independent Progress Bar */}
          <div className="bg-surface border border-surface rounded-lg p-4 flex items-center space-x-4 shadow-sm">
            <div className="flex-1 h-2 bg-bg rounded-full relative overflow-hidden">
              <div 
                className={clsx(
                  "absolute top-0 left-0 h-full rounded-full transition-all duration-1000 ease-out",
                  statusData.status === "failed" ? "bg-negative" : statusData.status === "completed" ? "bg-positive" : "bg-accent"
                )}
                style={{ width: `${getProgressPercentage()}%` }}
              >
                {statusData.status === "running" && (
                  <div className="absolute inset-0 bg-[linear-gradient(45deg,rgba(255,255,255,0.15)_25%,transparent_25%,transparent_50%,rgba(255,255,255,0.15)_50%,rgba(255,255,255,0.15)_75%,transparent_75%,transparent)] bg-[length:1rem_1rem] animate-stripes" />
                )}
              </div>
            </div>
            <div className="font-mono text-[13px] font-semibold text-ink-muted w-12 text-right">
              {getProgressPercentage()}%
            </div>
          </div>

          {/* Terminal Window */}
          <div className="bg-[#121413] border border-surface rounded-xl overflow-hidden shadow-2xl">
            {/* Mac Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-[#1E211F] border-b border-white/5">
              <div className="flex space-x-2">
                <div className="w-3 h-3 rounded-full bg-[#FF5F56]"></div>
                <div className="w-3 h-3 rounded-full bg-[#FFBD2E]"></div>
                <div className="w-3 h-3 rounded-full bg-[#27C93F]"></div>
              </div>
              <div className="font-mono text-[11px] text-ink-muted">
                {statusData.status === "running" ? `${elapsed}s elapsed` : statusData.status === "completed" ? "Finished" : statusData.status === "idle" ? "Ready" : "Failed"}
              </div>
            </div>

          {/* Terminal Window */}
          <div className="p-4 h-[240px] overflow-y-auto font-mono text-[13px] text-[#A1A1AA] flex flex-col space-y-2">
            {logs.map((log, i) => (
              <div key={i} className="flex space-x-3">
                <span className="text-[#52525B] shrink-0">[{log.time}]</span>
                <span className={clsx(
                  log.text.includes("Error") ? "text-negative" : 
                  log.text.includes("completed") ? "text-positive" : 
                  "text-[#E4E4E7]"
                )}>{log.text}</span>
              </div>
            ))}
            {statusData.status === "running" && (
              <div className="flex space-x-3 text-[#E4E4E7]">
                <span className="text-[#52525B] shrink-0">[{new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span>
                <span className="flex items-center">
                  Processing<span className="animate-pulse ml-1 text-accent">_</span>
                </span>
              </div>
            )}
            <div ref={terminalEndRef} />
          </div>
        </div>
        </div>
      )}

      {completedToast && (
        <div className="bg-positive/10 border border-positive/20 rounded-lg p-4 flex items-center space-x-3 animate-in slide-in-from-bottom-2 fade-in">
          <CheckCircle2 size={18} className="text-positive" />
          <span className="font-mono text-[13px] text-positive">Pipeline completed successfully</span>
        </div>
      )}

      {/* Ingestion Summary Modal */}
      {showSummaryModal && runSummary.length > 0 && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-[#121413] border border-surface rounded-xl max-w-md w-full shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="p-6 border-b border-surface flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-full bg-positive/10 flex items-center justify-center text-positive">
                  <CheckCircle2 size={24} />
                </div>
                <div>
                  <h3 className="text-[18px] font-sans font-bold text-ink">Ingestion Complete</h3>
                  <p className="text-[13px] font-mono text-ink-muted">Processed {runSummary.length} sources</p>
                </div>
              </div>
              <button 
                onClick={() => setShowSummaryModal(false)}
                className="text-ink-muted hover:text-ink transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Stats Grid */}
            <div className="p-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-surface/50 border border-surface rounded-lg p-4">
                  <p className="text-[12px] font-sans text-ink-muted mb-1">Raw Ingested</p>
                  <p className="text-[24px] font-mono font-semibold text-ink">
                    {runSummary.reduce((sum, s) => sum + s.raw_ingested, 0).toLocaleString()}
                  </p>
                </div>
                <div className="bg-surface/50 border border-surface rounded-lg p-4">
                  <p className="text-[12px] font-sans text-ink-muted mb-1">Embedded</p>
                  <p className="text-[24px] font-mono font-semibold text-accent">
                    {runSummary.reduce((sum, s) => sum + s.relevant_embedded, 0).toLocaleString()}
                  </p>
                </div>
                <div className="bg-surface/50 border border-surface rounded-lg p-4">
                  <p className="text-[12px] font-sans text-ink-muted mb-1">Discarded</p>
                  <p className="text-[24px] font-mono font-semibold text-ink">
                    {runSummary.reduce((sum, s) => sum + s.irrelevant_discarded, 0).toLocaleString()}
                  </p>
                </div>
                <div className="bg-surface/50 border border-surface rounded-lg p-4">
                  <p className="text-[12px] font-sans text-ink-muted mb-1">Retention Rate</p>
                  <p className="text-[24px] font-mono font-semibold text-ink">
                    {runSummary.reduce((sum, s) => sum + s.raw_ingested, 0) > 0 
                      ? ((runSummary.reduce((sum, s) => sum + s.relevant_embedded, 0) / runSummary.reduce((sum, s) => sum + s.raw_ingested, 0)) * 100).toFixed(1)
                      : "0.0"}%
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="mt-6 flex space-x-3">
                <button 
                  onClick={() => setShowSummaryModal(false)}
                  className="flex-1 bg-surface text-ink px-4 py-2.5 rounded-lg font-sans font-medium text-[14px] hover:bg-surface/80 transition-colors"
                >
                  Dismiss
                </button>
                <a 
                  href="/pipeline"
                  className="flex-1 bg-accent text-accent-ink px-4 py-2.5 rounded-lg font-sans font-medium text-[14px] hover:opacity-90 transition-opacity flex items-center justify-center space-x-2"
                >
                  <BarChart2 size={16} />
                  <span>View Dashboard</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
