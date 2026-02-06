"use client";

import React, { useState, useEffect } from "react";
import { Database, CheckCircle2, AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface RagStatus {
  chroma_initialized: boolean;
  rag_storage_exists: boolean;
  source_files_count: number;
  is_initializing: boolean;
  init_progress: number;
  init_message: string;
}

export function RagInitializer() {
  const [status, setStatus] = useState<RagStatus | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);

  // Загружаем статус при монтировании
  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/rag-status");
      const data = await res.json();
      setStatus(data);
      
      if (data.is_initializing) {
        setIsInitializing(true);
        setProgress(data.init_progress);
        setMessage(data.init_message);
      }
    } catch (e) {
      console.error("Failed to check RAG status:", e);
    }
  };

  const startInitialization = async () => {
    setIsInitializing(true);
    setProgress(0);
    setMessage("Starting...");
    setError(null);
    setIsComplete(false);

    try {
      const response = await fetch("http://localhost:8000/api/init-rag");
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.error) {
                setError(data.message);
                setIsInitializing(false);
                return;
              }
              
              setProgress(data.progress);
              setMessage(data.message);
              
              if (data.done) {
                setIsComplete(true);
                setIsInitializing(false);
                // Обновляем статус
                await checkStatus();
              }
            } catch (e) {
              // Ignore parse errors for empty lines
            }
          }
        }
      }
    } catch (e: any) {
      setError(e.message);
      setIsInitializing(false);
    }
  };

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 text-primary" />
          <CardTitle className="text-lg">Vector Store (RAG)</CardTitle>
        </div>
        <CardDescription>
          Векторное хранилище для поиска по компонентам EcoOS
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Статус */}
        {status && !isInitializing && !isComplete && (
          <div className="flex items-center gap-2 text-sm">
            {status.chroma_initialized ? (
              <>
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <span className="text-green-500">Initialized</span>
                <span className="text-muted-foreground">
                  ({status.source_files_count} source files)
                </span>
              </>
            ) : (
              <>
                <AlertCircle className="h-4 w-4 text-yellow-500" />
                <span className="text-yellow-500">Not initialized</span>
                {status.rag_storage_exists && (
                  <span className="text-muted-foreground">
                    ({status.source_files_count} files ready)
                  </span>
                )}
              </>
            )}
          </div>
        )}

        {/* Прогресс-бар */}
        {(isInitializing || isComplete) && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className={cn(
                "flex items-center gap-2",
                isComplete ? "text-green-500" : "text-muted-foreground"
              )}>
                {isInitializing && <Loader2 className="h-4 w-4 animate-spin" />}
                {isComplete && <CheckCircle2 className="h-4 w-4" />}
                {message}
              </span>
              <span className="font-mono text-xs">{progress}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}

        {/* Ошибка */}
        {error && (
          <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Кнопки */}
        <div className="flex gap-2">
          <Button
            onClick={startInitialization}
            disabled={isInitializing || (status?.chroma_initialized && !error)}
            className="flex-1"
          >
            {isInitializing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Initializing...
              </>
            ) : status?.chroma_initialized ? (
              <>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Already Initialized
              </>
            ) : (
              <>
                <Database className="mr-2 h-4 w-4" />
                Create Vector Store
              </>
            )}
          </Button>
          
          {status?.chroma_initialized && (
            <Button
              variant="outline"
              size="icon"
              onClick={startInitialization}
              disabled={isInitializing}
              title="Rebuild vector store"
            >
              <RefreshCw className={cn("h-4 w-4", isInitializing && "animate-spin")} />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

