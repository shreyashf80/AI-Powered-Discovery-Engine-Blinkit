"use client";

import { useState, useEffect, useRef } from "react";
import { Send, RefreshCw } from "lucide-react";
import { clsx } from "clsx";
import ReactMarkdown from "react-markdown";

type Citation = {
  id: string;
  snippet: string;
  source: string;
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  source_breakdown?: Record<string, number>;
  llm_used?: string;
  isError?: boolean;
  errorMessage?: string;
  isLoading?: boolean;
};

const EXAMPLE_QUESTIONS = [
  "What stops users from trying a new category on Blinkit?",
  "Why do users keep reordering from the same categories?",
  "What information do users need before trying something new on Blinkit?",
];

const SOURCE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  play_store: { bg: "bg-[var(--color-positive)]/10", text: "text-[var(--color-positive)]", border: "border-[var(--color-positive)]/20" },
  app_store: { bg: "bg-[#4A6FA5]/10", text: "text-[#4A6FA5]", border: "border-[#4A6FA5]/20" },
  reddit: { bg: "bg-[var(--color-negative)]/10", text: "text-[var(--color-negative)]", border: "border-[var(--color-negative)]/20" },
  youtube: { bg: "bg-[#B03A3A]/10", text: "text-[#B03A3A]", border: "border-[#B03A3A]/20" },
};

function SourceBadge({ source, count }: { source: string; count?: number }) {
  const colors = SOURCE_COLORS[source] || { bg: "bg-surface", text: "text-ink", border: "border-surface" };
  return (
    <span className={clsx("inline-flex items-center px-2 py-0.5 rounded font-mono text-[13px] border", colors.bg, colors.text, colors.border)}>
      {source} {count !== undefined && <span className="ml-1 opacity-80">{count}</span>}
    </span>
  );
}

