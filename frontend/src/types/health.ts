export interface ReadyResponse {
  status: "ok" | "degraded";
  checks: Record<string, "ok" | "unavailable">;
}
