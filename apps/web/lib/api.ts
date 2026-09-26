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
