// Browser smoke for navigation and persisted creator workflow summaries.

import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseUrl = process.env.CREATOR_WORKFLOW_SMOKE_URL || "http://127.0.0.1:3018";
const browser = await chromium.launch({ headless: true });

function contentFamilyFor(scenario) {
  const isBlocked = scenario === "missing-research";
  return {
    id: "family-1",
    title: "Benchmark family",
    slug: "benchmark-family",
    status: "ACTIVE",
    content_pillar: "Engineering",
    original_value_type: "benchmark",
    summary: "A verified benchmark project.",
    topic_id: "topic-1",
    research_packet_id: isBlocked ? null : "research-1",
    originality_plan_id: "originality-1",
    primary_experiment_id: null,
    research_cost: 0,
    experiment_cost: 0,
    ai_cost: 0,
    media_cost: 0,
    manual_time_minutes: 0,
    local_compute_seconds: 0,
    economics: {},
    items: [{
      id: "item-1",
      content_family_id: "family-1",
      format: "short_vertical",
      platform_target: "youtube",
      working_title: "Measured benchmark video",
      angle: "Measure a local model under repeatable conditions.",
      hook_type: "surprising_stat",
      status: isBlocked ? "PLANNED" : "SCRIPT_REVIEW",
      incremental_cost: 0,
      manual_time_minutes: 0,
      local_compute_seconds: 0,
      original_value_connection: "",
      viewer_value: "",
      evidence_selections: isBlocked ? [] : [{
        id: "selection-1",
        claim_id: "claim-1",
        relevance_note: "",
        is_primary: true,
        claim_text: "A verified test result.",
        claim_type: "empirical_test",
        is_verified: true,
      }],
    }],
  };
}

