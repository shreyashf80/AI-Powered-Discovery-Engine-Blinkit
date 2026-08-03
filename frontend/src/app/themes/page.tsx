"use client";

import { useEffect, useState } from "react";
import { ThemeCard } from "@/components/themes/ThemeCard";
import { VolumeHeatmap } from "@/components/themes/VolumeHeatmap";
import { Database, AlertCircle } from "lucide-react";

export default function ThemesPage() {
  const [themes, setThemes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchThemes = () => {
    setLoading(true);
    fetch("/api/themes")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch themes");
        return res.json();
      })
      .then((data) => {
        setThemes(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to load discovery themes. Make sure the backend is running and the full pipeline has been executed.");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchThemes();
  }, []);

  const handleRegenerate = async () => {
    const token = window.prompt("Enter Admin Secret Token to regenerate themes:");
    if (!token) return;

    setIsRegenerating(true);
    setError(null);
    try {
      const res = await fetch("/api/themes/generate", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to regenerate themes");
      
      // Re-fetch the new themes!
      fetchThemes();
    } catch (e: any) {
      console.error(e);
      window.alert(`Error: ${e.message}`);
    } finally {
      setIsRegenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-4 border-ink/20 border-t-ink rounded-full animate-spin mb-4" />
        <p className="text-ink-muted font-mono text-[14px]">Loading ML Clusters...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-[860px] mx-auto p-8 mt-12 flex flex-col items-center text-center">
        <AlertCircle size={48} className="text-red-500 mb-4" />
        <h2 className="text-[20px] font-sans font-bold text-ink mb-2">Error Loading Themes</h2>
        <p className="text-[15px] font-sans text-ink-muted">{error}</p>
      </div>
    );
  }

  if (!themes || themes.length === 0) {
    return (
      <div className="max-w-[860px] mx-auto p-8 mt-12 flex flex-col items-center text-center">
        <Database size={48} className="text-ink-muted mb-4 opacity-50" />
        <h2 className="text-[20px] font-sans font-bold text-ink mb-2">No Themes Found</h2>
        <p className="text-[15px] font-sans text-ink-muted max-w-[400px]">
          There are no machine learning clusters generated yet. Go to the Admin Console and run the Full Pipeline to generate them.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[1000px] mx-auto p-8 space-y-12 pb-24">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-3">
          <h1 className="text-[32px] font-sans font-bold text-ink tracking-tight leading-none">
            Discovery Themes
          </h1>
          <p className="text-[16px] font-sans text-ink-muted max-w-[600px] leading-relaxed">
            AI-generated clusters built using K-Means unsupervised machine learning on 384-dimensional embeddings.
          </p>
        </div>
        
        <button 
          onClick={handleRegenerate}
          disabled={isRegenerating}
          className="flex items-center space-x-2 bg-ink text-bg px-4 py-2.5 rounded-lg text-[14px] font-sans font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          <Database size={16} className={isRegenerating ? "animate-pulse" : ""} />
          <span>{isRegenerating ? "Generating Themes..." : "Regenerate Themes"}</span>
        </button>
      </div>

      {/* Volume Heatmap Visualization */}
      <div>
        <VolumeHeatmap themes={themes} />
      </div>

      {/* Theme Cards Grid */}
      <div className="grid grid-cols-1 gap-6">
        {themes.map((theme, i) => (
          <ThemeCard key={i} theme={theme} index={i} />
        ))}
      </div>

    </div>
  );
}
