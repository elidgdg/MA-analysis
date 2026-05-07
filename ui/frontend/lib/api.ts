const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body?.detail ?? JSON.stringify(body);
    } catch {
      detail = await res.text();
    }
    throw new Error(`GET ${path} failed (${res.status}): ${detail}`);
  }
  return (await res.json()) as T;
}

export function fetchPendingDeals(): Promise<any[]> {
  return getJSON("/pending-deals");
}

export function fetchDealSummary(eventId: number): Promise<any> {
  return getJSON(`/deal/${eventId}/summary`);
}

export function fetchDealSources(
  eventId: number
): Promise<{ sources: any[] }> {
  return getJSON(`/deal/${eventId}/sources`);
}

export function fetchDealAnalogues(
  eventId: number
): Promise<{ data: any }> {
  return getJSON(`/deal/${eventId}/analogues`);
}

export function fetchDealComparison(
  eventId: number
): Promise<{ data: any }> {
  return getJSON(`/deal/${eventId}/comparison`);
}
