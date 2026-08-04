"use client";

import { useRef, useState } from "react";
import { FolderUp, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";

export function RagImport() {
  const fileRef = useRef<HTMLInputElement>(null);
  const folderRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState("");

  const upload = async (files: FileList | null) => {
    if (!files?.length) return;
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
      setStatus(`Imported ${body.stats?.chunks ?? 0} chunks`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "RAG import failed");
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
          <Upload className="mr-2 h-3.5 w-3.5" />
          Import files
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={() => folderRef.current?.click()}>
          <FolderUp className="mr-2 h-3.5 w-3.5" />
          Import folder
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
      {status && <p className="text-xs text-muted-foreground">{status}</p>}
      <p className="text-[11px] text-muted-foreground/70">
        Updates marketplace_index.sqlite. SQLite dumps and source documents are accepted.
      </p>
    </div>
  );
}