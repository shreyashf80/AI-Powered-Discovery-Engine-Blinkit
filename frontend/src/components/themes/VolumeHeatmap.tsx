import React, { useState } from "react";

export function VolumeHeatmap({ themes }: { themes: any[] }) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (!themes || themes.length === 0) return null;

  const totalVolume = themes.reduce((acc, t) => acc + t.volume, 0);

  // Modern colors matching the app aesthetic
  const colors = [
    "bg-[#3B82F6]", // Blue
    "bg-[#10B981]", // Emerald
    "bg-[#F59E0B]", // Amber
    "bg-[#EF4444]", // Red
    "bg-[#8B5CF6]", // Purple
    "bg-[#EC4899]", // Pink
    "bg-[#6366F1]", // Indigo
    "bg-[#14B8A6]", // Teal
  ];

  return (
    <div className="w-full bg-bg border border-surface rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[15px] font-sans font-semibold text-ink">Volume Distribution Heatmap</h2>
        <span className="text-[13px] font-mono text-ink-muted bg-surface/50 px-2 py-0.5 rounded-full">
          Total: {totalVolume} Reviews
        </span>
      </div>

      {/* The Stacked Bar */}
      <div className="w-full h-8 rounded-full overflow-hidden flex bg-surface border border-surface/50 shadow-inner">
        {themes.map((theme, i) => {
          const width = (theme.volume / totalVolume) * 100;
          const color = colors[i % colors.length];
          const isHovered = hoveredIndex === i;

          return (
            <div
              key={i}
              className={`${color} h-full transition-all duration-300 ease-in-out cursor-pointer relative group flex items-center justify-center`}
              style={{
                width: `${width}%`,
                opacity: hoveredIndex !== null && hoveredIndex !== i ? 0.3 : 1,
              }}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            />
          );
        })}
      </div>

      {/* Hover Legend / Details */}
      <div className="mt-6 min-h-[40px] flex items-center justify-center">
        {hoveredIndex !== null ? (
          <div className="flex items-center space-x-3 animate-in fade-in slide-in-from-bottom-1 duration-200">
            <div className={`w-3 h-3 rounded-full ${colors[hoveredIndex % colors.length]}`} />
            <span className="text-[14px] font-sans font-medium text-ink">
              {themes[hoveredIndex].theme_name}
            </span>
            <span className="text-[14px] font-mono text-ink-muted">
              ({themes[hoveredIndex].volume} reviews / {((themes[hoveredIndex].volume / totalVolume) * 100).toFixed(1)}%)
            </span>
          </div>
        ) : (
          <div className="text-[13px] font-sans text-ink-muted/60 italic">
            Hover over the segments to view cluster details
          </div>
        )}
      </div>
    </div>
  );
}
