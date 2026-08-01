"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { clsx } from "clsx";

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

const SOURCE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  play_store: { bg: "bg-[var(--color-positive)]", text: "text-[var(--color-positive)]", border: "border-[var(--color-positive)]" },
  app_store: { bg: "bg-[#4A6FA5]", text: "text-[#4A6FA5]", border: "border-[#4A6FA5]" },
  reddit: { bg: "bg-[var(--color-negative)]", text: "text-[var(--color-negative)]", border: "border-[var(--color-negative)]" },
  youtube: { bg: "bg-[#B03A3A]", text: "text-[#B03A3A]", border: "border-[#B03A3A]" },
};

function getRelativeTime(dateString: string) {
  const d = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - d.getTime()) / 1000);
  
  if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  return `${Math.floor(diffInSeconds / 86400)}d ago`;
}

const ITEMS_PER_PAGE = 10;

export default function PipelinePage() {
  const [stats, setStats] = useState<PipelineStats[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    fetch("/api/stats")
      .then((res) => res.json())
      .then((data) => {
        // Sort descending by timestamp
        const sorted = data.sort((a: PipelineStats, b: PipelineStats) => 
          new Date(b.run_timestamp).getTime() - new Date(a.run_timestamp).getTime()
        );
        setStats(sorted);
      })
      .catch((err) => console.error(err))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <div className="w-full p-8 animate-pulse">
        <div className="h-8 w-48 bg-surface rounded mb-8" />
        <div className="grid grid-cols-4 gap-4 mb-12">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 bg-surface rounded-lg" />)}
        </div>
      </div>
    );
  }

  if (stats.length === 0) {
    return (
      <div className="w-full p-8">
        <h1 className="text-[24px] font-sans font-bold text-ink mb-4">Pipeline Dashboard</h1>
        <div className="border border-surface rounded-lg p-12 text-center bg-surface/30">
          <p className="text-[15px] font-sans text-ink-muted mb-4">
            No completed runs yet. Trigger one from Admin.
          </p>
          <Link href="/admin" className="inline-block bg-accent text-accent-ink px-4 py-2 rounded-md font-sans font-medium text-[15px] hover:opacity-90">
            Go to Admin
          </Link>
        </div>
      </div>
    );
  }

  const totalRaw = stats.reduce((sum, s) => sum + s.raw_ingested, 0);
  const totalEmbedded = stats.reduce((sum, s) => sum + s.relevant_embedded, 0);
  const retentionPct = totalRaw > 0 ? ((totalEmbedded / totalRaw) * 100).toFixed(1) : "0.0";
  const lastRunTime = stats.length > 0 ? getRelativeTime(stats[0].run_timestamp) : "N/A";

  // Group by source for funnel bars
  const sources = Array.from(new Set(stats.map((s) => s.source)));
  const sourceAggregates = sources.map((source) => {
    const sourceStats = stats.filter((s) => s.source === source);
    return {
      source,
      raw: sourceStats.reduce((sum, s) => sum + s.raw_ingested, 0),
      stg1: sourceStats.reduce((sum, s) => sum + s.stage1_passed, 0),
      stg2: sourceStats.reduce((sum, s) => sum + s.stage2_tagged, 0),
      embedded: sourceStats.reduce((sum, s) => sum + s.relevant_embedded, 0),
      discarded: sourceStats.reduce((sum, s) => sum + s.irrelevant_discarded, 0),
    };
  });

  return (
    <div className="w-full p-8 max-w-[1200px] mx-auto pb-24">
      <h1 className="text-[24px] font-sans font-bold text-ink mb-8">Pipeline Dashboard</h1>

      {/* Top 4 Summary Tiles */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-12">
        <div className="bg-surface border border-surface rounded-lg p-5 flex flex-col justify-between h-[100px]">
          <span className="text-[13px] font-sans text-ink-muted">Total raw ingested</span>
          <span className="text-[24px] font-mono text-ink">{totalRaw.toLocaleString()}</span>
        </div>
        <div className="bg-surface border border-surface rounded-lg p-5 flex flex-col justify-between h-[100px]">
          <span className="text-[13px] font-sans text-ink-muted">Total embedded</span>
          <span className="text-[24px] font-mono text-ink">{totalEmbedded.toLocaleString()}</span>
        </div>
        <div className="bg-surface border border-surface rounded-lg p-5 flex flex-col justify-between h-[100px]">
          <span className="text-[13px] font-sans text-ink-muted">Overall retention</span>
          <span className="text-[24px] font-mono text-ink">{retentionPct}%</span>
        </div>
        <div className="bg-surface border border-surface rounded-lg p-5 flex flex-col justify-between h-[100px]">
          <span className="text-[13px] font-sans text-ink-muted">Last run</span>
          <span className="text-[24px] font-mono text-ink">{lastRunTime}</span>
        </div>
      </div>

      {/* Funnel Attrition Bars */}
      <div className="mb-16">
        <h2 className="text-[18px] font-sans font-semibold text-ink mb-6">Source Attrition</h2>
        <div className="space-y-10">
          {sourceAggregates.map((agg) => {
            const raw = Math.max(agg.raw, 1); // prevent division by zero
            const embeddedPct = (agg.embedded / raw) * 100;
            const stg2DropPct = ((agg.stg2 - agg.embedded) / raw) * 100;
            const stg1DropPct = ((agg.stg1 - agg.stg2) / raw) * 100;
            const rawDropPct = ((agg.raw - agg.stg1) / raw) * 100;

            const colors = SOURCE_COLORS[agg.source] || { bg: "bg-surface", text: "text-ink" };
            const badgeBg = colors.bg.replace("]", "]/10");

            return (
              <div key={agg.source} className="flex flex-col space-y-3">
                <div className="flex items-center space-x-2">
                  <span className={clsx("inline-flex items-center px-2 py-0.5 rounded font-mono text-[13px] border", badgeBg, colors.text, colors.border.replace("]", "]/20"))}>
                    {agg.source}
                  </span>
                </div>
                
                {/* Horizontal Segmented Bar */}
                <div className="h-6 w-full flex rounded overflow-hidden bg-surface border border-surface shadow-inner">
                  {agg.embedded > 0 && (
                    <div className={clsx("h-full transition-all duration-500 border-r border-bg/20", colors.bg)} style={{ width: `${(agg.embedded / raw) * 100}%` }} title="Relevant Embedded" />
                  )}
                  {(agg.stg2 - agg.embedded) > 0 && (
                    <div className={clsx("h-full transition-all duration-500 opacity-70 border-r border-bg/20", colors.bg)} style={{ width: `${((agg.stg2 - agg.embedded) / raw) * 100}%` }} title="Dropped at Embed (Passed Stage 2)" />
                  )}
                  {(agg.stg1 - agg.stg2) > 0 && (
                    <div className={clsx("h-full transition-all duration-500 opacity-40 border-r border-bg/20", colors.bg)} style={{ width: `${((agg.stg1 - agg.stg2) / raw) * 100}%` }} title="Dropped at Stage 2 (Passed Stage 1)" />
                  )}
                  {(agg.raw - agg.stg1) > 0 && (
                    <div className={clsx("h-full transition-all duration-500 opacity-[0.15]", colors.bg)} style={{ width: `${((agg.raw - agg.stg1) / raw) * 100}%` }} title="Irrelevant Discarded (Failed Stage 1)" />
                  )}
                </div>

                {/* Mono Labels Underneath */}
                <div className="flex text-[11px] font-mono text-ink-muted justify-between px-1">
                  <span>raw: {agg.raw.toLocaleString()}</span>
                  <span>stg1: {agg.stg1.toLocaleString()}</span>
                  <span>stg2: {agg.stg2.toLocaleString()}</span>
                  <span className={clsx("font-semibold", colors.text)}>embedded: {agg.embedded.toLocaleString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Individual Runs Table */}
      <div>
        <h2 className="text-[18px] font-sans font-semibold text-ink mb-6">Run History</h2>
        
        {/* Calculate pagination data */}
        {(() => {
          const totalPages = Math.ceil(stats.length / ITEMS_PER_PAGE);
          const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
          const paginatedStats = stats.slice(startIndex, startIndex + ITEMS_PER_PAGE);
          
          return (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-surface text-[13px] font-mono text-ink-muted">
                <th className="py-3 px-2 font-normal">Timestamp</th>
                <th className="py-3 px-2 font-normal">Source</th>
                <th className="py-3 px-2 font-normal text-right">Raw</th>
                <th className="py-3 px-2 font-normal text-right">Stage 1</th>
                <th className="py-3 px-2 font-normal text-right">Stage 2</th>
                <th className="py-3 px-2 font-normal text-right">Embedded</th>
                <th className="py-3 px-2 font-normal text-right">Discarded</th>
              </tr>
            </thead>
            <tbody className="font-mono text-[13px] text-ink">
              {paginatedStats.map((run, idx) => {
                const colors = SOURCE_COLORS[run.source] || { text: "text-ink" };
                return (
                  <tr key={`${run.run_id}-${run.source}-${idx}`} className="border-b border-surface/50 hover:bg-surface/30 transition-colors">
                    <td className="py-3 px-2 whitespace-nowrap text-ink-muted">
                      {new Date(run.run_timestamp).toLocaleString(undefined, { 
                        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                      })}
                    </td>
                    <td className={clsx("py-3 px-2", colors.text)}>{run.source}</td>
                    <td className="py-3 px-2 text-right">{run.raw_ingested.toLocaleString()}</td>
                    <td className="py-3 px-2 text-right">{run.stage1_passed.toLocaleString()}</td>
                    <td className="py-3 px-2 text-right">{run.stage2_tagged.toLocaleString()}</td>
                    <td className="py-3 px-2 text-right">{run.relevant_embedded.toLocaleString()}</td>
                    <td className="py-3 px-2 text-right text-ink-muted">{run.irrelevant_discarded.toLocaleString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex justify-between items-center mt-6">
            <button
              onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
              className="px-4 py-2 border border-surface rounded-md text-[13px] font-sans text-ink disabled:opacity-50 hover:bg-surface/30 transition-colors"
            >
              Previous
            </button>
            <span className="text-[13px] font-mono text-ink-muted">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
              className="px-4 py-2 border border-surface rounded-md text-[13px] font-sans text-ink disabled:opacity-50 hover:bg-surface/30 transition-colors"
            >
              Next
            </button>
          </div>
        )}
        </>
      );
      })()}
      </div>
    </div>
  );
}
