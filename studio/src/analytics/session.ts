const SESSION_KEY = "ci.session.id";

// In-memory fallback for when sessionStorage is unavailable — e.g. private
// browsing mode, storage blocked by site policy, or a SecurityError from
// cookie/storage restrictions. Without this fallback, getSessionId() and
// the session-start dedup in events.ts throw before React renders, leaving
// the user with a blank Studio. Degradation: persistence across reloads is
// lost (a reload gets a new in-memory ID), but the session ID stays stable
// for the tab's lifetime so telemetry still works and the app still loads.
const _memStore = new Map<string, string>();

/** sessionStorage.getItem with an in-memory fallback when storage is blocked.
 *
 * Checks _memStore first: a value there means a prior write fell back to
 * memory (sessionStorage writes failed), so it's the authoritative value
 * for this tab. Without this ordering, a sessionStorage that reads fine but
 * throws on writes returns null on every read — getSessionId() would mint a
 * new ID per call and break session correlation across spans and API calls.
 */
export function safeGetItem(key: string): string | null {
  if (_memStore.has(key)) return _memStore.get(key)!;
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

/** sessionStorage.setItem with an in-memory fallback when storage is blocked.
 *
 * Deletes the _memStore entry on success so that, once storage recovers,
 * reads go back to sessionStorage (the durable store) instead of serving a
 * stale in-memory value from the blocked period.
 */
export function safeSetItem(key: string, value: string): void {
  try {
    sessionStorage.setItem(key, value);
    _memStore.delete(key);
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
