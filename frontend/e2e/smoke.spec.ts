import { test, expect } from "@playwright/test";

test("home loads and shows run test heading", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /run test/i })).toBeVisible();
});
