import assert from "node:assert/strict";
import { chromium } from "playwright";

const itemId = process.env.SCRIPT_STUDIO_ITEM_ID;
if (!itemId) {
  throw new Error("Set SCRIPT_STUDIO_ITEM_ID to a persisted Script Studio content item.");
}

const baseUrl = process.env.SCRIPT_STUDIO_BASE_URL || "http://127.0.0.1:3000";
const browser = await chromium.launch({ headless: true });

try {
  const page = await browser.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  const response = await page.goto(`${baseUrl}/script-studio/${encodeURIComponent(itemId)}`, {
    waitUntil: "networkidle",
  });
  assert.ok(response?.ok(), `Script Studio returned HTTP ${response?.status() ?? "no response"}.`);

  await page.getByText("AI Generation", { exact: true }).waitFor();
  await page.getByText("Mock or legacy preview — cannot be approved", { exact: true }).waitFor();

  const approvalButton = page.getByRole("button", { name: "Approve Script" });
  assert.equal(await approvalButton.isDisabled(), true, "Mock output must not enable approval.");
  assert.deepEqual(pageErrors, [], "Script Studio should render without browser errors.");

  console.log("PASS Script Studio labels mock output and keeps approval disabled.");
} finally {
  await browser.close();
}