function LoadingSkeleton() {
  const [phase, setPhase] = useState("Retrieving evidence...");

  useEffect(() => {
    const timer = setTimeout(() => {
      setPhase("Synthesizing answer...");
    }, 3000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="flex flex-col space-y-4 py-4 animate-pulse">
      <div className="flex items-center space-x-3">
        <div className="w-4 h-4 rounded-full bg-accent animate-bounce" />
        <span className="font-mono text-[13px] text-ink-muted">{phase}</span>
      </div>
      <div className="space-y-2">
        <div className="h-4 bg-surface rounded w-3/4" />
        <div className="h-4 bg-surface rounded w-full" />
        <div className="h-4 bg-surface rounded w-5/6" />
      </div>
    </div>
  );
}

function AssistantMessage({ msg, onRetry }: { msg: Message, onRetry: () => void }) {
  const [visibleCount, setVisibleCount] = useState(4);

  return (
    <div className="flex flex-col space-y-6">
      {msg.isLoading ? (
        <LoadingSkeleton />
      ) : msg.isError ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 max-w-fit">
          <p className="text-[15px] text-red-800 mb-3">{msg.errorMessage}</p>
          <button
            onClick={onRetry}
            className="flex items-center space-x-2 text-[13px] font-mono bg-white border border-red-200 text-red-700 px-3 py-1.5 rounded hover:bg-red-50 transition-colors"
          >
            <RefreshCw size={14} />
            <span>Retry</span>
          </button>
        </div>
      ) : (
        <>
          <div className="text-[15px] text-ink leading-relaxed space-y-4">
            <ReactMarkdown
              urlTransform={(value) => value}
              components={{
                p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
                a: ({ node, children, href, ...rest }) => {
                  if (!href) return <a href={href} {...rest}>{children}</a>;
                  
                  const isCitation = /^(play_store|app_store|reddit|youtube):/.test(href);
                  if (!isCitation) {
                    return <a href={href} className="text-accent underline hover:opacity-80" {...rest}>{children}</a>;
                  }

                  const rawId = href.replace(/^(?:play_store|app_store|reddit|youtube):/, '');
                  const citationIndex = msg.citations?.findIndex(c => c.id === rawId || c.id === href);
                  const displayNum = citationIndex !== undefined && citationIndex >= 0 ? citationIndex + 1 : '*';

                  return (
                    <span 
                      className="group relative inline-flex items-center cursor-help mx-0.5"
                      title={`Source: ${href.split(':')[0] || 'Unknown'}`}
                    >
                      <sup className="text-[10px] font-mono text-accent-ink bg-accent w-[16px] h-[16px] rounded-full inline-flex items-center justify-center relative -top-1 font-medium shadow-sm">
                        {displayNum}
                      </sup>
                    </span>
                  );
                }
              }}
            >
              {msg.content.replace(
                /\[([^\]]+)\]\(((?:play_store|app_store|reddit|youtube):[a-zA-Z0-9\-:/_]+)\)|\[((?:play_store|app_store|reddit|youtube):[a-zA-Z0-9\-:/_]+)\]|((?:play_store|app_store|reddit|youtube):[a-zA-Z0-9\-:/_]+)/g,
                (match, mdText, mdId, bracketId, bareId) => {
                  if (mdText && mdId) return `${mdText} [ ](${mdId})`;
                  if (bracketId) return `[ ](${bracketId})`;
                  if (bareId) return `[ ](${bareId})`;
                  return match;
                }
              )}
            </ReactMarkdown>
          </div>

          {/* Evidence Section */}
          {((msg.citations && msg.citations.length > 0) || msg.source_breakdown) && (
            <div className="border-t border-surface pt-6 space-y-4 mt-6">
              <div className="flex items-center space-x-3">
                <h3 className="text-[13px] font-mono text-ink uppercase tracking-wider">Evidence</h3>
                <div className="h-px bg-surface flex-1" />
              </div>

              {/* Source Breakdown Badges */}
              {msg.source_breakdown && (
                <div className="flex flex-wrap gap-2">
                  {Object.entries(msg.source_breakdown).map(([source, count]) => (
                    <SourceBadge key={source} source={source} count={count as number} />
                  ))}
                </div>
              )}

              {/* Evidence Receipts */}
              {msg.citations && msg.citations.length > 0 && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                    {msg.citations.slice(0, visibleCount).map((cit, idx) => (
                      <div
                        key={idx}
                        className="bg-surface rounded-[10px] p-4 border-t-2 border-dashed border-t-surface transition-colors flex flex-col"
                      >
                        <div className="mb-3 flex justify-between items-start">
                          <SourceBadge source={cit.source} />
                          <span className="text-[10px] font-mono text-ink-muted bg-bg px-1.5 py-0.5 rounded border border-surface">
                            {idx + 1}
                          </span>
                        </div>
                        <p className="text-[13px] font-mono text-ink-muted leading-relaxed flex-1 mb-4 italic">
                          &quot;{cit.snippet}&quot;
                        </p>
                        <p className="text-[11px] font-mono text-ink-muted opacity-70 mt-auto truncate" title={cit.id}>
                          id: {cit.id}
                        </p>
                      </div>
                    ))}
                  </div>
                  
                  {msg.citations.length > 4 && (
                    <div className="pt-2 flex justify-center">
                      <button
                        onClick={() => setVisibleCount(visibleCount === 4 ? msg.citations!.length : 4)}
                        className="text-[13px] font-mono text-ink-muted hover:text-ink transition-colors border border-[#E7E5DE] px-4 py-2 rounded-full hover:bg-surface transition-all"
                      >
                        {visibleCount === 4 ? `View ${msg.citations.length - 4} more citations` : "View less"}
                      </button>
                    </div>
                  )}
                </>
              )}

              {msg.llm_used && (
                <div className="pt-4 text-right">
                  <span className="text-[11px] font-mono text-ink-muted">
                    synthesized by {msg.llm_used}
                  </span>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (question: string) => {
    if (!question.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: question.trim(),
    };

    const assistantId = (Date.now() + 1).toString();
    const loadingMessage: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setInput("");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim() }),
      });

      if (!res.ok) {
        throw new Error("The engine hit a rate limit. Try again in a moment.");
      }

      const data = await res.json();

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? {
              ...msg,
              isLoading: false,
              content: data.answer,
              citations: data.citations,
              source_breakdown: data.source_breakdown,
              llm_used: data.llm_used,
            }
            : msg
        )
      );
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? {
              ...msg,
              isLoading: false,
              isError: true,
              errorMessage: err.message || "An error occurred.",
            }
            : msg
        )
      );
    }
  };

  const isInputDisabled = !input.trim();
  const isCurrentlyLoading = messages.some((m) => m.isLoading);

  return (
    <div className="flex flex-col h-screen max-w-[860px] mx-auto relative">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-8 pb-32">
        {messages.length === 0 ? (
          <div className="flex flex-col justify-center h-full max-w-3xl mx-auto space-y-10">
            <div className="space-y-4 px-1">
              <h1 className="text-[24px] font-sans font-medium text-ink">
                Blinkit Echo
              </h1>
              <div className="bg-accent/10 border-l-4 border-accent p-5 rounded-r-[10px]">
                <h2 className="text-[13px] font-mono font-bold text-ink uppercase tracking-wider mb-2">
                  Objective
                </h2>
                <p className="text-[15px] font-sans text-ink leading-relaxed">
                  Understand how Blinkit customers actually think — why they keep reordering the same categories, what stops them from trying new ones, and what would change their mind. Every answer here is grounded in real App Store, Play Store, and Reddit discussions, not assumptions.
                </p>
                <div className="mt-4 text-[12px] font-mono text-ink-muted flex items-center space-x-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-accent" />
                  <span>
                    Backed by real reviews and discussions across Play Store, App Store, Reddit, Youtube.
                  </span>
                </div>
              </div>
            </div>
            <div className="space-y-4">
              <p className="text-[12px] font-mono text-ink-muted uppercase tracking-widest px-1">
                TRY ASKING
              </p>
              <div className="space-y-2">
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSubmit(q)}
                    disabled={isCurrentlyLoading}
                    className="block text-left w-full px-4 py-3 rounded-[10px] border border-[#E7E5DE] bg-transparent hover:bg-accent/10 hover:border-accent transition-colors text-[15px] text-ink-muted hover:text-ink disabled:opacity-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-12">
            {messages.map((msg, index) => {
              if (msg.role === "user") {
                return (
                  <div key={msg.id} className="flex justify-end">
                    <div className="bg-surface border border-surface rounded-[10px] rounded-tr-sm px-5 py-3 max-w-[80%]">
                      <p className="text-[15px] font-sans text-ink whitespace-pre-wrap leading-relaxed">
                        {msg.content}
                      </p>
                    </div>
                  </div>
                );
              }

              return (
                <AssistantMessage 
                  key={msg.id} 
                  msg={msg} 
                  onRetry={() => handleSubmit(messages[index - 1].content)} 
                />
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="absolute bottom-0 left-0 right-0 p-6 bg-bg">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit(input);
          }}
          className="relative max-w-3xl mx-auto"
        >
          <textarea
            value={input}
            maxLength={500}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(input);
              }
            }}
            placeholder="Ask about your customers. e.g. What prevents users from exploring new categories?"
            className="w-full bg-surface border border-[#E7E5DE] rounded-[10px] pl-6 pr-14 py-4 text-[15px] text-ink placeholder:text-ink-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:border-transparent resize-none"
            rows={1}
            style={{ minHeight: "56px", maxHeight: "120px" }}
          />
          <button
            type="submit"
            disabled={isInputDisabled || isCurrentlyLoading}
            className={clsx(
              "absolute right-3 top-2.5 p-2 rounded-full transition-all flex items-center justify-center",
              isInputDisabled || isCurrentlyLoading
                ? "bg-transparent text-ink-muted"
                : "bg-accent text-accent-ink hover:opacity-90"
            )}
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
