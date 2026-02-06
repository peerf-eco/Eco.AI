"use client";

import React, { useState, useEffect, useRef } from "react";
import { Send, Bot, User, FileCode, Settings, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { ProgressViewer, Stage } from "./progress-viewer";
import { RagInitializer } from "./rag-initializer";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
  files?: GeneratedFile[];
}

interface GeneratedFile {
  path: string;
  type: string;
  url: string;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [currentStage, setCurrentStage] = useState<Stage>("analyze_request");
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const threadId = useRef(Math.random().toString(36).substring(7));

  useEffect(() => {
    // Подключение WebSocket
    const ws = new WebSocket(`ws://localhost:8000/ws/chat/${threadId.current}`);
    
    ws.onopen = () => {
      console.log("Connected to agent");
      setIsConnected(true);
    };

    ws.onclose = () => {
      console.log("Disconnected");
      setIsConnected(false);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWsMessage(data);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, []);

  // Автоскролл
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, statusMessage]);

  const handleWsMessage = (data: any) => {
    switch (data.type) {
      case "token":
        // Стриминг ответа
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.role === "assistant") {
            return [
              ...prev.slice(0, -1),
              { ...lastMsg, content: lastMsg.content + data.content },
            ];
          } else {
            return [...prev, { role: "assistant", content: data.content }];
          }
        });
        break;

      case "progress":
        // Обновление стадии
        if (data.status === "running") {
          setCurrentStage(data.stage);
          setIsProcessing(true);
        } else if (data.status === "completed") {
          // Стадия завершена
        }
        break;

      case "status":
        // Текстовый статус (например "Analyzing...")
        setStatusMessage(data.content);
        break;

      case "files":
        // Пришли файлы
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.role === "assistant") {
            return [
              ...prev.slice(0, -1),
              { ...lastMsg, files: data.files },
            ];
          }
          return prev;
        });
        break;

      case "done":
        setIsProcessing(false);
        setCurrentStage("complete");
        setStatusMessage("");
        break;

      case "error":
        console.error("Agent error:", data.content);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${data.content}` },
        ]);
        setIsProcessing(false);
        break;
    }
  };

  const sendMessage = () => {
    if (!input.trim() || !isConnected) return;

    // Добавляем сообщение пользователя
    setMessages((prev) => [...prev, { role: "user", content: input }]);
    
    // Отправляем
    wsRef.current?.send(JSON.stringify({ message: input }));
    
    setInput("");
    setIsProcessing(true);
    setCurrentStage("analyze_request");
    
    // Создаем пустой ответ ассистента, чтобы токены дописывались
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Settings Sidebar */}
      <div
        className={cn(
          "fixed inset-y-0 right-0 z-50 w-80 border-l bg-background p-4 shadow-lg transition-transform duration-300",
          showSettings ? "translate-x-0" : "translate-x-full"
        )}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Settings</h2>
          <Button variant="ghost" size="icon" onClick={() => setShowSettings(false)}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <RagInitializer />
      </div>

      {/* Overlay */}
      {showSettings && (
        <div 
          className="fixed inset-0 z-40 bg-black/50" 
          onClick={() => setShowSettings(false)} 
        />
      )}

      {/* Main Content */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b p-4">
          <div>
            <h1 className="text-xl font-bold">EcoOS Component Agent</h1>
            <p className="text-sm text-muted-foreground">
              Connected: {isConnected ? "Yes" : "No"} | Thread: {threadId.current}
            </p>
          </div>
          <Button variant="outline" size="icon" onClick={() => setShowSettings(true)}>
            <Settings className="h-4 w-4" />
          </Button>
        </div>

        {/* Main Chat Area */}
        <ScrollArea className="flex-1 p-4">
          <div className="mx-auto max-w-3xl space-y-6">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={cn(
                  "flex gap-3",
                  msg.role === "user" ? "flex-row-reverse" : "flex-row"
                )}
              >
                <div
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border",
                    msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                  )}
                >
                  {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
                </div>
                
                <div className="flex max-w-[80%] flex-col gap-2">
                  <Card className={cn(
                      "p-4", 
                      msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-card"
                  )}>
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  </Card>

                  {/* Файлы */}
                  {msg.files && (
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {msg.files.map((file, fIdx) => (
                        <a
                          key={fIdx}
                          href={`http://localhost:8000${file.url}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 rounded-md border bg-card p-2 text-sm hover:bg-accent"
                        >
                          <FileCode className="h-4 w-4 text-blue-500" />
                          <span className="truncate">{file.path}</span>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Индикатор статуса */}
            {isProcessing && (
              <div className="flex flex-col gap-2 rounded-lg border bg-muted/50 p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Bot size={16} />
                  <span>{statusMessage || "Processing..."}</span>
                </div>
                <ProgressViewer currentStage={currentStage} isProcessing={isProcessing} />
              </div>
            )}
            
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="border-t p-4">
          <div className="mx-auto flex max-w-3xl gap-2">
            <Input
              placeholder="Describe the component you want to create..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
              disabled={!isConnected || isProcessing}
            />
            <Button 
              onClick={sendMessage} 
              disabled={!isConnected || isProcessing || !input.trim()}
            >
              <Send size={18} />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

