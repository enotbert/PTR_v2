import { expect, test } from "@playwright/test";

test.describe.configure({ mode: "serial" });

test.describe("app shell (mobile viewport)", () => {
  test("shows network status strip and enables primary CTA when API healthy", async ({
    page,
  }) => {
    await page.route("**/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ok", postgres: "reachable" }),
      });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });

    const strip = page.getByTestId("network-status");
    await expect(strip).toBeVisible({ timeout: 15_000 });
    await expect(strip).toHaveAttribute("data-status", "ready", {
      timeout: 15_000,
    });

    const cta = page.getByTestId("primary-cta");
    await expect(cta).toBeEnabled();
  });

  test("shows offline state on an already loaded shell", async ({
    context,
    page,
  }) => {
    await page.route("**/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ok", postgres: "reachable" }),
      });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("network-status")).toBeVisible({
      timeout: 15_000,
    });

    await context.setOffline(true);
    await expect(page.getByTestId("network-status")).toHaveAttribute(
      "data-status",
      "offline",
      { timeout: 10_000 },
    );
    await expect(page.getByTestId("primary-cta")).toBeDisabled();
  });

  test("keeps shell available but blocks gameplay when API is unavailable", async ({
    page,
  }) => {
    await page.route("**/health", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ status: "degraded", postgres: "unreachable" }),
      });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });

    await expect(page.getByTestId("network-status")).toHaveAttribute(
      "data-status",
      "api-unavailable",
      { timeout: 15_000 },
    );
    await expect(page.getByTestId("primary-cta")).toBeDisabled();
    await expect(page.getByText(/shell stays available/i)).toBeVisible();
  });
});
