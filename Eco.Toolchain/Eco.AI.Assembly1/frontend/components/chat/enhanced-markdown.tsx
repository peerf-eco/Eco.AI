"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";

import { MermaidDiagram } from "./mermaid-diagram";

interface EnhancedMarkdownProps {
  children: string;
  className?: string;
}

// Iconography for known plan section headings — keeps long handoff cards
// scannable. Matches the section names in ARCHITECT_SYSTEM_PROMPT.
const HEADING_ICONS: Record<string, string> = {
  "user objective": "🎯",
  "selected marketplace components": "📦",
  "to-be-written code": "📝",
  "project layout": "🌳",
  "architecture diagram": "🗺️",
  "interface contracts": "🔌",
  "acceptance criteria": "✅",
  "do not redo": "🚫",
  "handoff to coder": "🤝",
  "handoff to tester": "🧪",
  "handoff to architect": "↩️",
  "build log highlights": "🔧",
  "what the binary does": "📟",
  "how to invoke": "▶️",
  "artifact path": "📍",
};

function headingIcon(text: string): string | null {
  const key = text.trim().toLowerCase();
  return HEADING_ICONS[key] ?? null;
}

export function EnhancedMarkdown({ children, className }: EnhancedMarkdownProps) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
        skipHtml
        components={{
          // ```mermaid blocks → diagram. Other code blocks → highlight.js.
          code({ inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || "");
            const lang = match ? match[1] : null;
            const value = String(children ?? "").replace(/\n$/, "");
            if (!inline && lang === "mermaid") {
              return <MermaidDiagram code={value} />;
            }
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
          // Section headings get an emoji prefix for visual scanning.
          h1({ children, ...props }: any) {
            const text = String(Array.isArray(children) ? children.join("") : children ?? "");
            const icon = headingIcon(text);
            return (
              <h1 {...props} className="flex items-baseline gap-2 border-b border-slate-700/50 pb-2 mt-4 mb-3 text-2xl font-semibold">
                {icon && <span aria-hidden>{icon}</span>}
                <span>{children}</span>
              </h1>
            );
          },
          h2({ children, ...props }: any) {
            const text = String(Array.isArray(children) ? children.join("") : children ?? "");
            const icon = headingIcon(text);
            return (
              <h2 {...props} className="flex items-baseline gap-2 mt-5 mb-2 text-lg font-semibold text-slate-200">
                {icon && <span aria-hidden>{icon}</span>}
                <span>{children}</span>
              </h2>
            );
          },
          h3({ children, ...props }: any) {
            const text = String(Array.isArray(children) ? children.join("") : children ?? "");
            const icon = headingIcon(text);
            return (
              <h3 {...props} className="flex items-baseline gap-2 mt-3 mb-1 text-base font-medium text-slate-300">
                {icon && <span aria-hidden>{icon}</span>}
                <span>{children}</span>
              </h3>
            );
          },
          // Make pre/code blocks look like proper code panels.
          pre({ children, ...props }: any) {
            return (
              <pre
                {...props}
                className="my-2 overflow-x-auto rounded-md border border-slate-700/40 bg-slate-950/60 p-3 text-xs leading-relaxed"
              >
                {children}
              </pre>
            );
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
