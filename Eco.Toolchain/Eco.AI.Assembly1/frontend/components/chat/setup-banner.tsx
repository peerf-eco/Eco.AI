"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { X } from "lucide-react";
import { API_URL } from "@/lib/api";

const DISMISS_KEY = "eco_harness.setup_banner_dismissed";

export function SetupBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(DISMISS_KEY)) return;
    fetch(`${API_URL}/api/setup/status`)
      .then((r) => r.json())
      .then((s) => setVisible(!s.configured))
      .catch(() => setVisible(false));
  }, []);

  if (!visible) return null;

  return (
    <div className="flex items-center justify-between gap-3 border-b border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-600 dark:text-amber-400">
      <span>
        Setup not finished — the app runs degraded until an OpenRouter key is
        configured.
      </span>
      <span className="flex items-center gap-2">
        <Link href="/setup" className="font-medium underline underline-offset-4">
          Finish setup
        </Link>
        <button
          aria-label="Dismiss"
          onClick={() => {
            localStorage.setItem(DISMISS_KEY, "1");
            setVisible(false);
          }}
          className="rounded p-1 hover:bg-amber-500/20"
        >
          <X className="h-4 w-4" />
        </button>
      </span>
    </div>
  );
}