const scriptFixture = {
  id: "script-1",
  content_item_id: "item-1",
  version: 1,
  format: "short_vertical",
  title: "Measured benchmark video",
  target_platform: "youtube",
  target_duration_sec: 60,
  total_word_count: 8,
  estimated_duration_sec: 5,
  status: "SCRIPT_REVIEW",
  is_approved: false,
  approved_by: null,
  approved_at: null,
  override_reason: null,
  quality_scores: null,
  generation_metadata: {
    generation_mode: "mock",
    provider: "mock",
    model: "deterministic-mock",
    approval_eligible: false,
    fallback_used: false,
    warnings: [],
  },
  sections: [{
    id: "section-1",
    section_type: "hook",
    order_index: 0,
    heading: "Hook",
    narration: "This is a local mock preview.",
    visual_cue: "Show a measurement chart.",
    evidence_category: "context",
    estimated_seconds: 5,
    word_count: 6,
    linked_claim_ids: [],
  }],
  revisions: [],
};

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const pageErrors = [];
  const failedRequests = [];
  const failedApiResponses = [];
  let workScenario = "script-review";
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => {
    if (request.url().includes("/api/")) failedRequests.push(request.url());
  });
  page.on("response", (response) => {
    if (response.url().includes("/api/") && response.status() >= 400) {
      failedApiResponses.push(`${response.status()} ${response.url()}`);
    }
  });
  await page.addInitScript(() => localStorage.setItem("studio_locale", "en"));

  await page.route("**/api/v1/settings/status", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      niche_configured: true,
      brand_configured: true,
      platforms_configured_count: 4,
      is_setup_completed: true,
      discovery_ready: true,
      generation_ready: true,
      active_niche_name: "Engineering",
      active_brand_name: "Hexabyte",
    }),
  }));

  await page.route("**/api/v1/opportunities/cockpit/summary", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      signals_today: 4,
      needs_review: 2,
      watching: 0,
      research_ready: 1,
      in_production: 3,
      ready_to_publish: 1,
      published: 0,
      ai_spend: 0,
      disk_usage: { database_bytes: 0, database_mb: 0, media_bytes: 0, media_mb: 0 },
      top_opportunities: [],
      engine_health_summary: [],
    }),
  }));

  await page.route("**/api/v1/content-families**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body;
    if (path.endsWith("/health")) {
      body = { status: "healthy", engine_id: "content_family" };
    } else if (path.endsWith("/family-1")) {
      body = contentFamilyFor(workScenario);
    } else {
      body = [{
        id: "family-1",
        title: "Benchmark family",
        slug: "benchmark-family",
        status: "ACTIVE",
        content_pillar: "Engineering",
        original_value_type: "benchmark",
        summary: "A verified benchmark project.",
        topic_id: "topic-1",
        research_packet_id: workScenario === "missing-research" ? null : "research-1",
        originality_plan_id: "originality-1",
        item_count: 1,
        shared_cost: 0,
        created_at: "2026-10-10T00:00:00Z",
      }];
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });

  await page.route("**/api/v1/content-items/item-1", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(contentFamilyFor(workScenario).items[0]),
  }));
  await page.route("**/api/v1/scripts/item/item-1", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(scriptFixture),
  }));
  await page.route("**/api/v1/scripts/script-1/revisions", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([]),
  }));

  await page.route("**/health", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      status: "healthy",
      database: "connected",
      version: "smoke",
      app_env: "test",
      registered_engines: 13,
      timestamp: new Date().toISOString(),
    }),
  }));

  const response = await page.goto(baseUrl, { waitUntil: "networkidle" });
  assert.equal(response?.status(), 200);
  await page.getByRole("heading", { name: "Creator workflow" }).waitFor();
  await page.getByRole("heading", { name: "Benchmark family" }).waitFor();
  await page.getByText("Current item: Measured benchmark video", { exact: true }).waitFor();
  await page.getByText("Script review required").waitFor();
  await page.getByText("A script draft is saved. Review it and approve it explicitly before scene and media production.", { exact: true }).waitFor();
  assert.equal(await page.getByRole("link", { name: "Review script" }).getAttribute("href"), "/script-studio/item-1");
  assert.equal(await page.locator('[data-checkpoint="topicLinked"]').getAttribute("data-complete"), "true");
  assert.equal(await page.locator('[data-checkpoint="researchLinked"]').getAttribute("data-complete"), "true");
  assert.equal(await page.locator('[data-checkpoint="scriptApproved"]').getAttribute("data-complete"), "false");
  assert.equal(await page.locator('[data-workflow-stage="discover"][data-next-action="true"]').count(), 1);
  assert.equal(await page.locator('[data-workflow-stage="verify"][data-next-action="true"]').count(), 0);
  if (process.env.CREATOR_WORKFLOW_SCREENSHOT) {
    await page.locator('section[aria-labelledby="current-work-title"]').screenshot({
      path: process.env.CREATOR_WORKFLOW_SCREENSHOT,
    });
  }

  await page.getByRole("link", { name: "Review script" }).click();
  await page.waitForURL("**/script-studio/item-1");
  await page.getByRole("heading", { name: "Script Studio" }).waitFor();

  const familiesResponse = await page.goto(`${baseUrl}/content-families`, { waitUntil: "networkidle" });
  assert.equal(familiesResponse?.status(), 200);
  const desktopNavigation = page.locator("aside").getByRole("navigation", { name: "Creator navigation" });
  assert.equal(await desktopNavigation.getByRole("link", { name: "Content Families", exact: true }).getAttribute("aria-current"), "page");
  const createGroup = desktopNavigation.getByRole("button", { name: /Create/ });
  assert.equal(await createGroup.getAttribute("aria-expanded"), "true");
  await page.reload({ waitUntil: "networkidle" });
  assert.equal(await page.locator("aside").getByRole("navigation", { name: "Creator navigation" }).getByRole("link", { name: "Content Families", exact: true }).getAttribute("aria-current"), "page");

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.getByTitle("বাংলা ভাষায় পরিবর্তন করুন").click();
  await page.getByRole("heading", { name: "বর্তমান কাজ" }).waitFor();
  await page.getByRole("button", { name: /যাচাই/ }).waitFor();
  await page.getByTitle("Switch to English").click();
  await page.getByRole("heading", { name: "Current work" }).waitFor();

  const verifyGroup = desktopNavigation.getByRole("button", { name: /Verify/ });
  assert.match(await verifyGroup.getAttribute("class") ?? "", /focus-visible:ring-2/);
  await verifyGroup.focus();
  assert.equal(await verifyGroup.evaluate((element) => document.activeElement === element), true);
  await verifyGroup.click();
  assert.equal(await verifyGroup.getAttribute("aria-expanded"), "true");
  await desktopNavigation.getByRole("link", { name: "Research", exact: true }).waitFor();
  await verifyGroup.click();
  assert.equal(await verifyGroup.getAttribute("aria-expanded"), "false");
  assert.equal(await desktopNavigation.getByRole("link", { name: "Research", exact: true }).count(), 0);
  await verifyGroup.click();

  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.waitForTimeout(100);
    const dimensions = await page.evaluate(() => ({
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
    }));
    assert.ok(dimensions.document <= dimensions.viewport, `horizontal overflow at ${width}px: ${JSON.stringify(dimensions)}`);
  }

  await page.setViewportSize({ width: 375, height: 812 });
  const mobileMenuButton = page.getByTestId("mobile-menu-button");
  const mobileMenuBox = await mobileMenuButton.boundingBox();
  assert.ok(mobileMenuBox && mobileMenuBox.width >= 44 && mobileMenuBox.height >= 44, "mobile menu should have a 44px target");
  await mobileMenuButton.click();
  const drawer = page.getByRole("dialog");
  const mobileVerify = drawer.getByRole("button", { name: /যাচাই|Verify/ });
  await mobileVerify.click();
  assert.equal(await mobileVerify.getAttribute("aria-expanded"), "true");
  await drawer.getByRole("link", { name: "Research", exact: true }).waitFor();
  const mobileCloseButton = page.getByTestId("mobile-menu-close-button");
  const mobileCloseBox = await mobileCloseButton.boundingBox();
  assert.ok(mobileCloseBox && mobileCloseBox.width >= 44 && mobileCloseBox.height >= 44, "mobile drawer close should have a 44px target");
  await page.keyboard.press("Escape");
  await drawer.waitFor({ state: "detached" });

  workScenario = "missing-research";
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.getByText("Blocked: no research packet is linked to this family. Complete research before script generation.", { exact: true }).waitFor();
  const blockedAction = page.locator('section[aria-labelledby="current-work-title"]').getByRole("link", { name: "Open research" });
  assert.equal(await blockedAction.getAttribute("href"), "/research");

  assert.deepEqual(pageErrors, []);
  assert.deepEqual(failedRequests, []);
  assert.deepEqual(failedApiResponses, []);
  console.log("PASS persisted current work, blocked prerequisites, action routes, desktop/mobile navigation, Bangla/English, direct route refresh, and responsive overflow checks.");
} finally {
  await browser.close();
}
