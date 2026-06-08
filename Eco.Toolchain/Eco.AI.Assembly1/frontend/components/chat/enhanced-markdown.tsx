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

// Mermaid grammar starts with a fixed set of diagram-type tokens. We treat
// a fenced block as a mermaid diagram when EITHER the language tag is
// "mermaid", OR the language tag is itself a mermaid diagram type, OR no
// language tag is given but the first non-empty line begins with one of
// these tokens. This catches LLMs that emit ```flowchart or bare ``` for
// architecture diagrams (Kimi/GLM do this regularly).
const MERMAID_DIAGRAM_TYPES = new Set([
  "flowchart", "graph",
  "sequenceDiagram", "classDiagram",
  "stateDiagram", "stateDiagram-v2",
  "erDiagram", "journey", "gantt", "pie",
  "quadrantChart", "requirementDiagram",
  "gitGraph", "gitgraph", "mindmap", "timeline",
  "C4Context", "C4Container", "C4Component", "C4Dynamic", "C4Deployment",
  "sankey-beta", "xychart-beta", "block-beta", "packet-beta",
]);

function looksLikeMermaid(source: string): boolean {
  const firstLine = source.split(/\r?\n/).find((l) => l.trim().length > 0);
  if (!firstLine) return false;
  const firstToken = firstLine.trim().split(/\s+/)[0];
  return MERMAID_DIAGRAM_TYPES.has(firstToken);
}

// prose-invert: dark-theme typography defaults from @tailwindcss/typography.
// max-w-none: don't clamp to 65ch — handoffs and mermaid diagrams need width.
// prose-pre:*: cancel prose's own <pre> styling — we render our own pre/code
// panels in the components map below, so the two should not stack.
const PROSE_CLASSES =
  "prose prose-invert prose-slate max-w-none " +
  "prose-pre:bg-transparent prose-pre:p-0 prose-pre:m-0 prose-pre:border-0 " +
  "prose-code:bg-transparent prose-code:p-0 prose-code:font-mono " +
  "prose-code:before:content-none prose-code:after:content-none";

export function EnhancedMarkdown({ children, className }: EnhancedMarkdownProps) {
  return (
    <div className={[PROSE_CLASSES, className ?? ""].join(" ").trim()}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
        skipHtml
        components={{
          // Mermaid blocks → diagram. Other code blocks → highlight.js.
          // We accept ```mermaid, ```flowchart/```graph/etc, and untagged
          // blocks whose first line looks like a mermaid diagram type.
          code({ inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || "");
            const lang = match ? match[1] : null;
            const value = String(children ?? "").replace(/\n$/, "");
            const isMermaid =
              !inline && (
                lang === "mermaid" ||
                (lang !== null && MERMAID_DIAGRAM_TYPES.has(lang)) ||
                (lang === null && looksLikeMermaid(value))
              );
            if (isMermaid) {
              return <MermaidDiagram code={value} />;
            }
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
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
