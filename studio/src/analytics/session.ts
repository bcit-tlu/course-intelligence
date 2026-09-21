const SESSION_KEY = "ci.session.id";

// In-memory fallback for when sessionStorage is unavailable — e.g. private
// browsing mode, storage blocked by site policy, or a SecurityError from
// cookie/storage restrictions. Without this fallback, getSessionId() and
// the session-start dedup in events.ts throw before React renders, leaving
// the user with a blank Studio. Degradation: persistence across reloads is
// lost (a reload gets a new in-memory ID), but the session ID stays stable
// for the tab's lifetime so telemetry still works and the app still loads.
const _memStore = new Map<string, string>();

/** sessionStorage.getItem with an in-memory fallback when storage is blocked. */
export function safeGetItem(key: string): string | null {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return _memStore.has(key) ? _memStore.get(key)! : null;
  }
}

/** sessionStorage.setItem with an in-memory fallback when storage is blocked. */
export function safeSetItem(key: string, value: string): void {
  try {
    sessionStorage.setItem(key, value);
  } catch {
    _memStore.set(key, value);
  }
}

export function getSessionId(): string {
  if (typeof window === "undefined") return "";

  let id = safeGetItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    safeSetItem(SESSION_KEY, id);
  }
  return id;
}
