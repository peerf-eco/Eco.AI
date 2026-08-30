/**
 * Single API-base policy for every component.
 *
 * - NEXT_PUBLIC_API_URL set (dev stack / docker-compose): use it verbatim.
 * - Unset (static bundle served by FastAPI on the same port): same-origin —
 *   the UI talks to window.location.origin and no CORS is involved.
 */
const envUrl = process.env.NEXT_PUBLIC_API_URL;

export const API_URL: string =
  envUrl && envUrl.length > 0
    ? envUrl.replace(/\/$/, "")
    : typeof window !== "undefined"
      ? window.location.origin
      : "";

export const WS_BASE: string = API_URL.replace(/^http/, "ws");
