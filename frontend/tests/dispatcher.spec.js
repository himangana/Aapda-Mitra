import { expect, test } from "@playwright/test";

test("dispatcher can create and approve a critical flood rescue report", async ({ page }) => {
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Aapda-Mitra" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Rescue queue" })).toBeVisible();
  const caseId = `browser-case-${Date.now()}`;
  const transcript = `We are trapped in rising flood water with my elderly mother. ${caseId}`;
  await page.getByLabel("Caller transcript").fill(transcript);
  await page.getByLabel("Location (if known)").fill("Sector 12, Delhi");
  await page.getByRole("button", { name: "Create rescue report" }).click();

  const createdReport = page.locator(".report").filter({
    hasText: caseId,
  }).first();
  await expect(createdReport).toContainText("Critical");
  await expect(createdReport).toContainText("Immediate emergency dispatch");
  await createdReport.getByRole("button", { name: "Approve dispatch" }).click();
  await expect(createdReport.getByText("Approved", { exact: true })).toBeVisible();
  expect(pageErrors).toEqual([]);
});

test("dashboard keeps the responsive emergency input usable on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/", { waitUntil: "networkidle" });
  await expect(page.getByRole("button", { name: "Shelter guidance" })).toBeVisible();
  await page.getByRole("button", { name: "Shelter guidance" }).click();
  await page.getByRole("button", { name: "Create rescue report" }).click();
  await expect(page.locator(".report").first()).toContainText("Send automated guidance");
});
