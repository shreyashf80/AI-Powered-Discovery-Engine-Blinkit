"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronUp, Quote, Apple, Play, MessageCircle, Video, Info } from "lucide-react";

export function ThemeCard({ theme, index }: { theme: any; index: number }) {
  const [expanded, setExpanded] = useState(false);

  // Sentiment Bar calculations
  const totalSentiment = 
    (theme.sentiment_split.positive || 0) + 
    (theme.sentiment_split.neutral || 0) + 
    (theme.sentiment_split.negative || 0);

  const posPct = ((theme.sentiment_split.positive || 0) / totalSentiment) * 100;
  const neuPct = ((theme.sentiment_split.neutral || 0) / totalSentiment) * 100;
  const negPct = ((theme.sentiment_split.negative || 0) / totalSentiment) * 100;

  const getSourceIcon = (source: string) => {
    switch (source.toLowerCase()) {
      case "app_store": return <Apple size={14} className="text-ink" />;
      case "play_store": return <Play size={14} className="text-[#10B981]" />;
      case "reddit": return <MessageCircle size={14} className="text-[#FF4500]" />;
      case "youtube": return <Video size={14} className="text-[#FF0000]" />;
      default: return <Info size={14} className="text-ink-muted" />;
    }
  };

  const formatSourceName = (source: string) => {
    return source.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };

  return (
    <div className="bg-bg border border-surface rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow group">
      <div className="p-6 md:p-8">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-3">
              <span className="text-[11px] font-mono font-semibold bg-ink text-bg px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                Theme {index + 1}
              </span>
              <span className="text-[13px] font-mono text-ink-muted bg-surface/50 px-2 py-0.5 rounded-md">
                {theme.volume} feedback items
              </span>
            </div>
            <h3 className="text-[22px] md:text-[24px] font-sans font-bold text-ink mb-2 tracking-tight">
              {theme.theme_name}
            </h3>
            <p className="text-[15px] font-sans text-ink-muted leading-relaxed max-w-[800px]">
              {theme.theme_description}
            </p>
          </div>
        </div>

        {/* Analytics Dashboard */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6 bg-surface/30 p-5 rounded-lg border border-surface/50">
          
          {/* Sentiment Progress Bar */}
          <div>
            <div className="flex justify-between items-end mb-3">
              <h4 className="text-[13px] font-sans font-semibold text-ink">Sentiment Distribution</h4>
            </div>
            
            <div className="w-full h-3 rounded-full flex overflow-hidden bg-surface border border-surface shadow-inner">
              <div style={{ width: `${posPct}%` }} className="bg-[#10B981] h-full transition-all duration-500" title={`Positive: ${posPct.toFixed(1)}%`} />
              <div style={{ width: `${neuPct}%` }} className="bg-[#9CA3AF] h-full transition-all duration-500" title={`Neutral: ${neuPct.toFixed(1)}%`} />
              <div style={{ width: `${negPct}%` }} className="bg-[#EF4444] h-full transition-all duration-500" title={`Negative: ${negPct.toFixed(1)}%`} />
            </div>
            
            <div className="flex justify-between mt-2 text-[12px] font-mono">
              <span className="text-[#10B981] font-medium">{posPct.toFixed(0)}% Pos</span>
              <span className="text-[#9CA3AF] font-medium">{neuPct.toFixed(0)}% Neu</span>
              <span className="text-[#EF4444] font-medium">{negPct.toFixed(0)}% Neg</span>
            </div>
          </div>

          {/* Source Breakdown Icons */}
          <div>
            <h4 className="text-[13px] font-sans font-semibold text-ink mb-3">Feedback Sources</h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(theme.source_split)
                .sort((a: any, b: any) => b[1] - a[1]) // highest % first
                .filter(([_, val]) => (val as number) > 0)
                .map(([key, val]) => (
                  <div key={key} className="flex items-center space-x-1.5 bg-bg border border-surface/80 px-2.5 py-1.5 rounded-md shadow-sm">
                    {getSourceIcon(key)}
                    <span className="text-[13px] font-sans text-ink font-medium pr-1">{formatSourceName(key)}</span>
                    <span className="text-[12px] font-mono text-ink-muted">{(val as number).toFixed(0)}%</span>
                  </div>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* Accordion Toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-4 bg-surface/20 border-t flex items-center justify-center text-[13px] font-sans font-medium text-ink hover:bg-surface/50 transition-colors group-hover:border-ink/10"
      >
        <span className="flex items-center">
          {expanded ? "Hide Representative Evidence" : "View Representative Evidence"}
        </span>
        {expanded ? <ChevronUp size={16} className="ml-2 text-ink-muted" /> : <ChevronDown size={16} className="ml-2 text-ink-muted" />}
      </button>

      {/* Expanded Evidence */}
      {expanded && (
        <div className="bg-bg p-6 md:p-8 border-t">
          <p className="text-[13px] font-sans text-ink-muted mb-6 flex items-center">
            <Info size={14} className="mr-2 opacity-60" />
            Showing the Top 5 most mathematically representative snippets from the center of this cluster.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {theme.evidence.map((ev: any, idx: number) => (
              <div key={idx} className="flex flex-col justify-between p-5 bg-surface/30 border border-surface/50 rounded-xl hover:border-surface transition-colors">
                <div className="flex items-start space-x-3 mb-4">
                  <Quote size={18} className="text-ink/20 flex-shrink-0 mt-0.5" />
                  <p className="text-[14px] font-sans text-ink leading-relaxed italic">
                    &quot;{ev.text}&quot;
                  </p>
                </div>
                <div className="flex items-center self-end space-x-1.5 bg-bg border px-2 py-1 rounded-md opacity-80">
                  {getSourceIcon(ev.source)}
                  <span className="text-[11px] font-mono text-ink-muted uppercase tracking-wider">{formatSourceName(ev.source)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
