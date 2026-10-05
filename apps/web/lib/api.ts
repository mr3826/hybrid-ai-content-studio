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
  default_lead_magnet?: string | null;
  newsletter_cta?: string | null;
  digital_product_cta?: string | null;
  visual_identity: Record<string, any>;
  platform_adaptations: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface BrandMemoryItem {
  id: string;
  memory_type: string;
  content: string;
  context_metadata?: Record<string, any>;
  usage_count: number;
  last_used_at: string;
  created_at: string;
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

// Brand Memory
export async function getBrandMemory(memory_type?: string): Promise<BrandMemoryItem[]> {
  const q = memory_type ? `?memory_type=${encodeURIComponent(memory_type)}` : "";
  return await request<BrandMemoryItem[]>(`/api/v1/brand/memory${q}`, { cache: "no-store" });
}

export async function recordBrandMemory(data: {
  memory_type: string;
  content: string;
  context_metadata?: Record<string, any>;
}): Promise<BrandMemoryItem> {
  return await request<BrandMemoryItem>("/api/v1/brand/memory", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteBrandMemory(id: string): Promise<void> {
  await request<void>(`/api/v1/brand/memory/${id}`, {
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

// Niche Guard & Brand QA Evaluation Contracts
export interface NicheGuardInput {
  id?: string;
  title: string;
  text: string;
  tags?: string[];
  url?: string;
}

export interface NicheGuardFactor {
  criterion: string;
  points: number;
  detail: string;
  matched_items: string[];
}

export interface NicheGuardVerdict {
  id: string;
  input_id?: string;
  passed: boolean;
  score: number;
  reason: string;
  primary_pillar?: string | null;
  is_adjacent?: boolean;
  is_blocked?: boolean;
  audience_relevance?: number;
  pillar_matches: string[];
  matched_allowed_topics: string[];
  matched_adjacent_topics: string[];
  matched_must_have_signals: string[];
  matched_negative_keywords: string[];
  blocked_topics_detected: string[];
  factors: NicheGuardFactor[];
  evaluated_at: string;
}

export interface BrandViolation {
  rule_type: string;
  severity: "critical" | "warning" | "suggestion";
  matched_phrase: string;
  message: string;
  suggestion: string;
}

export interface BrandQAInput {
  id?: string;
  title?: string;
  body: string;
  hook?: string;
  cta?: string;
  platform?: string;
}

export interface BrandQAVerdict {
  id: string;
  input_id?: string;
  on_brand: boolean;
  overall_score: number;
  tone_score: number;
  vocabulary_score: number;
  repetition_score: number;
  audience_fit_score?: number;
  cta_fit_score?: number;
  platform_fit_score?: number;
  dimensions?: Record<string, number>;
  cliche_score: number;
  claim_score: number;
  repetition_warnings?: string[];
  matched_memory_items?: Array<Record<string, any>>;
  violations: BrandViolation[];
  matched_preferred_words: string[];
  matched_avoid_words: string[];
  matched_cliches: string[];
  suggested_fixes: string[];
  exemplar_matches: Array<Record<string, any>>;
  factors: Array<Record<string, any>>;
  evaluated_at: string;
}

export async function evaluateNicheGuard(payload: NicheGuardInput): Promise<NicheGuardVerdict> {
  return await request<NicheGuardVerdict>("/api/v1/niche-guard/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function evaluateBrandQA(payload: BrandQAInput): Promise<BrandQAVerdict> {
  return await request<BrandQAVerdict>("/api/v1/brand-qa/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------------------------
// Phase 4: RSS Discovery Engine Contracts & Client APIs
// ---------------------------------------------------------------------------

export interface RssFeed {
  id: string;
  name: string;
  url: string;
  category: string;
  trust_weight: number;
  enabled: boolean;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  failure_count: number;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CandidateSourceInfo {
  feed_id?: string | null;
  feed_name: string;
  url: string;
  trust_weight: number;
  published_at: string;
}

export interface DiscoveredCandidate {
  id: string;
  canonical_url: string;
  title: string;
  normalized_title: string;
  summary: string;
  content_fingerprint: string;
  primary_source: string;
  published_at: string;
  first_seen_at: string;
  last_seen_at: string;
  source_count: number;
  sources: CandidateSourceInfo[];
  authority_score: number;
  pillar?: string | null;
  niche_score: number;
  is_in_niche: boolean;
  niche_verdict: Record<string, any>;
  status: "candidate" | "rejected" | "promoted_to_opportunity" | string;
  created_at: string;
  updated_at: string;
}

export interface RssRunResponse {
  engine_result: {
    engine_id: string;
    engine_version: string;
    rules_version: string;
    run_id: string;
    success: boolean;
    duration_ms: number;
    input_count: number;
    output_count: number;
    rejected_count: number;
    error_count: number;
    cost: number;
    summary: string;
    outputs: DiscoveredCandidate[];
    errors: string[];
    explanations: Array<Record<string, any>>;
  };
  explanation: {
    result_id: string;
    summary: string;
    factors: Array<{ factor: string; value: any }>;
  };
}

export async function listRssFeeds(enabledOnly: boolean = false): Promise<RssFeed[]> {
  const query = enabledOnly ? "?enabled_only=true" : "";
  return await request<RssFeed[]>(`/api/v1/rss/feeds${query}`);
}

export async function createRssFeed(payload: {
  name: string;
  url: string;
  category?: string;
  trust_weight?: number;
  enabled?: boolean;
}): Promise<RssFeed> {
  return await request<RssFeed>("/api/v1/rss/feeds", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateRssFeed(
  id: string,
  payload: Partial<RssFeed>
): Promise<RssFeed> {
  return await request<RssFeed>(`/api/v1/rss/feeds/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteRssFeed(id: string): Promise<void> {
  await request<void>(`/api/v1/rss/feeds/${id}`, {
    method: "DELETE",
  });
}

export async function runRssDiscovery(
  parameters: Record<string, any> = {}
): Promise<RssRunResponse> {
  return await request<RssRunResponse>("/api/v1/rss/run", {
    method: "POST",
    body: JSON.stringify(parameters),
  });
}

export async function dryRunRssDiscovery(
  parameters: Record<string, any> = {}
): Promise<RssRunResponse> {
  return await request<RssRunResponse>("/api/v1/rss/dry-run", {
    method: "POST",
    body: JSON.stringify(parameters),
  });
}

export async function listDiscoveredCandidates(params?: {
  status?: string;
  pillar?: string;
  in_niche_only?: boolean;
  limit?: number;
}): Promise<DiscoveredCandidate[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.pillar) searchParams.set("pillar", params.pillar);
  if (params?.in_niche_only) searchParams.set("in_niche_only", "true");
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return await request<DiscoveredCandidate[]>(`/api/v1/rss/candidates${qs}`);
}

export async function getDiscoveredCandidate(
  id: string
): Promise<DiscoveredCandidate> {
  return await request<DiscoveredCandidate>(`/api/v1/rss/candidates/${id}`);
}

// ---------------------------------------------------------
// Trends Engine Contracts & API
// ---------------------------------------------------------

export interface TrendScoreBreakdown {
  base_mentions_score: number;
  source_diversity_score: number;
  source_authority_score: number;
  recency_score: number;
  velocity_score: number;
  baseline_ratio: number;
  manual_boost: number;
  is_suppressed: boolean;
  raw_score: number;
  final_score: number;
}

export interface TrendExplanation {
  topic_key: string;
  title: string;
  summary: string;
  mentions_text: string;
  sources_text: string;
  recency_text: string;
  baseline_text: string;
  velocity_text: string;
  breakdown: TrendScoreBreakdown;
}

export interface TrendHistoryItem {
  id: string;
  topic_id: string;
  recorded_at: string;
  trend_score: number;
  momentum_score: number;
  mention_count: number;
  velocity: number;
  snapshot_data: Record<string, any>;
}

export interface TrendTopic {
  id: string;
  topic_key: string;
  title: string;
  summary: string;
  pillar: string | null;
  keywords: string[];
  trend_score: number;
  momentum_score: number;
  mention_count: number;
  distinct_sources_count: number;
  source_diversity_score: number;
  source_authority_score: number;
  velocity: number;
  velocity_ratio: number;
  historical_baseline: number;
  first_seen_at: string;
  last_seen_at: string;
  manual_boost: number;
  is_suppressed: boolean;
  status: "active" | "emerging" | "cooling" | "archived";
  signal_ids: string[];
  source_breakdown: Array<{
    source_name: string;
    source_type: string;
    trust_weight: number;
    url?: string;
  }>;
  explanation: TrendExplanation;
  history?: TrendHistoryItem[];
  created_at: string;
  updated_at: string;
}

export async function listTrends(params?: {
  status?: string;
  pillar?: string;
  min_score?: number;
  is_suppressed?: boolean;
  sort_by?: "trend_score" | "velocity" | "recency" | "mentions";
  limit?: number;
}): Promise<TrendTopic[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.pillar) searchParams.set("pillar", params.pillar);
  if (params?.min_score !== undefined) searchParams.set("min_score", params.min_score.toString());
  if (params?.is_suppressed !== undefined) searchParams.set("is_suppressed", params.is_suppressed.toString());
  if (params?.sort_by) searchParams.set("sort_by", params.sort_by);
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return await request<TrendTopic[]>(`/api/v1/trends${qs}`);
}

export async function getTrend(id: string): Promise<TrendTopic> {
  return await request<TrendTopic>(`/api/v1/trends/${id}`);
}

export async function getTrendExplain(id: string): Promise<any> {
  return await request<any>(`/api/v1/trends/${id}/explain`);
}

export async function runTrends(parameters: Record<string, any> = {}): Promise<EngineResult> {
  return await request<EngineResult>("/api/v1/trends/run", {
    method: "POST",
    body: JSON.stringify(parameters),
  });
}

export async function dryRunTrends(parameters: Record<string, any> = {}): Promise<EngineResult> {
  return await request<EngineResult>("/api/v1/trends/dry-run", {
    method: "POST",
    body: JSON.stringify(parameters),
  });
}

export async function boostTrend(id: string, boost_factor: number): Promise<TrendTopic> {
  return await request<TrendTopic>(`/api/v1/trends/${id}/boost`, {
    method: "POST",
    body: JSON.stringify({ boost_factor }),
  });
}

export async function suppressTrend(id: string, suppress: boolean): Promise<TrendTopic> {
  return await request<TrendTopic>(`/api/v1/trends/${id}/suppress`, {
    method: "POST",
    body: JSON.stringify({ suppress }),
  });
}

export async function createManualSignal(payload: {
  title: string;
  source_name?: string;
  summary?: string;
  url?: string;
  pillar?: string;
  trust_weight?: number;
}): Promise<TrendTopic> {
  return await request<TrendTopic>("/api/v1/trends/manual-signal", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------
// Opportunity Intelligence & Creator Cockpit Contracts & API
// ---------------------------------------------------------

export interface OpportunityScoreBreakdown {
  niche_fit: number;
  original_value: number;
  audience_usefulness: number;
  evergreen_value: number;
  trend_momentum: number;
  commercial_fit: number;
  content_family_potential: number;
  sponsor_relevance: number;
  production_effort_score: number;
  saturation_penalty: number;
  raw_score: number;
  final_score: number;
}

export interface Opportunity {
  id: string;
  topic: string;
  slug: string;
  candidate_id?: string | null;
  trend_id?: string | null;
  pillar?: string | null;
  status: "needs_review" | "watching" | "rejected" | "approved" | "research_ready" | "in_production" | "ready_to_publish" | "published";
  opportunity_score: number;
  trend_score: number;
  niche_fit_score: number;
  originality_potential: number;
  audience_usefulness: number;
  evergreen_value: number;
  commercial_fit: number;
  content_family_potential: number;
  sponsor_relevance: number;
  saturation_penalty: number;
  production_effort: "low" | "medium" | "high";
  estimated_cost: number;
  estimated_time_minutes: number;
  suggested_original_angle: string;
  suggested_content_family: string;
  risks: string[];
  why: string;
  recommended_action: "Research" | "Watch" | "Reject";
  score_breakdown: OpportunityScoreBreakdown;
  source_references: Array<Record<string, any>>;
  rejection_reason?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CockpitSummary {
  signals_today: number;
  needs_review: number;
  watching: number;
  research_ready: number;
  in_production: number;
  ready_to_publish: number;
  published: number;
  ai_spend: number;
  disk_usage: {
    database_bytes: number;
    database_mb: number;
    media_bytes: number;
    media_mb: number;
  };
  top_opportunities: Opportunity[];
  engine_health_summary: Array<{
    id: string;
    name: string;
    status: string;
    message: string;
  }>;
}

export async function listOpportunities(params?: {
  status?: string;
  pillar?: string;
  min_score?: number;
  content_family?: string;
  sort_by?: "opportunity_score" | "trend_score" | "originality" | "recency";
  limit?: number;
}): Promise<Opportunity[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.pillar) searchParams.set("pillar", params.pillar);
  if (params?.min_score !== undefined) searchParams.set("min_score", params.min_score.toString());
  if (params?.content_family) searchParams.set("content_family", params.content_family);
  if (params?.sort_by) searchParams.set("sort_by", params.sort_by);
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return await request<Opportunity[]>(`/api/v1/opportunities${qs}`);
}

export async function getOpportunity(id: string): Promise<Opportunity> {
  return await request<Opportunity>(`/api/v1/opportunities/${id}`);
}

export async function getOpportunityExplain(id: string): Promise<any> {
  return await request<any>(`/api/v1/opportunities/${id}/explain`);
}

export async function runOpportunities(parameters: Record<string, any> = {}): Promise<EngineResult> {
  return await request<EngineResult>("/api/v1/opportunities/run", {
    method: "POST",
    body: JSON.stringify(parameters),
  });
}

export async function dryRunOpportunities(parameters: Record<string, any> = {}): Promise<EngineResult> {
  return await request<EngineResult>("/api/v1/opportunities/dry-run", {
    method: "POST",
    body: JSON.stringify(parameters),
  });
}

export async function approveOpportunityResearch(id: string): Promise<Opportunity> {
  return await request<Opportunity>(`/api/v1/opportunities/${id}/research`, {
    method: "POST",
  });
}

export async function watchOpportunity(id: string): Promise<Opportunity> {
  return await request<Opportunity>(`/api/v1/opportunities/${id}/watch`, {
    method: "POST",
  });
}

export async function rejectOpportunity(id: string, rejection_reason?: string): Promise<Opportunity> {
  return await request<Opportunity>(`/api/v1/opportunities/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ rejection_reason }),
  });
}

export async function getCockpitSummary(): Promise<CockpitSummary> {
  return await request<CockpitSummary>("/api/v1/opportunities/cockpit/summary");
}

export interface SourceReference {
  url: string;
  title: string;
  domain: string;
  excerpt?: string;
  trust_weight: number;
  published_at?: string | null;
}

export interface FactItem {
  id: string;
  text: string;
  source_url: string;
  source_title?: string | null;
  confidence: number;
}

export interface NumberMetric {
  id: string;
  metric: string;
  value: string;
  unit?: string | null;
  context: string;
  source_url: string;
}

export interface DateItem {
  id: string;
  event: string;
  date_str: string;
  source_url: string;
}

export interface EntityItem {
  id: string;
  name: string;
  type: string;
  relevance: number;
  source_url?: string | null;
}

export interface ClaimItem {
  id: string;
  claim_text: string;
  verification_status: "source-backed" | "explicitly_uncertain" | "manually_entered";
  evidence_quote?: string | null;
  source_url?: string | null;
  uncertainty_reason?: string | null;
  confidence: number;
}

export interface ContradictionItem {
  id: string;
  claim_a: string;
  source_a: string;
  claim_b: string;
  source_b: string;
  conflict_summary: string;
}

export interface UncertainClaimItem {
  id: string;
  claim_text: string;
  uncertainty_reason: string;
}

export interface ThingNotToClaimItem {
  id: string;
  claim_text: string;
  reason_to_avoid: string;
  flagged_source?: string | null;
}

export interface ResearchRevision {
  id: string;
  packet_id: string;
  revision_number: number;
  changed_by: string;
  change_summary: string;
  snapshot: Record<string, any>;
  created_at: string;
}

export interface ResearchPacket {
  id: string;
  opportunity_id?: string | null;
  topic: string;
  slug: string;
  summary: string;
  primary_sources: SourceReference[];
  supporting_sources: SourceReference[];
  facts: FactItem[];
  numbers: NumberMetric[];
  dates: DateItem[];
  entities: EntityItem[];
  claims: ClaimItem[];
  contradictions: ContradictionItem[];
  uncertain_claims: UncertainClaimItem[];
  things_not_to_claim: ThingNotToClaimItem[];
  version: number;
  is_verified: boolean;
  verified_at?: string | null;
  verified_by?: string | null;
  revisions?: ResearchRevision[];
  created_at: string;
  updated_at: string;
}

export async function listResearchPackets(params?: {
  opportunity_id?: string;
  is_verified?: boolean;
  search?: string;
  limit?: number;
}): Promise<ResearchPacket[]> {
  const searchParams = new URLSearchParams();
  if (params?.opportunity_id) searchParams.set("opportunity_id", params.opportunity_id);
  if (params?.is_verified !== undefined) searchParams.set("is_verified", params.is_verified.toString());
  if (params?.search) searchParams.set("search", params.search);
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return await request<ResearchPacket[]>(`/api/v1/research/packets${qs}`);
}

export async function getResearchPacket(id: string): Promise<ResearchPacket> {
  return await request<ResearchPacket>(`/api/v1/research/packets/${id}`);
}

export async function createResearchPacket(payload: {
  opportunity_id?: string;
  topic?: string;
  sources?: any[];
  raw_text?: string;
  context?: string;
}): Promise<ResearchPacket> {
  return await request<ResearchPacket>("/api/v1/research/packets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateResearchPacket(
  id: string,
  updates: Partial<ResearchPacket> & { changed_by?: string; change_summary?: string }
): Promise<ResearchPacket> {
  return await request<ResearchPacket>(`/api/v1/research/packets/${id}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

export async function verifyResearchPacket(id: string): Promise<ResearchPacket> {
  return await request<ResearchPacket>(`/api/v1/research/packets/${id}/verify`, {
    method: "POST",
  });
}

export async function getResearchRevisions(id: string): Promise<ResearchRevision[]> {
  return await request<ResearchRevision[]>(`/api/v1/research/packets/${id}/revisions`);
}

export async function revertResearchRevision(id: string, revisionNumber: number): Promise<ResearchPacket> {
  return await request<ResearchPacket>(`/api/v1/research/packets/${id}/revert/${revisionNumber}`, {
    method: "POST",
  });
}

// ---------------------------------------------------------------------------
// Evidence & Provenance API
// ---------------------------------------------------------------------------

export type ClaimType =
  | "external_fact"
  | "original_measurement"
  | "derived_conclusion"
  | "opinion"
  | "prediction_speculation";

export type VerificationStatus =
  | "verified"
  | "unsupported"
  | "labeled_opinion"
  | "overridden";

export interface EvidenceSource {
  id: string;
  url: string;
  title: string;
  domain: string;
  source_type: "primary" | "supporting" | "experiment";
  trust_weight: number;
  author?: string | null;
  published_at?: string | null;
  created_at: string;
}

export interface Claim {
  id: string;
  packet_id?: string | null;
  text: string;
  claim_type: ClaimType;
  confidence: number;
  is_verified: boolean;
  evidence_count?: number;
  created_at: string;
}

export interface ProvenanceSourceNode {
  source_id?: string | null;
  url: string;
  title: string;
  domain: string;
  source_type: string;
  trust_weight: number;
  quote?: string | null;
  confidence: number;
}

export interface ProvenanceMeasurementNode {
  metric: string;
  value: number;
  unit?: string | null;
  context?: string | null;
}

export interface ProvenanceRunNode {
  run_id: string;
  run_number: number;
  cost_usd: number;
  execution_time_ms: number;
  status: string;
  measurements: ProvenanceMeasurementNode[];
}

export interface ProvenanceExperimentNode {
  experiment_id: string;
  title: string;
  hypothesis: string;
  method: string;
  conclusion_summary?: string | null;
  confidence: number;
  runs: ProvenanceRunNode[];
}

export interface ProvenanceContentUsageNode {
  content_claim_id: string;
  content_id: string;
  section_id: string;
  quote_in_script: string;
  verification_status: VerificationStatus;
  is_overridden: boolean;
  override_reason?: string | null;
}

export interface ProvenanceTrace {
  claim_id: string;
  claim_text: string;
  claim_type: ClaimType;
  is_verified: boolean;
  confidence: number;
  sources: ProvenanceSourceNode[];
  experiments: ProvenanceExperimentNode[];
  content_usages: ProvenanceContentUsageNode[];
}

export interface CoverageReport {
  total_claims: number;
  factual_claims: number;
  primary_source_backed: number;
  supporting_source_backed: number;
  original_test_backed: number;
  opinions_labeled: number;
  overridden_count: number;
  unsupported: number;
  coverage_percent: number;
  gate_passed: boolean;
  explanation?: string | null;
}

export interface Experiment {
  id: string;
  title: string;
  hypothesis: string;
  method: string;
  opportunity_id?: string | null;
  run_count?: number;
  conclusions_count?: number;
  runs?: any[];
  conclusions?: any[];
  created_at: string;
}

export async function listClaims(params?: {
  packet_id?: string;
  claim_type?: string;
  is_verified?: boolean;
  limit?: number;
}): Promise<Claim[]> {
  const searchParams = new URLSearchParams();
  if (params?.packet_id) searchParams.set("packet_id", params.packet_id);
  if (params?.claim_type) searchParams.set("claim_type", params.claim_type);
  if (params?.is_verified !== undefined) searchParams.set("is_verified", params.is_verified.toString());
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return await request<Claim[]>(`/api/v1/evidence/claims${qs}`);
}

export async function getClaim(claimId: string): Promise<any> {
  return await request<any>(`/api/v1/evidence/claims/${claimId}`);
}

export async function getClaimProvenance(claimId: string): Promise<ProvenanceTrace> {
  return await request<ProvenanceTrace>(`/api/v1/evidence/claims/${claimId}/provenance`);
}

export async function createClaim(payload: {
  text: string;
  claim_type?: ClaimType;
  confidence?: number;
  packet_id?: string;
  is_verified?: boolean;
}): Promise<Claim> {
  return await request<Claim>("/api/v1/evidence/claims", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function linkSourceEvidence(
  claimId: string,
  payload: {
    source_url?: string;
    source_title?: string;
    source_type?: string;
    trust_weight?: number;
    quote: string;
    confidence?: number;
    notes?: string;
  }
): Promise<any> {
  return await request<any>(`/api/v1/evidence/claims/${claimId}/link-source`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function labelClaimOpinion(
  claimId: string,
  claimType: "opinion" | "prediction_speculation" = "opinion"
): Promise<any> {
  return await request<any>(`/api/v1/evidence/claims/${claimId}/label-opinion`, {
    method: "POST",
    body: JSON.stringify({ claim_type: claimType }),
  });
}

export async function listExperiments(opportunityId?: string): Promise<Experiment[]> {
  const qs = opportunityId ? `?opportunity_id=${encodeURIComponent(opportunityId)}` : "";
  return await request<Experiment[]>(`/api/v1/evidence/experiments${qs}`);
}

export async function getExperiment(experimentId: string): Promise<any> {
  return await request<any>(`/api/v1/evidence/experiments/${experimentId}`);
}

export async function createExperiment(payload: {
  title: string;
  hypothesis: string;
  method: string;
  opportunity_id?: string;
  tools_models?: string[];
  parameters?: Record<string, any>;
}): Promise<Experiment> {
  return await request<Experiment>("/api/v1/evidence/experiments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function addExperimentRun(
  experimentId: string,
  payload: {
    run_number?: number;
    execution_time_ms?: number;
    cost_usd?: number;
    status?: string;
    error_message?: string;
    measurements?: Array<{
      metric: string;
      value: number;
      unit?: string;
      context?: string;
    }>;
  }
): Promise<any> {
  return await request<any>(`/api/v1/evidence/experiments/${experimentId}/runs`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function addConclusion(
  experimentId: string,
  payload: {
    summary: string;
    claim_id?: string;
    confidence?: number;
  }
): Promise<any> {
  return await request<any>(`/api/v1/evidence/experiments/${experimentId}/conclusions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getEvidenceCoverage(params?: {
  packet_id?: string;
  content_id?: string;
}): Promise<CoverageReport> {
  const searchParams = new URLSearchParams();
  if (params?.packet_id) searchParams.set("packet_id", params.packet_id);
  if (params?.content_id) searchParams.set("content_id", params.content_id);
  const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return await request<CoverageReport>(`/api/v1/evidence/coverage${qs}`, {
    method: "POST",
  });
}

export async function overrideContentClaim(
  contentClaimId: string,
  reason: string
): Promise<any> {
  return await request<any>(`/api/v1/evidence/content-claims/${contentClaimId}/override`, {
    method: "POST",
    body: JSON.stringify({ override_reason: reason }),
  });
}

// ---------------------------------------------------------------------------
// AI Provider Engine Contracts & APIs (Phase 9)
// ---------------------------------------------------------------------------

export interface AIProviderStatus {
  mock_mode: boolean;
  primary_provider: string;
  primary_configured: boolean;
  primary_model: string;
  fallback_provider: string;
  fallback_configured: boolean;
  fallback_model: string;
  fallback_enabled: boolean;
  daily_spend_today: number;
  daily_budget_limit: number;
  budget_exceeded: boolean;
}

export interface AIResponse {
  text: string;
  structured_data?: any;
  provider: string;
  model: string;
  task: string;
  prompt_version?: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost: number;
  latency_ms: number;
  success: boolean;
  error_message?: string;
  fallback_used: boolean;
  fallback_reason?: string;
  primary_provider?: string;
  primary_error?: string;
}

export interface AIInvocationLog {
  id: string;
  provider: string;
  model: string;
  task: string;
  prompt_version: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost: number;
  latency_ms: number;
  success: boolean;
  error_message?: string;
  fallback_used: boolean;
  fallback_reason?: string;
  primary_provider?: string;
  primary_error?: string;
  prompt_hash?: string;
  created_at: string;
}

export interface AIAnalyticsSummary {
  period_days: number;
  total_calls: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  fallback_count: number;
  fallback_rate: number;
  total_cost: number;
  daily_spend_today: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  avg_latency_ms: number;
  provider_breakdown: Array<{ provider: string; calls: number; cost: number; tokens: number }>;
  task_breakdown: Array<{ task: string; calls: number; cost: number }>;
}

export async function getAIStatus(): Promise<AIProviderStatus> {
  return await request<AIProviderStatus>("/api/v1/ai/status");
}

export async function generateAIText(payload: {
  prompt: string;
  system_prompt?: string;
  task?: string;
  temperature?: number;
  max_tokens?: number;
  preferred_provider?: string;
  allow_fallback?: boolean;
  simulate_failure?: string;
}): Promise<AIResponse> {
  return await request<AIResponse>("/api/v1/ai/generate-text", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function generateAIStructured(payload: {
  prompt: string;
  response_schema: Record<string, any>;
  system_prompt?: string;
  task?: string;
  temperature?: number;
  preferred_provider?: string;
  allow_fallback?: boolean;
  simulate_failure?: string;
}): Promise<AIResponse> {
  return await request<AIResponse>("/api/v1/ai/generate-structured", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function analyzeAIContent(payload: {
  content: string;
  instruction: string;
  criteria?: string[];
  task?: string;
  preferred_provider?: string;
  allow_fallback?: boolean;
  simulate_failure?: string;
}): Promise<AIResponse> {
  return await request<AIResponse>("/api/v1/ai/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAILogs(params?: {
  limit?: number;
  offset?: number;
  provider?: string;
  task?: string;
  success?: boolean;
  fallback_used?: boolean;
}): Promise<AIInvocationLog[]> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.offset) searchParams.set("offset", params.offset.toString());
  if (params?.provider) searchParams.set("provider", params.provider);
  if (params?.task) searchParams.set("task", params.task);
  if (params?.success !== undefined) searchParams.set("success", params.success.toString());
  if (params?.fallback_used !== undefined) searchParams.set("fallback_used", params.fallback_used.toString());
  const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return await request<AIInvocationLog[]>(`/api/v1/ai/logs${qs}`);
}

export async function getAIAnalytics(days: number = 30): Promise<AIAnalyticsSummary> {
  return await request<AIAnalyticsSummary>(`/api/v1/ai/analytics?days=${days}`);
}

// ---------------------------------------------------------------------------
// Originality & Experiment Workspace (Phase 10)
// ---------------------------------------------------------------------------

export interface OriginalityFormat {
  type: string;
  title: string;
  description: string;
}

export interface OriginalityAngle {
  originality_type: string;
  what_are_we_adding: string;
  why_it_matters: string;
  suggested_experiments: Array<{ title: string; method: string }>;
}

export interface ExperimentAttachment {
  id: string;
  experiment_id?: string;
  attachment_type: string;
  filename: string;
  file_path: string;
  mime_type: string;
  size_bytes: number;
  content_snippet?: string;
  caption?: string;
  created_at?: string;
}

export interface ExperimentConclusion {
  id: string;
  summary: string;
  confidence: number;
  claim_id?: string;
}

export interface ExperimentItem {
  id: string;
  title: string;
  question?: string;
  hypothesis: string;
  method: string;
  dataset_sample?: string;
  tools_models: string[];
  parameters?: Record<string, any>;
  results?: Record<string, any>;
  failures: string[];
  latency_ms?: number;
  cost_usd?: number;
  notes?: string;
  conclusion?: string;
  status: string;
  opportunity_id?: string;
  originality_plan_id?: string;
  attachment_count?: number;
  attachments?: ExperimentAttachment[];
  conclusions?: ExperimentConclusion[];
  created_at?: string;
}

export interface OriginalityPlan {
  id: string;
  topic: string;
  slug: string;
  originality_type: string;
  what_are_we_adding: string;
  why_it_matters?: string;
  status: string;
  is_generic_summary: boolean;
  confidence_score: number;
  opportunity_id?: string;
  packet_id?: string;
  reviewed_by?: string;
  review_notes?: string;
  reviewed_at?: string;
  suggested_experiments?: Array<Record<string, any>>;
  experiments?: ExperimentItem[];
  created_at?: string;
}

export async function getOriginalityHealth(): Promise<{ status: string; engine_id: string }> {
  return await request<{ status: string; engine_id: string }>("/api/v1/originality/health");
}

export async function getOriginalityFormats(): Promise<{ formats: OriginalityFormat[]; count: number }> {
  return await request<{ formats: OriginalityFormat[]; count: number }>("/api/v1/originality/formats");
}

export async function proposeOriginalAngles(
  topic: string,
  summary: string = ""
): Promise<{ topic: string; angles: OriginalityAngle[] }> {
  return await request<{ topic: string; angles: OriginalityAngle[] }>("/api/v1/originality/propose-angles", {
    method: "POST",
    body: JSON.stringify({ topic, summary }),
  });
}

export async function createOriginalityPlan(payload: {
  topic: string;
  originality_type: string;
  what_are_we_adding: string;
  why_it_matters?: string;
  opportunity_id?: string;
  packet_id?: string;
  suggested_experiments?: any[];
}): Promise<OriginalityPlan> {
  return await request<OriginalityPlan>("/api/v1/originality/plans", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listOriginalityPlans(params?: {
  status?: string;
  originality_type?: string;
  limit?: number;
  offset?: number;
}): Promise<OriginalityPlan[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.originality_type) searchParams.set("originality_type", params.originality_type);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.offset) searchParams.set("offset", params.offset.toString());
  const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return await request<OriginalityPlan[]>(`/api/v1/originality/plans${qs}`);
}

export async function getOriginalityPlan(id: string): Promise<OriginalityPlan> {
  return await request<OriginalityPlan>(`/api/v1/originality/plans/${id}`);
}

export async function approveOriginalityPlan(
  id: string,
  payload?: { reviewer?: string; notes?: string }
): Promise<{ id: string; status: string; reviewed_by: string; review_notes?: string }> {
  return await request<{ id: string; status: string; reviewed_by: string; review_notes?: string }>(
    `/api/v1/originality/plans/${id}/approve`,
    {
      method: "POST",
      body: JSON.stringify(payload || {}),
    }
  );
}

export async function rejectOriginalityPlan(
  id: string,
  reason: string
): Promise<{ id: string; status: string; review_notes: string }> {
  return await request<{ id: string; status: string; review_notes: string }>(
    `/api/v1/originality/plans/${id}/reject`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
    }
  );
}

export async function createWorkspaceExperiment(payload: {
  title: string;
  hypothesis: string;
  method: string;
  question?: string;
  dataset_sample?: string;
  tools_models?: string[];
  parameters?: Record<string, any>;
  results?: Record<string, any>;
  failures?: string[];
  latency_ms?: number;
  cost_usd?: number;
  notes?: string;
  conclusion?: string;
  status?: string;
  opportunity_id?: string;
  originality_plan_id?: string;
}): Promise<ExperimentItem> {
  return await request<ExperimentItem>("/api/v1/originality/experiments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listWorkspaceExperiments(params?: {
  opportunity_id?: string;
  originality_plan_id?: string;
  status?: string;
  limit?: number;
}): Promise<ExperimentItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.opportunity_id) searchParams.set("opportunity_id", params.opportunity_id);
  if (params?.originality_plan_id) searchParams.set("originality_plan_id", params.originality_plan_id);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return await request<ExperimentItem[]>(`/api/v1/originality/experiments${qs}`);
}

export async function getWorkspaceExperiment(id: string): Promise<ExperimentItem> {
  return await request<ExperimentItem>(`/api/v1/originality/experiments/${id}`);
}

export async function addExperimentAttachment(
  id: string,
  payload: {
    attachment_type: string;
    filename: string;
    file_path: string;
    mime_type?: string;
    size_bytes?: number;
    content_snippet?: string;
    caption?: string;
  }
): Promise<ExperimentAttachment> {
  return await request<ExperimentAttachment>(`/api/v1/originality/experiments/${id}/attachments`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function linkExperimentEvidence(
  id: string,
  payload: {
    conclusion_text: string;
    claim_id?: string;
    confidence?: number;
  }
): Promise<ExperimentConclusion> {
  return await request<ExperimentConclusion>(`/api/v1/originality/experiments/${id}/link-evidence`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------------------------
// Content Family Engine (Phase 11)
// ---------------------------------------------------------------------------

export interface ContentChildItemEvidence {
  id: string;
  claim_id: string;
  relevance_note?: string;
  is_primary: boolean;
  claim_text: string;
  claim_type: string;
  is_verified: boolean;
}

export interface ContentChildItem {
  id: string;
  content_family_id: string;
  family_title?: string;
  format: string;
  platform_target: string;
  working_title: string;
  angle: string;
  hook_type: string;
  status: string;
  incremental_cost: number;
  manual_time_minutes: number;
  local_compute_seconds: number;
  original_value_connection: string;
  viewer_value: string;
  evidence_count?: number;
  evidence_selections?: ContentChildItemEvidence[];
  created_at?: string;
  approved_at?: string;
}

export interface ContentFamilyEconomics {
  family_id?: string;
  item_count: number;
  shared_family_cost: number;
  shared_manual_time_minutes: number;
  shared_compute_seconds: number;
  total_incremental_cost: number;
  total_family_cost: number;
  cost_per_child: number;
  total_time_minutes: number;
  total_compute_seconds: number;
  roi_ratio: number;
}

export interface ContentFamilyItem {
  id: string;
  title: string;
  slug: string;
  status: string;
  content_pillar: string;
  original_value_type: string;
  summary: string;
  topic_id?: string;
  research_packet_id?: string;
  originality_plan_id?: string;
  primary_experiment_id?: string;
  item_count: number;
  shared_cost: number;
  created_at?: string;
  approved_at?: string;
}

export interface ContentFamilyDetail extends ContentFamilyItem {
  research_cost: number;
  experiment_cost: number;
  ai_cost: number;
  media_cost: number;
  manual_time_minutes: number;
  local_compute_seconds: number;
  economics: ContentFamilyEconomics;
  items: ContentChildItem[];
  updated_at?: string;
  archived_at?: string;
}

export interface ChildSuggestionProposal {
  format: string;
  platform_target: string;
  working_title: string;
  angle: string;
  hook_type: string;
  evidence_focus: string[];
  original_value_connection: string;
  viewer_value: string;
}

export interface SuggestChildrenResponse {
  family_title: string;
  proposals: ChildSuggestionProposal[];
  brand_applied: string;
  pillar_applied: string;
}

export async function getContentFamilyHealth(): Promise<{ status: string; engine_id: string }> {
  return await request<{ status: string; engine_id: string }>("/api/v1/content-families/health");
}

export async function listContentFamilies(params?: {
  status?: string;
  content_pillar?: string;
  topic_id?: string;
  limit?: number;
  offset?: number;
}): Promise<ContentFamilyItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.content_pillar) searchParams.set("content_pillar", params.content_pillar);
  if (params?.topic_id) searchParams.set("topic_id", params.topic_id);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.offset) searchParams.set("offset", params.offset.toString());
  const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return await request<ContentFamilyItem[]>(`/api/v1/content-families${qs}`);
}

export async function getContentFamily(id: string): Promise<ContentFamilyDetail> {
  return await request<ContentFamilyDetail>(`/api/v1/content-families/${id}`);
}

export async function createContentFamily(payload: {
  title: string;
  content_pillar?: string;
  original_value_type?: string;
  summary?: string;
  topic_id?: string;
  research_packet_id?: string;
  originality_plan_id?: string;
  primary_experiment_id?: string;
  research_cost?: number;
  experiment_cost?: number;
  ai_cost?: number;
  media_cost?: number;
  manual_time_minutes?: number;
  local_compute_seconds?: number;
}): Promise<ContentFamilyItem> {
  return await request<ContentFamilyItem>("/api/v1/content-families", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateContentFamily(
  id: string,
  payload: Record<string, any>
): Promise<{ id: string; title: string; status: string }> {
  return await request<{ id: string; title: string; status: string }>(`/api/v1/content-families/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function approveContentFamily(
  id: string,
  payload?: { reviewer?: string }
): Promise<{ id: string; status: string; approved_at?: string }> {
  return await request<{ id: string; status: string; approved_at?: string }>(
    `/api/v1/content-families/${id}/approve`,
    {
      method: "POST",
      body: JSON.stringify(payload || {}),
    }
  );
}

export async function archiveContentFamily(id: string): Promise<{ id: string; status: string; archived_at?: string }> {
  return await request<{ id: string; status: string; archived_at?: string }>(
    `/api/v1/content-families/${id}/archive`,
    {
      method: "POST",
    }
  );
}

export async function suggestContentFamilyItems(familyId: string): Promise<SuggestChildrenResponse> {
  return await request<SuggestChildrenResponse>(`/api/v1/content-families/${familyId}/suggest-items`, {
    method: "POST",
  });
}

export async function listFamilyItems(
  familyId: string,
  params?: {
    status?: string;
    format?: string;
    platform_target?: string;
  }
): Promise<ContentChildItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.format) searchParams.set("format", params.format);
  if (params?.platform_target) searchParams.set("platform_target", params.platform_target);
  const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return await request<ContentChildItem[]>(`/api/v1/content-families/${familyId}/items${qs}`);
}

export async function createFamilyItem(
  familyId: string,
  payload: {
    format: string;
    working_title: string;
    angle: string;
    platform_target?: string;
    hook_type?: string;
    status?: string;
    incremental_cost?: number;
    manual_time_minutes?: number;
    local_compute_seconds?: number;
    original_value_connection?: string;
    viewer_value?: string;
    claim_ids?: string[];
  }
): Promise<ContentChildItem> {
  return await request<ContentChildItem>(`/api/v1/content-families/${familyId}/items`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getContentItem(itemId: string): Promise<ContentChildItem> {
  return await request<ContentChildItem>(`/api/v1/content-items/${itemId}`);
}

export async function updateContentItem(
  itemId: string,
  payload: Record<string, any>
): Promise<{ id: string; working_title: string; status: string; format: string }> {
  return await request<{ id: string; working_title: string; status: string; format: string }>(
    `/api/v1/content-items/${itemId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
}

export async function deleteContentItem(itemId: string): Promise<{ id: string; deleted: boolean }> {
  return await request<{ id: string; deleted: boolean }>(`/api/v1/content-items/${itemId}`, {
    method: "DELETE",
  });
}

export async function linkChildEvidence(
  itemId: string,
  payload: {
    claim_id: string;
    relevance_note?: string;
    is_primary?: boolean;
  }
): Promise<ContentChildItemEvidence> {
  return await request<ContentChildItemEvidence>(`/api/v1/content-items/${itemId}/evidence`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function unlinkChildEvidence(
  itemId: string,
  claimId: string
): Promise<{ content_item_id: string; claim_id: string; unlinked: boolean }> {
  return await request<{ content_item_id: string; claim_id: string; unlinked: boolean }>(
    `/api/v1/content-items/${itemId}/evidence/${claimId}`,
    {
      method: "DELETE",
    }
  );
}



// ────────────────────────────────────────────────────────────────────────────
// Script Studio (Phase 12)
// ────────────────────────────────────────────────────────────────────────────

export interface ScriptSectionDetail {
  id: string;
  section_type: string;
  order_index: number;
  heading: string;
  narration: string;
  visual_cue: string;
  estimated_seconds: number;
  word_count: number;
  linked_claim_ids: string[];
}

export interface ScriptRevisionSummary {
  id: string;
  revision_number: number;
  trigger: string;
  notes: string;
  created_at: string;
}

export interface DimensionCheckResult {
  dimension: string;
  score: number;
  passed: boolean;
  is_blocking: boolean;
  notes: string;
  flags: string[];
}

export interface ScriptQualityVerdict {
  is_approvable: boolean;
  blocking_reasons: string[];
  dimension_scores: Record<string, DimensionCheckResult>;
  summary: string;
}

export interface ScriptDraft {
  id: string;
  content_item_id: string;
  version: number;
  format: string;
  title: string;
  target_platform: string;
  target_duration_sec: number;
  total_word_count: number;
  estimated_duration_sec: number;
  status: string;
  is_approved: boolean;
  approved_by: string | null;
  approved_at: string | null;
  override_reason: string | null;
  quality_scores: ScriptQualityVerdict | null;
  sections: ScriptSectionDetail[];
  revisions: ScriptRevisionSummary[];
}

export type RefinementType = "shorten" | "expand" | "make_clearer" | "more_evidence" | "regenerate";

export interface SectionRefineResult {
  section_id: string;
  new_narration: string;
  new_visual_cue: string;
  word_count: number;
  estimated_seconds: number;
  explanation: string;
}

export async function generateScriptDraft(
  contentItemId: string,
  targetDurationSec?: number,
  guidance?: string
): Promise<ScriptDraft> {
  return await request<ScriptDraft>("/api/v1/scripts/generate", {
    method: "POST",
    body: JSON.stringify({
      content_item_id: contentItemId,
      target_duration_sec: targetDurationSec,
      guidance,
    }),
  });
}

export async function getScript(scriptId: string): Promise<ScriptDraft> {
  return await request<ScriptDraft>(`/api/v1/scripts/${scriptId}`);
}

export async function getScriptByItem(itemId: string): Promise<ScriptDraft | null> {
  try {
    return await request<ScriptDraft>(`/api/v1/scripts/item/${itemId}`);
  } catch {
    return null;
  }
}

export async function updateScriptSection(
  scriptId: string,
  sectionId: string,
  payload: {
    heading?: string;
    narration?: string;
    visual_cue?: string;
    linked_claim_ids?: string[];
  }
): Promise<ScriptDraft> {
  return await request<ScriptDraft>(
    `/api/v1/scripts/${scriptId}/sections/${sectionId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
}

export async function refineScriptSection(
  scriptId: string,
  sectionId: string,
  refinementType: RefinementType,
  guidance?: string
): Promise<{ refinement: SectionRefineResult; script: ScriptDraft }> {
  return await request<{ refinement: SectionRefineResult; script: ScriptDraft }>(
    `/api/v1/scripts/${scriptId}/sections/${sectionId}/refine`,
    {
      method: "POST",
      body: JSON.stringify({
        refinement_type: refinementType,
        guidance,
      }),
    }
  );
}

export async function checkScriptQuality(scriptId: string): Promise<ScriptQualityVerdict> {
  return await request<ScriptQualityVerdict>(
    `/api/v1/scripts/${scriptId}/quality-check`,
    { method: "POST" }
  );
}

export async function approveScript(
  scriptId: string,
  reviewer: string,
  overrideReason?: string
): Promise<ScriptDraft> {
  return await request<ScriptDraft>(
    `/api/v1/scripts/${scriptId}/approve`,
    {
      method: "POST",
      body: JSON.stringify({
        reviewer,
        override_reason: overrideReason,
      }),
    }
  );
}

export async function getScriptRevisions(scriptId: string): Promise<ScriptRevisionSummary[]> {
  return await request<ScriptRevisionSummary[]>(
    `/api/v1/scripts/${scriptId}/revisions`
  );
}

export async function restoreScriptRevision(
  scriptId: string,
  revisionId: string
): Promise<ScriptDraft> {
  return await request<ScriptDraft>(
    `/api/v1/scripts/${scriptId}/revisions/${revisionId}/restore`,
    { method: "POST" }
  );
}

// -----------------------------------------------------------------------------
// Phase 13: Export & Publishing Assistant
// -----------------------------------------------------------------------------

export interface ExportPackageData {
  id: string;
  content_item_id: string;
  package_slug: string;
  export_dir: string;
  manifest_data: Record<string, any>;
  files: string[];
  checksum: string;
  created_at: string;
  updated_at: string;
}

export interface PlatformPublicationData {
  id: string;
  content_item_id: string;
  export_package_id?: string;
  platform: "youtube" | "facebook" | "instagram" | "tiktok" | string;
  status: "NOT_READY" | "READY" | "PUBLISHED" | "SKIPPED";
  title: string;
  caption: string;
  hashtags: string[];
  pinned_comment: string;
  checklist: {
    media_ready?: boolean;
    thumbnail_ready?: boolean;
    title_caption_ready?: boolean;
    sources_checked?: boolean;
    affiliate_disclosure_needed?: boolean;
    ai_disclosure_recommended?: boolean;
    asset_rights_verified?: boolean;
    [key: string]: boolean | undefined;
  };
  published_at?: string;
  post_url?: string;
  platform_post_id?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface PublishingOverview {
  content_item: {
    id: string;
    content_family_id: string;
    working_title: string;
    format: string;
    platform_target: string;
    status: string;
    hook_type: string;
    angle: string;
    viewer_value: string;
  };
  export_package?: ExportPackageData;
  publications: PlatformPublicationData[];
  platform_launch_urls: Record<string, string>;
}

export interface PublishableItemSummary {
  id: string;
  working_title: string;
  format: string;
  platform_target: string;
  status: string;
  family_id: string;
  family_title: string;
  has_export: boolean;
  export_slug?: string;
  checksum?: string;
  platform_statuses: Record<string, string>;
  updated_at: string;
}

export async function createExportPackage(itemId: string): Promise<ExportPackageData> {
  return await request<ExportPackageData>(
    `/api/v1/export/${itemId}`,
    { method: "POST" }
  );
}

export async function getExportPackage(itemId: string): Promise<ExportPackageData> {
  return await request<ExportPackageData>(
    `/api/v1/export/item/${itemId}`
  );
}

export async function getPublishingOverview(itemId: string): Promise<PublishingOverview> {
  return await request<PublishingOverview>(
    `/api/v1/publishing/item/${itemId}`
  );
}

export async function updatePlatformPublication(
  pubId: string,
  payload: Partial<PlatformPublicationData>
): Promise<PlatformPublicationData> {
  return await request<PlatformPublicationData>(
    `/api/v1/publishing/${pubId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
}

export async function listPublishableItems(statusFilter?: string): Promise<PublishableItemSummary[]> {
  const query = statusFilter && statusFilter !== "all" ? `?status_filter=${encodeURIComponent(statusFilter)}` : "";
  return await request<PublishableItemSummary[]>(
    `/api/v1/publishing/list${query}`
  );
}

export function getExportDownloadUrl(itemId: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || API_BASE_URL;
  return `${base}/api/v1/export/item/${itemId}/download`;
}


