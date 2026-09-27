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



