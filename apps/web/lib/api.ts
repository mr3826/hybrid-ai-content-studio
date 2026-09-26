export interface HealthData {
  status: string;
  database: string;
  version: string;
  app_env: string;
  registered_engines: number;
  timestamp: string;
}

export interface StudioStatus {
  niche_configured: boolean;
  brand_configured: boolean;
  platforms_configured_count: number;
  is_setup_completed: boolean;
  discovery_ready: boolean;
  generation_ready: boolean;
  active_niche_name: string | null;
  active_brand_name: string | null;
}

export interface ContentPillar {
  id: string;
  name: string;
  description: string;
}

export interface NicheProfile {
  id?: string;
  name: string;
  one_sentence_definition: string;
  audience: string;
  audience_regions: string[];
  primary_problems: string[];
  allowed_topics: string[];
  adjacent_topics: string[];
  blocked_topics: string[];
  must_have_signals: string[];
  negative_keywords: string[];
  preferred_source_types: string[];
  content_pillars: ContentPillar[];
  commercial_intent_topics: string[];
  evergreen_topics: string[];
  created_at?: string;
  updated_at?: string;
}

export interface BrandProfile {
  id?: string;
  brand_name: string;
  brand_promise: string;
  audience: string;
  tone: string[];
  voice_rules: string[];
  preferred_vocabulary: string[];
  avoid_vocabulary: string[];
  banned_cliches: string[];
  claim_rules: string[];
  cta_style: string;
  humor_policy: string;
  controversy_policy: string;
  sponsor_policy: string;
  affiliate_disclosure_style: string;
  visual_identity: Record<string, any>;
  platform_adaptations: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface BrandExemplar {
  id: string;
  category: string;
  title: string;
  content: string;
  context_note?: string | null;
  platform: string;
  created_at: string;
  updated_at: string;
}

export interface PlatformSetting {
  platform: string;
  channel_name: string;
  channel_url: string;
  publishing_url: string;
  account_handle: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8400";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`API Error [${res.status}]: ${errorBody}`);
  }

  if (res.status === 204) {
    return {} as T;
  }

  return await res.json();
}

export async function getHealth(): Promise<HealthData | null> {
  try {
    return await request<HealthData>("/health", { cache: "no-store" });
  } catch (error) {
    return null;
  }
}

export async function getStudioStatus(): Promise<StudioStatus | null> {
  try {
    return await request<StudioStatus>("/api/v1/settings/status", { cache: "no-store" });
  } catch (error) {
    return null;
  }
}

// Single Niche
export async function getNiche(): Promise<NicheProfile | null> {
  try {
    return await request<NicheProfile>("/api/v1/niche", { cache: "no-store" });
  } catch (error) {
    return null;
  }
}

