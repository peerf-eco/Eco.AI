"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FolderUp, Upload, Download, Database, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";

interface RagIndexStatus {
  available: boolean;
  chunks: number;
  size_bytes: number;
  last_import: Record<string, unknown> | null;
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export function RagSection({ onImported }: { onImported?: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const folderRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [index, setIndex] = useState<RagIndexStatus | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/rag/status`);
      if (!response.ok) return;
      setIndex(await response.json());
    } catch {
      // Status is informational — ignore fetch failures.
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  const upload = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy(true);
    setStatus(`Importing ${files.length} file${files.length === 1 ? "" : "s"}…`);
    const form = new FormData();
    const paths: Record<string, string> = {};
    Array.from(files).forEach((file, index) => {
      form.append("files", file);
      paths[String(index)] = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
    });
    form.append("relative_paths", JSON.stringify(paths));
    try {
      const response = await fetch(`${API_URL}/rag/import`, { method: "POST", body: form });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "RAG import failed");
      const stats = body.stats || {};
      const parts = [
        `${stats.chunks ?? 0} chunks embedded`,
        stats.imported_files ? `${stats.imported_files} files` : null,
        stats.imported_sqlite_chunks ? `${stats.imported_sqlite_chunks} dump rows` : null,
      ].filter(Boolean);
      setStatus(`Imported — ${parts.join(", ")}`);
      onImported?.();
      void refreshStatus();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "RAG import failed");
    } finally {
      setBusy(false);
    }
  };

  const exportIndex = async () => {
    setBusy(true);
    setStatus("Preparing index export…");
    try {
      const response = await fetch(`${API_URL}/rag/export`);
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "RAG export failed");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "marketplace_index.sqlite";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setStatus(`Exported marketplace_index.sqlite (${formatBytes(blob.size)})`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "RAG export failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      {/* Index summary */}
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-emerald-500/15">
            <Database className="h-3.5 w-3.5 text-emerald-300" />
          </div>
          <span className="text-xs font-semibold">Marketplace index</span>
          {index?.available && (
            <span className="ml-auto rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
              {index.chunks.toLocaleString()} chunks · {formatBytes(index.size_bytes)}
            </span>
          )}
        </div>
        {index?.last_import != null && (
          <p className="mt-1.5 text-[10px] text-muted-foreground/60">
            Last import: {String(index.last_import.imported_files ?? 0)} files,{" "}
            {String(index.last_import.chunks ?? 0)} chunks
          </p>
        )}
      </div>

      <div className="grid grid-cols-3 gap-1.5">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={busy}
          onClick={() => fileRef.current?.click()}
          className="h-8 rounded-lg border-white/[0.1] bg-white/[0.03] text-[11px] hover:bg-white/[0.08]"
        >
          <Upload className="mr-1.5 h-3.5 w-3.5" />
          Files
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={busy}
          onClick={() => folderRef.current?.click()}
          className="h-8 rounded-lg border-white/[0.1] bg-white/[0.03] text-[11px] hover:bg-white/[0.08]"
        >
          <FolderUp className="mr-1.5 h-3.5 w-3.5" />
          Folder
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={busy || !index?.available}
          onClick={exportIndex}
          className="h-8 rounded-lg border-white/[0.1] bg-white/[0.03] text-[11px] hover:bg-white/[0.08]"
        >
          {busy ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Download className="mr-1.5 h-3.5 w-3.5" />}
          Export
        </Button>
      </div>
      <input ref={fileRef} type="file" multiple className="hidden" onChange={(event) => upload(event.target.files)} />
      <input
        ref={folderRef}
        type="file"
        multiple
        {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
        className="hidden"
        onChange={(event) => upload(event.target.files)}
      />

      {status && <p className="text-[11px] text-muted-foreground">{status}</p>}
      <p className="text-[10px] leading-relaxed text-muted-foreground/60">
        <span>
          Import accepts C/C++ sources, headers, IDL, Markdown and SQLite dumps;
          documents are chunked, embedded and merged into the shared{" "}
          <span className="font-mono">marketplace_index.sqlite</span>. Export
          downloads that index for backup or another workspace.
        </span>
      </p>
    </div>
  );
}
