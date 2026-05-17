"use client";

import { useEffect, useRef, useState } from "react";

let mermaidInitialized = false;

async function ensureMermaid() {
  const mod = await import("mermaid");
  const mermaid = mod.default;
  if (!mermaidInitialized) {
    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      securityLevel: "loose",
      themeVariables: {
        primaryColor: "#1e293b",
        primaryTextColor: "#e2e8f0",
        primaryBorderColor: "#475569",
        lineColor: "#94a3b8",
        secondaryColor: "#334155",
        tertiaryColor: "#0f172a",
        fontFamily: "ui-sans-serif, system-ui, sans-serif",
      },
    });
    mermaidInitialized = true;
  }
  return mermaid;
}

interface MermaidDiagramProps {
  code: string;
}

export function MermaidDiagram({ code }: MermaidDiagramProps) {
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const idRef = useRef(`mmd-${Math.random().toString(36).slice(2, 10)}`);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setSvg(null);

    (async () => {
      try {
        const mermaid = await ensureMermaid();
        // Validate before rendering — mermaid.parse throws on bad syntax.
        try {
          await mermaid.parse(code);
        } catch (parseErr: any) {
          if (!cancelled) {
            setError(typeof parseErr?.message === "string"
              ? parseErr.message
              : "Mermaid parse error");
          }
          return;
        }
        const { svg: rendered } = await mermaid.render(idRef.current, code);
        if (!cancelled) setSvg(rendered);
      } catch (e: any) {
        if (!cancelled) {
          setError(typeof e?.message === "string" ? e.message : "Mermaid render failed");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [code]);

  if (error) {
    return (
      <div className="my-2 rounded-md border border-red-500/40 bg-red-950/20 p-3 text-xs text-red-300">
        <div className="mb-1 font-medium">Mermaid error</div>
        <div className="font-mono whitespace-pre-wrap">{error}</div>
        <details className="mt-2 opacity-70">
          <summary className="cursor-pointer">show source</summary>
          <pre className="mt-1 whitespace-pre-wrap text-[10px]">{code}</pre>
        </details>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="my-2 rounded-md border border-slate-700/50 bg-slate-900/40 p-3 text-xs text-slate-400">
        Rendering diagram...
      </div>
    );
  }

  return (
    <div
      className="my-3 overflow-x-auto rounded-md border border-slate-700/40 bg-slate-950/40 p-3"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
