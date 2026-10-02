// @spec docs/BACKLOG.md#RG-012 | docs/BACKLOG.md#RG-013 | docs/DAT.md#api
// Client de l'API du moteur, sur la même origine (/api relayé par Vite en dev, nginx en prod).

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly details: { champ: string; message: string }[] = [],
  ) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    credentials: "same-origin",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new ApiError(response.status, data.detail ?? response.statusText, data.erreurs ?? []);
  }
  return data as T;
}

export interface Health {
  status: string;
  version: string;
  env: string;
  profile: string;
  degraded: string[];
  components: Record<string, boolean>;
}

export interface AuditEntity {
  label: string;
  detector: string;
  score: number;
  action: string;
  preview: string | null;
}

export interface AuditEvent {
  id: number;
  ts: string;
  event: string;
  tool: string | null;
  decision: string;
  profile: string;
  latency_ms: number;
  entity_count: number;
  categories: { category: string; probability: number; action: string }[];
  bypass: boolean;
  partial: boolean;
  subagent: boolean;
  note: string | null;
  entities: AuditEntity[];
}

export interface AuditPage {
  events: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditStats {
  total: number;
  by_decision: Record<string, number>;
  by_label: Record<string, number>;
}

export interface Finding {
  start: number;
  end: number;
  label: string;
  name: string;
  score: number;
  detector: string;
  validated: boolean;
  action: string;
  preview: string;
}

export interface Analysis {
  decision: string;
  profile: string;
  partial: boolean;
  counts: Record<string, number>;
  categories: { category: string; name: string; probability: number; action: string }[];
  timings_ms: Record<string, number>;
  findings: Finding[];
  pseudonymized: string;
}

export interface LabelRule {
  prompt: string;
  tool_output: string;
  min_score: number;
}

export interface CategoryRule {
  threshold: number;
  action: string;
}

export interface Policy {
  version: number;
  labels: Record<string, LabelRule>;
  categories: Record<string, CategoryRule>;
  allowlist: { values: string[]; patterns: string[] };
  secret_files: string[];
  secret_files_exceptions: string[];
  bypass_excluded: string[];
}

export interface PolicyResponse {
  policy: Policy;
  source: "default" | "custom";
  labels: Record<string, string>;
  categories: Record<string, string>;
}

export interface Component {
  name: string;
  kind: string;
  ready: boolean;
  load_ms: number;
  error: string | null;
  detail: Record<string, string>;
}

export interface Scores {
  precision: number;
  recall: number;
  f1: number;
  tp: number;
  fp: number;
  fn: number;
}

export interface BenchResult {
  profile: string;
  records: number;
  global: Scores;
  by_label: Record<string, Scores>;
  categories: Record<string, Scores>;
  latency_ms: { p50: number; p95: number; mean: number };
}

export interface EnginesResponse {
  default_profile: string;
  profiles: Record<
    string,
    { detectors: string[]; classifiers_prompt: string[]; classifiers_output: string[]; missing: string[] }
  >;
  components: Component[];
  vault: { sessions: number; tokens: number };
  bench: { generated_at: string; corpus: { records: number }; results: BenchResult[] } | null;
  labels: Record<string, string>;
  categories: Record<string, string>;
}

export const api = {
  health: () => request<Health>("GET", "/health"),
  session: () => request<{ authenticated: boolean }>("GET", "/v1/auth/session"),
  login: (token: string) => request<{ authenticated: boolean }>("POST", "/v1/auth/session", { token }),
  logout: () => request<{ authenticated: boolean }>("DELETE", "/v1/auth/session"),
  events: (params: Record<string, string | number>) => {
    const query = new URLSearchParams(
      Object.entries(params)
        .filter(([, value]) => value !== "")
        .map(([key, value]) => [key, String(value)]),
    );
    return request<AuditPage>("GET", `/v1/audit/events?${query.toString()}`);
  },
  stats: () => request<AuditStats>("GET", "/v1/audit/stats"),
  analyze: (text: string, profile: string, context: string) =>
    request<Analysis>("POST", "/v1/analyze", { text, profile, context }),
  policy: () => request<PolicyResponse>("GET", "/v1/policies"),
  savePolicy: (policy: Policy) => request<PolicyResponse>("PUT", "/v1/policies", policy),
  resetPolicy: () => request<PolicyResponse>("POST", "/v1/policies/reset"),
  engines: () => request<EnginesResponse>("GET", "/v1/engines"),
};
