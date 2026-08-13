import { expect, test } from "@playwright/test";

test("dispatcher can create and approve a critical flood rescue report", async ({ page }) => {
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Aapda-Mitra" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Rescue queue" })).toBeVisible();
  await page.getByRole("button", { name: "Flood rescue" }).click();
  await expect(page.getByLabel("Caller transcript")).toHaveValue(/rising flood water/);
  await page.getByRole("button", { name: "Create rescue report" }).click();

  const createdReport = page.locator(".report").filter({
    hasText: "We are trapped in rising flood water with my elderly mother.",
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
