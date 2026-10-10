// Browser smoke for Gemini-only live selection; API responses are intercepted.

import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseUrl = process.env.AI_PROVIDER_UI_SMOKE_URL || "http://127.0.0.1:3017";
const browser = await chromium.launch({ headless: true });

try {
  const page = await browser.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.route("**/api/v1/ai/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body;
    if (path.endsWith("/status")) {
      body = {
        mock_mode: true,
        primary_provider: "gemini",
        primary_configured: true,
        primary_model: "gemini-3.8-flash",
        fallback_provider: "none",
        fallback_configured: false,
        fallback_model: "",
        fallback_enabled: false,
        daily_spend_today: 0,
        daily_budget_limit: 5,
        budget_exceeded: false,
      };
    } else if (path.endsWith("/analytics")) {
      body = {
        total_calls: 0,
        total_cost: 0,
        success_rate: 100,
        fallback_count: 0,
        fallback_rate: 0,
        provider_breakdown: [],
      };
    } else if (path.endsWith("/logs")) {
      body = [];
    } else {
      throw new Error(`Unexpected AI API route: ${path}`);
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });

  const response = await page.goto(`${baseUrl}/ai`, { waitUntil: "networkidle" });
  assert.equal(response?.status(), 200);
  await page.getByRole("heading", { name: "AI Provider Engine" }).waitFor();
  await page.getByText("gemini credential configured · Mock adapter active", { exact: true }).waitFor();
  await page.getByText("Gemini Adapter", { exact: true }).waitFor();

  const provider = page.getByRole("combobox", { name: "Preferred Provider" });
  const preferredOptions = await provider.getByRole("option").allTextContents();
  assert.deepEqual(preferredOptions, ["Auto (Gemini or Mock mode)", "Gemini", "Mock Offline"]);
  assert.equal(await provider.locator('option[value="openai"]').count(), 0);
  assert.equal(await provider.locator('option[value="qwen"]').count(), 0);
  await provider.selectOption("gemini");
  assert.equal(await provider.inputValue(), "gemini");

  await page.getByRole("button", { name: /Invocation Telemetry Logs/ }).click();
  const providerFilter = page.getByRole("combobox", { name: "Filter Provider" });
  const providerOptions = await providerFilter.getByRole("option").allTextContents();
  assert.ok(providerOptions.includes("Gemini"));
  assert.ok(providerOptions.includes("Mock"));
  assert.deepEqual(pageErrors, []);

  console.log("PASS only Gemini and Mock are selectable for new requests (API responses intercepted).");
} finally {
  await browser.close();
}