export async function updateNiche(data: NicheProfile): Promise<NicheProfile> {
  return await request<NicheProfile>("/api/v1/niche", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function seedNiche(): Promise<NicheProfile> {
  return await request<NicheProfile>("/api/v1/niche/seed-default", {
    method: "POST",
  });
}

// Single Brand
export async function getBrand(): Promise<BrandProfile | null> {
  try {
    return await request<BrandProfile>("/api/v1/brand", { cache: "no-store" });
  } catch (error) {
    return null;
  }
}

export async function updateBrand(data: BrandProfile): Promise<BrandProfile> {
  return await request<BrandProfile>("/api/v1/brand", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function seedBrand(): Promise<BrandProfile> {
  return await request<BrandProfile>("/api/v1/brand/seed-default", {
    method: "POST",
  });
}

// Brand Exemplars
export async function getBrandExemplars(category?: string): Promise<BrandExemplar[]> {
  const q = category ? `?category=${encodeURIComponent(category)}` : "";
  return await request<BrandExemplar[]>(`/api/v1/brand/exemplars${q}`, { cache: "no-store" });
}

export async function createBrandExemplar(data: Partial<BrandExemplar>): Promise<BrandExemplar> {
  return await request<BrandExemplar>("/api/v1/brand/exemplars", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteBrandExemplar(id: string): Promise<void> {
  await request<void>(`/api/v1/brand/exemplars/${id}`, {
    method: "DELETE",
  });
}

// Platforms
export async function getPlatforms(): Promise<Record<string, PlatformSetting>> {
  return await request<Record<string, PlatformSetting>>("/api/v1/platforms", { cache: "no-store" });
}

export async function updatePlatform(platform: string, data: Partial<PlatformSetting>): Promise<PlatformSetting> {
  return await request<PlatformSetting>(`/api/v1/platforms/${platform}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function seedPlatforms(): Promise<Record<string, PlatformSetting>> {
  return await request<Record<string, PlatformSetting>>("/api/v1/platforms/seed-default", {
    method: "POST",
  });
}

// Full settings export/import
export async function exportSettings(): Promise<any> {
  return await request<any>("/api/v1/settings/export", { cache: "no-store" });
}

export async function importSettings(payload: any): Promise<StudioStatus> {
  return await request<StudioStatus>("/api/v1/settings/import", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function seedAllSettings(): Promise<StudioStatus> {
  return await request<StudioStatus>("/api/v1/settings/seed-all", {
    method: "POST",
  });
}

// ==========================================
// Feature Engines
// ==========================================

export interface EngineSummary {
  id: string;
  name: string;
  version: string;
  description: string;
  enabled: boolean;
  inputs: string[];
  outputs: string[];
  dependencies: string[];
  triggers: string[];
  supports: Record<string, boolean>;
  health: {
    status: "healthy" | "degraded" | "failing";
    message: string;
    checked_at: string;
    details: Record<string, any>;
  };
  last_run_at: string | null;
  last_run_status: string | null;
  total_runs_count: number;
}

export interface EngineRunRecord {
  id: string;
  engine_id: string;
  engine_version: string;
  run_id: string;
  trigger: string;
  status: string;
  started_at: string;
  ended_at: string;
  duration_ms: number;
  input_count: number;
  output_count: number;
  rejected_count: number;
  error_count: number;
  cost: number;
  summary: string;
  parameters: Record<string, any>;
  errors: string[];
  explanations: Array<Record<string, any>>;
}

export interface EngineDetail {
  manifest: {
    id: string;
    name: string;
    version: string;
    description: string;
    enabled: boolean;
    inputs: string[];
    outputs: string[];
    dependencies: string[];
    triggers: string[];
    supports: Record<string, boolean>;
  };
  health: {
    status: string;
    message: string;
    checked_at: string;
    details: Record<string, any>;
  };
  rules: Record<string, any>;
  total_runs_count: number;
  last_run?: {
    run_id: string;
    status: string;
    started_at: string;
    summary: string;
    duration_ms: number;
  } | null;
}

export interface EngineResult {
  engine_id: string;
  engine_version: string;
  run_id: string;
  success: boolean;
  started_at: string;
  ended_at: string;
  duration_ms: number;
  input_count: number;
  output_count: number;
  rejected_count: number;
  error_count: number;
  cost: number;
  summary: string;
  outputs: any[];
  errors: string[];
  explanations: any[];
}

export interface EngineExplanation {
  result_id: string;
  summary: string;
  factors: Array<Record<string, any>>;
}

export async function getEngines(): Promise<EngineSummary[]> {
  return await request<EngineSummary[]>("/api/v1/engines", { cache: "no-store" });
}

export async function getEngineDetail(id: string): Promise<EngineDetail> {
  return await request<EngineDetail>(`/api/v1/engines/${id}`, { cache: "no-store" });
}

export async function runEngine(id: string, params: Record<string, any> = {}): Promise<EngineResult> {
  return await request<EngineResult>(`/api/v1/engines/${id}/run`, {
    method: "POST",
    body: JSON.stringify({ parameters: params }),
  });
}

export async function dryRunEngine(id: string, params: Record<string, any> = {}): Promise<EngineResult> {
  return await request<EngineResult>(`/api/v1/engines/${id}/dry-run`, {
    method: "POST",
    body: JSON.stringify({ parameters: params }),
  });
}

export async function getEngineRules(id: string): Promise<Record<string, any>> {
  return await request<Record<string, any>>(`/api/v1/engines/${id}/rules`, { cache: "no-store" });
}

export async function updateEngineRules(id: string, rules: Record<string, any>): Promise<Record<string, any>> {
  return await request<Record<string, any>>(`/api/v1/engines/${id}/rules`, {
    method: "PUT",
    body: JSON.stringify({ rules }),
  });
}

export async function getEngineRuns(id: string, limit: number = 20): Promise<EngineRunRecord[]> {
  return await request<EngineRunRecord[]>(`/api/v1/engines/${id}/runs?limit=${limit}`, { cache: "no-store" });
}

export async function explainEngineResult(id: string, resultId: string): Promise<EngineExplanation> {
  return await request<EngineExplanation>(`/api/v1/engines/${id}/explain/${resultId}`, { cache: "no-store" });
}

