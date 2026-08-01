"use client";

import { useState, useEffect, useRef } from "react";
import { Send, RefreshCw, ChevronUp, ChevronDown, Sparkles, Plus, Quote } from "lucide-react";
import { clsx } from "clsx";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Citation = {
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

const ADDITIONAL_QUESTIONS = [
  "How do users discover products today?",
  "What role do habits play in shopping behavior?",
  "What frustrations emerge repeatedly?",
  "Which user segments are more likely to experiment?",
  "What unmet needs emerge consistently across discussions?"
];



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

const SOURCE_LABELS: Record<string, string> = {
  app_store: "App Store",
  play_store: "Play Store",
  reddit: "Reddit",
  youtube: "YouTube",
};

function AssistantMessage({ msg, onRetry }: { msg: Message, onRetry: () => void }) {
  const [showEvidence, setShowEvidence] = useState(false);
  const hasCitations = msg.citations && msg.citations.length > 0;

  return (
    <div className="flex flex-col space-y-4 w-full">
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
          <div className="prose prose-sm dark:prose-invert max-w-none break-words leading-relaxed prose-p:my-3 prose-headings:mb-3 prose-headings:mt-6 prose-li:my-0.5">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {msg.content}
            </ReactMarkdown>
          </div>

          {/* Evidence Section */}
          {hasCitations && (
            <div className="mt-2">
              <button
                onClick={() => setShowEvidence(!showEvidence)}
                className="flex items-center space-x-2 text-[12px] font-mono text-ink-muted hover:text-ink transition-colors"
              >
                <Quote size={12} />
                <span>Evidence ({msg.citations!.length} sources)</span>
                {showEvidence ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>

              {showEvidence && (
                <div className="mt-3 space-y-2.5 border-l-2 border-accent/30 pl-4">
                  {msg.citations!.map((c, i) => (
                    <div key={i} className="text-[13px] break-words">
                      <p className="text-ink-muted italic leading-relaxed">&ldquo;{c.snippet}&rdquo;</p>
                      <span className="text-[11px] font-mono text-accent">
                        — {SOURCE_LABELS[c.source] || c.source}
                      </span>
                    </div>
                  ))}
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
  const [isHydrated, setIsHydrated] = useState(false);
  const [showQuestions, setShowQuestions] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowQuestions(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Hydrate from sessionStorage on mount
  useEffect(() => {
    const savedMessages = sessionStorage.getItem("chatMessages");
    const savedInput = sessionStorage.getItem("chatInput");
    
    if (savedMessages) {
      try {
        setMessages(JSON.parse(savedMessages));
      } catch (e) {
        console.error("Failed to parse saved chat messages", e);
      }
    }
    
    if (savedInput) {
      setInput(savedInput);
    }
    
    setIsHydrated(true);
  }, []);

  // Save to sessionStorage when changed
  useEffect(() => {
    if (isHydrated) {
      sessionStorage.setItem("chatMessages", JSON.stringify(messages));
    }
  }, [messages, isHydrated]);

  useEffect(() => {
    if (isHydrated) {
      sessionStorage.setItem("chatInput", input);
    }
  }, [input, isHydrated]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleNewChat = () => {
    setMessages([]);
    setInput("");
  };

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

  const dropdownQuestions = messages.length === 0 
    ? ADDITIONAL_QUESTIONS 
    : [...EXAMPLE_QUESTIONS, ...ADDITIONAL_QUESTIONS].filter(
        q => !messages.some(m => m.role === "user" && m.content === q)
      );

  return (
    <div className="flex flex-col h-screen max-w-[860px] mx-auto relative">
      {/* Header Area for New Chat */}
      {messages.length > 0 && (
        <div className="flex justify-end px-8 pt-4 pb-0 z-10">
          <button
            onClick={handleNewChat}
            className="flex items-center space-x-2 text-[13px] font-sans font-medium bg-surface border border-[#E7E5DE] text-ink px-3 py-1.5 rounded-full hover:bg-surface/70 transition-colors shadow-sm"
          >
            <Plus size={14} />
            <span>New Chat</span>
          </button>
        </div>
      )}

      {/* Messages Area */}
      <div className={clsx("flex-1 overflow-y-auto px-8 pb-32", messages.length > 0 ? "pt-4" : "pt-8")}>
        {messages.length === 0 ? (
          <div className="flex flex-col justify-center h-full max-w-3xl mx-auto space-y-10">
            <div className="space-y-4 px-1">
              <div className="bg-accent/10 border-l-4 border-accent p-5 rounded-r-[10px]">
                <h2 className="text-[13px] font-mono font-bold text-ink uppercase tracking-wider mb-2">
                  Objective
                </h2>
                <p className="text-[15px] font-sans text-ink leading-relaxed">
                  Drive product decisions using the authentic voice of the customer. Echo instantly synthesizes raw feedback across App Store, Play Store, Reddit, and YouTube into actionable insights—helping you confidently steer Blinkit's roadmap with real, data-backed evidence.
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
      <div className="absolute bottom-0 left-0 right-0 p-6 bg-bg flex flex-col items-center">
        <div className="w-full max-w-3xl mb-3 flex justify-start relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setShowQuestions(!showQuestions)}
            className={clsx(
              "flex items-center space-x-2 text-[12px] font-sans font-medium px-4 py-1.5 rounded-full transition-all border",
              showQuestions 
                ? "bg-surface text-ink border-surface shadow-sm" 
                : "bg-transparent text-ink-muted border-[#E7E5DE] hover:bg-surface/50 hover:text-ink hover:border-surface"
            )}
          >
            <Sparkles size={14} className={showQuestions ? "text-accent" : ""} />
            <span>More seed questions</span>
            <ChevronUp size={14} className={clsx("transition-transform duration-200", showQuestions && "rotate-180")} />
          </button>

          {showQuestions && (
            <div className="absolute bottom-full left-0 mb-2 w-[320px] bg-surface border border-[#E7E5DE] rounded-xl shadow-xl overflow-hidden animate-in fade-in slide-in-from-bottom-2 z-50">
              <div className="px-3 py-2 border-b border-bg/50">
                <span className="text-[10px] font-mono text-ink-muted uppercase tracking-wider">Select a question</span>
              </div>
              <div className="py-1 max-h-[250px] overflow-y-auto custom-scrollbar">
                {dropdownQuestions.map((q) => (
                  <button
                    key={q}
                    onClick={() => {
                      handleSubmit(q);
                      setShowQuestions(false);
                    }}
                    className="block w-full text-left px-4 py-2.5 text-[13px] font-sans text-ink hover:bg-bg transition-colors border-l-2 border-transparent hover:border-accent"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit(input);
          }}
          className="relative max-w-3xl w-full mx-auto"
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
            className="w-full min-h-[56px] max-h-[120px] bg-surface border border-[#E7E5DE] rounded-[10px] pl-6 pr-14 py-4 text-[15px] leading-6 text-ink placeholder:text-ink-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:border-transparent resize-none custom-scrollbar"
            rows={1}
          />
          <button
            type="submit"
            disabled={isInputDisabled || isCurrentlyLoading}
            className={clsx(
              "absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-full transition-all flex items-center justify-center",
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
