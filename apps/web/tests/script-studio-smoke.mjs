// Browser smoke for a persisted-state Script Studio preview; API responses are intercepted.

import assert from "node:assert/strict";
import { chromium } from "playwright";

const itemId = "script-studio-smoke-item";
const baseUrl = process.env.SCRIPT_STUDIO_BASE_URL || "http://127.0.0.1:3018";
const browser = await chromium.launch({ headless: true });

const item = {
  id: itemId,
  content_family_id: "script-studio-smoke-family",
  family_title: "Script Studio smoke family",
  format: "short_vertical",
  platform_target: "youtube",
  working_title: "Mock preview item",
  angle: "A deterministic offline smoke fixture.",
  hook_type: "direct_value",
  status: "SCRIPT_REVIEW",
  incremental_cost: 0,
  manual_time_minutes: 0,
  local_compute_seconds: 0,
  original_value_connection: "",
  viewer_value: "",
  evidence_selections: [],
};

const script = {
  id: "script-studio-smoke-script",
  content_item_id: itemId,
  version: 1,
  format: "short_vertical",
  title: "Mock preview item",
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
    id: "script-studio-smoke-section",
    section_type: "hook",
    order_index: 0,
    heading: "Hook",
    narration: "This is a deterministic mock preview.",
    visual_cue: "Show a local preview card.",
    evidence_category: "context",
    estimated_seconds: 5,
    word_count: 6,
    linked_claim_ids: [],
  }],
  revisions: [],
};

try {
  const page = await browser.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.addInitScript(() => localStorage.setItem("studio_locale", "en"));

  await page.route(`**/api/v1/content-items/${itemId}`, (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(item),
  }));
  await page.route(`**/api/v1/scripts/item/${itemId}`, (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(script),
  }));
  await page.route(`**/api/v1/scripts/${script.id}/revisions`, (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([]),
  }));

  const response = await page.goto(`${baseUrl}/script-studio/${encodeURIComponent(itemId)}`, {
    waitUntil: "networkidle",
  });
  assert.ok(response?.ok(), `Script Studio returned HTTP ${response?.status() ?? "no response"}.`);

  await page.getByText("AI Generation", { exact: true }).waitFor();
  await page.getByText("Mock or legacy preview — cannot be approved", { exact: true }).waitFor();

  const approvalButton = page.getByRole("button", { name: "Approve Script" });
  assert.equal(await approvalButton.isDisabled(), true, "Mock output must not enable approval.");
  assert.deepEqual(pageErrors, [], "Script Studio should render without browser errors.");

  console.log("PASS intercepted mock preview is labeled unverified and keeps script approval disabled.");
} finally {
  await browser.close();
}
