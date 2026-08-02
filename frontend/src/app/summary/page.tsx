"use client";

import { useState, useEffect } from "react";
import { FileText, Loader2, Target, BarChart2, Lightbulb, DownloadCloud } from "lucide-react";
import ReactMarkdown from "react-markdown";

type SummaryItem = {
  question: string;
  answer: string;
  citations: Array<{ id: string; snippet: string; source: string }>;
  confidence: string;
  sample_size: number;
};

type InsightSummary = {
  summaries: SummaryItem[];
  source_funnel: Record<string, { raw: number; filtered: number; tagged: number; discarded: number }>;
  emergent_themes: string[];
  generated_at?: string;
};

export default function SummaryPage() {
  const [summary, setSummary] = useState<InsightSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState("");
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  useEffect(() => {
    const fetchCache = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/api/summary");
        if (res.ok) {
          const data = await res.json();
          setSummary(data);
        }
      } catch (err) {
        console.error("Failed to fetch cached report:", err);
      } finally {
        setIsInitialLoad(false);
      }
    };
    fetchCache();
  }, []);

  const handleGenerate = async () => {
    setIsLoading(true);
    setError("");
    try {
      // Call backend directly to bypass Next.js proxy timeout (~60s).
      // The summary endpoint can take 2-3 minutes on free-tier LLM APIs.
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5 * 60 * 1000); // 5 min

      const res = await fetch("http://127.0.0.1:8000/api/summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ questions: "all" }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      
      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`Backend error (${res.status}): ${errBody}`);
      }
      const data = await res.json();
      setSummary(data);
    } catch (err: any) {
      if (err.name === "AbortError") {
        setError("Request timed out after 5 minutes. Your LLM API quotas may be exhausted — try again later.");
      } else {
        setError(err.message);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadMarkdown = () => {
    if (!summary) return;

    let md = `# Insight Summary Report\n\n`;
    if (summary.generated_at) {
      md += `*Generated: ${new Date(summary.generated_at).toLocaleString()}*\n\n`;
    }

    if (summary.emergent_themes && summary.emergent_themes.length > 0) {
      md += `## Emergent Themes\n\n`;
      summary.emergent_themes.forEach(theme => {
        md += `- ${theme}\n`;
      });
      md += `\n`;
    }

    md += `## Core Research Answers\n\n`;
    summary.summaries.forEach(item => {
      md += `### ${item.question}\n\n`;
      md += `> **Confidence:** ${item.confidence.toUpperCase()}\n\n`;
      md += `${item.answer}\n\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Blinkit_Discovery_Report.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col min-h-screen max-w-4xl mx-auto py-12 px-6">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 mb-10 print:hidden">
        <div className="space-y-3">
          <h1 className="text-3xl font-sans font-semibold text-ink">Insight Summary Report</h1>
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
            <p className="text-ink-muted text-[15px]">A deep dive into 8 core product research questions based on real user feedback.</p>
            {summary?.generated_at && (
              <span className="text-[11px] font-mono bg-surface border border-surface px-2 py-1 rounded text-ink-muted whitespace-nowrap w-max">
                Last generated: {new Date(summary.generated_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          {summary && (
            <button
              onClick={handleDownloadMarkdown}
              className="flex items-center space-x-2 bg-transparent border-2 border-surface text-ink px-4 py-2 rounded-md font-medium text-[15px] hover:bg-surface transition-colors whitespace-nowrap"
            >
              <DownloadCloud size={16} />
              <span>Download Report</span>
            </button>
          )}
          <button
            onClick={handleGenerate}
            disabled={isLoading || isInitialLoad}
            className="flex items-center space-x-2 bg-accent text-accent-ink px-5 py-2.5 rounded-md font-medium text-[15px] shadow-sm hover:opacity-90 transition-opacity disabled:opacity-50 whitespace-nowrap"
          >
            {isLoading ? <Loader2 className="animate-spin" size={18} /> : <FileText size={18} />}
            <span>{isLoading ? "Generating (takes ~1 min)..." : summary ? "Regenerate Report" : "Generate Report"}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-md mb-8 print:hidden">
          {error}
        </div>
      )}

      {summary && (
        <div id="report-content" className="space-y-12">
          {/* Emergent Themes Spotlight */}
          {summary.emergent_themes && summary.emergent_themes.length > 0 && (
            <div className="bg-surface border-l-4 border-l-accent border-y-surface border-r-surface shadow-sm rounded-xl p-8 print:break-inside-avoid">
              <div className="flex items-center space-x-3 mb-6">
                <Lightbulb className="text-accent" size={24} />
                <h2 className="text-xl font-semibold text-ink">Emergent Themes</h2>
              </div>
              <p className="text-ink-muted text-sm mb-4">Themes detected by AI outside of our 8 core seed questions.</p>
              <ul className="space-y-3">
                {summary.emergent_themes.map((theme, i) => (
                  <li key={i} className="flex items-start space-x-3">
                    <span className="text-accent font-bold mt-0.5">•</span>
                    <span className="text-ink leading-relaxed">{theme}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Seed Questions */}
          <div>
            <div className="flex items-center space-x-3 mb-6 border-b border-surface pb-4">
              <Target className="text-ink-muted" size={24} />
              <h2 className="text-xl font-semibold text-ink">Core Research Answers</h2>
            </div>
            
            <div className="space-y-8">
              {summary.summaries.map((item, idx) => (
                <div key={idx} className="bg-surface border border-surface rounded-xl p-6 hover:shadow-sm transition-shadow print:break-inside-avoid">
                  <div className="flex justify-between items-start mb-4 gap-4">
                    <h3 className="text-lg font-medium text-ink leading-snug">{item.question}</h3>
                    <div className="flex flex-col items-end gap-1 shrink-0">
                      <span className={`text-[11px] font-mono uppercase px-2 py-1 rounded-sm border ${
                        item.confidence === 'High' ? 'text-positive border-positive' :
                        item.confidence === 'Medium' ? 'text-[#D4A017] border-[#D4A017]' :
                        'text-negative border-negative'
                      }`}>
                        {item.confidence} CONFIDENCE
                      </span>
                    </div>
                  </div>
                  
                  <div className="prose prose-sm prose-p:text-ink prose-p:leading-relaxed max-w-none">
                    <ReactMarkdown>{item.answer}</ReactMarkdown>
                  </div>
                </div>
              ))}
            </div>
          </div>


        </div>
      )}
    </div>
  );
}
