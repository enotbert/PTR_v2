import { expect, test } from "@playwright/test";

test.describe.configure({ mode: "serial" });

async function mockTavernState(page: import("@playwright/test").Page) {
  await page.route("**/v1/taverns/*/state", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        tavern_id: "00000000-0000-0000-0000-000000000001",
        player_id: "00000000-0000-0000-0000-000000000010",
        reputation: 25,
        weekly_points: 25,
        updated_at: "2026-05-05T09:00:00Z",
        current_project: {
          id: "weekly_route_reopening",
          title: "Reopen the blocked route",
          status: "active",
          progress_points: 25,
          target_points: 1000,
        },
        contribution_summary: {
          total_points: 25,
          latest_amount: 25,
          latest_source_type: "raid_reward",
          latest_at: "2026-05-05T09:00:00Z",
        },
        chronicle: [
          {
            id: "00000000-0000-0000-0000-000000000099",
            source_type: "raid_reward",
            source_ref: "raid-1",
            amount: 25,
            created_at: "2026-05-05T09:00:00Z",
          },
        ],
      }),
    });
  });
}

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
    await mockTavernState(page);

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
    await mockTavernState(page);

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
    await expect(page.getByText(/temporarily unavailable/i)).toBeVisible();
  });

  test("renders tavern first-load state with project and chronicle data", async ({
    page,
  }) => {
    await page.route("**/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ok", postgres: "reachable" }),
      });
    });
    await mockTavernState(page);

    await page.goto("/", { waitUntil: "domcontentloaded" });

    await expect(page.getByTestId("network-status")).toHaveAttribute(
      "data-status",
      "ready",
      { timeout: 15_000 },
    );
    await expect(page.getByTestId("tavern-project")).toBeVisible();
    await expect(page.getByText(/reopen the blocked route/i)).toBeVisible();
    await expect(page.getByTestId("tavern-chronicle")).toContainText(
      /\+25 from raid reward/i,
    );
  });

  test("creates first tutorial raid setup and enables next CTA", async ({
    page,
  }) => {
    await page.route("**/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ok", postgres: "reachable" }),
      });
    });
    await mockTavernState(page);

    let raidCreateBody: Record<string, unknown> | null = null;
    await page.route("**/v1/raids", async (route) => {
      const req = route.request();
      raidCreateBody = req.postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "00000000-0000-0000-0000-000000000777",
          party_id: "00000000-0000-0000-0000-000000000222",
          raid_template_id: "tutorial_solo_v1",
          status: "pending",
        }),
      });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("primary-cta")).toBeEnabled({
      timeout: 15_000,
    });

    await page.getByTestId("primary-cta").click();

    await expect(page.getByTestId("first-session-message")).toContainText(
      /first raid setup is ready/i,
    );
    await expect(page.getByTestId("first-session-raid-id")).toContainText(
      /00000000-0000-0000-0000-000000000777/i,
    );
    await expect(page.getByTestId("next-cta")).toBeEnabled();

    expect(raidCreateBody).toEqual({
      raid_template_id: "tutorial_solo_v1",
      tavern_id: "00000000-0000-0000-0000-000000000001",
    });
  });

  test("renders nonblank combat canvas preview", async ({ page }) => {
    await page.route("**/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ok", postgres: "reachable" }),
      });
    });
    await mockTavernState(page);

    await page.goto("/", { waitUntil: "domcontentloaded" });

    const canvas = page.getByTestId("combat-canvas");
    await expect(canvas).toBeVisible({ timeout: 15_000 });

    const renderMeta = await canvas.evaluate((node) => {
      if (!(node instanceof HTMLCanvasElement)) {
        return { rendered: false, unitCount: 0 };
      }
      const { width, height } = node;
      if (width === 0 || height === 0) {
        return { rendered: false, unitCount: 0 };
      }
      return {
        rendered: node.dataset.renderState === "ready",
        unitCount: Number.parseInt(node.dataset.unitCount ?? "0", 10),
      };
    });

    expect(renderMeta.rendered).toBe(true);
    expect(renderMeta.unitCount).toBeGreaterThanOrEqual(6);
  });
});
