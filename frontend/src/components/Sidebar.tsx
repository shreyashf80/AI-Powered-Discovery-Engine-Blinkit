"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquare, LayoutDashboard, Settings, Moon, Sun } from "lucide-react";
import { clsx } from "clsx";
import { useEffect, useState } from "react";
import { useTheme } from "next-themes";

export function Sidebar() {
  const pathname = usePathname();
  const [status, setStatus] = useState<"idle" | "running" | "completed" | "failed">("idle");
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    // Poll /api/admin/ingest/status every 2.5s
    const poll = async () => {
      try {
        const res = await fetch("/api/admin/ingest/status");
        if (res.ok) {
          const data = await res.json();
          setStatus(data.status || "idle");
        }
      } catch (e) {
        // fail silently
      }
    };
    
    poll();
    const interval = setInterval(poll, 2500);
    return () => clearInterval(interval);
  }, []);

  const links = [
    { name: "Chat", href: "/", icon: MessageSquare },
    { name: "Pipeline", href: "/pipeline", icon: LayoutDashboard },
    { name: "Admin", href: "/admin", icon: Settings },
  ];

  return (
    <div className="w-full md:w-[220px] bg-bg border-b md:border-b-0 md:border-r border-surface h-auto md:h-screen flex flex-row md:flex-col fixed left-0 top-0 z-50 items-center md:items-stretch">
      <div className="p-4 md:border-b border-surface flex-shrink-0">
        <h1 className="font-sans font-semibold text-[18px] text-ink">Blinkit Echo</h1>
      </div>
      
      <nav className="flex-1 p-2 md:p-4 flex flex-row md:flex-col space-x-2 md:space-x-0 md:space-y-2 overflow-x-auto">
        {links.map((link) => {
          const isActive = pathname === link.href;
          const Icon = link.icon;
          
          return (
            <Link 
              key={link.name}
              href={link.href} 
              className={clsx(
                "flex items-center space-x-2 md:space-x-3 px-3 py-2 md:p-2 rounded-md text-[14px] md:text-[15px] font-sans transition-colors whitespace-nowrap",
                isActive 
                  ? "bg-accent text-accent-ink font-medium" 
                  : "hover:bg-surface text-ink"
              )}
            >
              <Icon size={18} className={isActive ? "text-accent-ink" : "text-ink-muted"} />
              <span>{link.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="flex-shrink-0 p-4 border-t border-surface">
        {mounted && (
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex items-center justify-between w-full p-2 rounded-md hover:bg-surface transition-colors cursor-pointer group"
            aria-label="Toggle theme"
          >
            <div className="flex items-center space-x-3">
              {theme === "dark" ? (
                <Moon size={18} className="text-accent" />
              ) : (
                <Sun size={18} className="text-ink-muted" />
              )}
              <span className="text-[14px] md:text-[15px] font-sans text-ink">
                {theme === "dark" ? "Dark Mode" : "Light Mode"}
              </span>
            </div>
            
            <div
              className={clsx(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-300",
                theme === "dark" ? "bg-accent" : "bg-ink-muted/50 group-hover:bg-ink-muted/70"
              )}
            >
              <span
                className={clsx(
                  "inline-block h-4 w-4 transform rounded-full bg-surface shadow-sm transition-transform duration-300",
                  theme === "dark" ? "translate-x-6" : "translate-x-1"
                )}
              />
            </div>
          </button>
        )}
      </div>

      <div className="hidden md:flex p-4 border-t border-surface items-center space-x-3 bg-surface/50 mt-auto">
        {status === "running" ? (
          <div className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#D4A017]"></span>
          </div>
        ) : (
          <div className={clsx(
            "w-2.5 h-2.5 rounded-full",
            status === "completed" ? "bg-positive" : status === "failed" ? "bg-negative" : "bg-ink-muted"
          )} />
        )}
        <span className="font-mono text-[13px] text-ink-muted">status: {status}</span>
      </div>
    </div>
  );
}
