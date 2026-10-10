// Browser smoke for the stage-first creator workflow; all API responses are intercepted.

import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseUrl = process.env.CREATOR_WORKFLOW_SMOKE_URL || "http://127.0.0.1:3018";
const browser = await chromium.launch({ headless: true });

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
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

  await page.route("**/api/v1/content-families**", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([{
      id: "family-1",
      title: "Benchmark family",
      slug: "benchmark-family",
      status: "ACTIVE",
      content_pillar: "Engineering",
      original_value_type: "benchmark",
      summary: "A verified benchmark project.",
      item_count: 2,
      shared_cost: 0,
    }]),
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
  await page.getByRole("link", { name: "Review opportunities" }).waitFor();
  assert.equal(await page.locator('[data-workflow-stage="discover"][data-next-action="true"]').count(), 1);
  assert.equal(await page.locator('[data-workflow-stage="verify"][data-next-action="true"]').count(), 0);

  const desktopNavigation = page.locator("aside").getByRole("navigation", { name: "Creator navigation" });
  const verifyGroup = desktopNavigation.getByRole("button", { name: /Verify/ });
  await verifyGroup.click();
  assert.equal(await verifyGroup.getAttribute("aria-expanded"), "true");
  await desktopNavigation.getByRole("link", { name: "Research", exact: true }).waitFor();
  const navButtonBox = await verifyGroup.boundingBox();
  assert.ok(navButtonBox && navButtonBox.height >= 44, "stage navigation buttons should have a 44px target");

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
  const mobileVerify = drawer.getByRole("button", { name: /Verify/ });
  await mobileVerify.click();
  assert.equal(await mobileVerify.getAttribute("aria-expanded"), "true");
  await drawer.getByRole("link", { name: "Research", exact: true }).waitFor();
  const mobileCloseButton = page.getByTestId("mobile-menu-close-button");
  const mobileCloseBox = await mobileCloseButton.boundingBox();
  assert.ok(mobileCloseBox && mobileCloseBox.width >= 44 && mobileCloseBox.height >= 44, "mobile drawer close should have a 44px target");
  await mobileCloseButton.click();

  assert.deepEqual(pageErrors, []);
  console.log("PASS stage-first workflow, next action, accessible navigation, mobile drawer, and 375/768/1440px overflow checks.");
} finally {
  await browser.close();
}
