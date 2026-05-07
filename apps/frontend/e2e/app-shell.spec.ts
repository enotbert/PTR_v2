import { expect, test } from "@playwright/test";

test.describe.configure({ mode: "serial" });

const MOCK_SESSION_ENVELOPE = {
  player: {
    id: "00000000-0000-0000-0000-000000000010",
    display_name: "E2E Player",
    created_at: "2026-05-05T09:00:00Z",
    updated_at: "2026-05-05T09:00:00Z",
    last_seen_at: "2026-05-05T09:00:00Z",
    is_active: true,
  },
  session: {
    id: "00000000-0000-0000-0000-000000000099",
    player_id: "00000000-0000-0000-0000-000000000010",
    issued_at: "2026-05-05T09:00:00Z",
    expires_at: "2027-05-05T09:00:00Z",
  },
};

async function mockGameplaySession(page: import("@playwright/test").Page) {
  await page.route("**/v1/sessions", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify(MOCK_SESSION_ENVELOPE),
    });
  });
  await page.route("**/v1/sessions/current", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_SESSION_ENVELOPE),
    });
  });
}

async function mockTavernState(page: import("@playwright/test").Page) {
  await mockGameplaySession(page);
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

async function mockBattleSocketWithOutcome(
  page: import("@playwright/test").Page,
) {
  await page.addInitScript(() => {
    const NativeWebSocket = window.WebSocket;
    window.WebSocket = new Proxy(NativeWebSocket, {
      construct(target, args) {
        const [url] = args as [string | URL];
        const parsedUrl = String(url);
        if (!parsedUrl.includes("/v1/ws/battles/")) {
          return Reflect.construct(target, args);
        }
        const listeners = new Map<string, Set<(event: Event) => void>>();
        const socket = {
          url: parsedUrl,
          readyState: NativeWebSocket.OPEN,
          onopen: null as ((event: Event) => void) | null,
          onmessage: null as ((event: MessageEvent) => void) | null,
          onerror: null as ((event: Event) => void) | null,
          onclose: null as ((event: CloseEvent) => void) | null,
          send() {},
          close() {
            socket.readyState = NativeWebSocket.CLOSED;
            const event = new CloseEvent("close");
            socket.onclose?.(event);
            listeners.get("close")?.forEach((handler) => {
              handler(event);
            });
          },
          addEventListener(type: string, handler: (event: Event) => void) {
            const bucket = listeners.get(type) ?? new Set();
            bucket.add(handler);
            listeners.set(type, bucket);
          },
          removeEventListener(type: string, handler: (event: Event) => void) {
            listeners.get(type)?.delete(handler);
          },
          dispatchEvent(event: Event) {
            listeners.get(event.type)?.forEach((handler) => {
              handler(event);
            });
            return true;
          },
        };
        setTimeout(() => {
          const openEvent = new Event("open");
          socket.onopen?.(openEvent);
          socket.dispatchEvent(openEvent);
          const snapshotEvent = new MessageEvent("message", {
            data: JSON.stringify({
              kind: "snapshot",
              type: "battle.snapshot",
              server_seq: 1,
              payload: {
                battle_id: "00000000-0000-0000-0000-000000000222",
                phase: "active",
                raid_lead_player_id: "00000000-0000-0000-0000-000000000010",
                party_order: [],
                entities: [],
                last_raid_lead_command: null,
              },
            }),
          });
          socket.onmessage?.(snapshotEvent);
          socket.dispatchEvent(snapshotEvent);
          const outcomeEvent = new MessageEvent("message", {
            data: JSON.stringify({
              kind: "event",
              type: "battle.event",
              server_seq: 2,
              payload: {
                event_type: "raid_outcome_resolved",
                raid_id: "00000000-0000-0000-0000-000000000777",
                status: "completed",
                approved_failed_progress: false,
                reward_points_per_member: 30,
                claim_status: "already_claimed",
                reward_record_ids: ["reward-1"],
                newly_issued_reward_record_ids: [],
                existing_reward_record_ids: ["reward-1"],
              },
            }),
          });
          socket.onmessage?.(outcomeEvent);
          socket.dispatchEvent(outcomeEvent);
        }, 0);
        return socket as unknown as WebSocket;
      },
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

  test("renders battle communications panel on tavern home", async ({
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

    await expect(page.getByTestId("combat-comms-panel")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByTestId("combat-comms-emoji-row")).toBeVisible();
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

    const rendered = await canvas.evaluate((node) => {
      if (!(node instanceof HTMLCanvasElement)) {
        return false;
      }
      const { width, height } = node;
      if (width === 0 || height === 0) {
        return false;
      }
      return node.dataset.renderState === "ready";
    });

    expect(rendered).toBe(true);
  });

  test("supports target selection flow with valid and invalid feedback", async ({
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

    await expect(page.getByTestId("combat-skill-bar")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByTestId("combat-target")).toContainText(
      /no target selected/i,
    );

    await expect(page.getByTestId("combat-skill-quick-shot")).toBeEnabled();
    await expect(page.getByTestId("combat-skill-heavy-slash")).toBeEnabled();
    await expect(page.getByTestId("combat-skill-focus-stance")).toBeDisabled();

    const canvas = page.getByTestId("combat-canvas");
    await expect(canvas).toBeVisible();

    await page.getByTestId("combat-skill-heavy-slash").click();
    const box = await canvas.boundingBox();
    expect(box).not.toBeNull();
    if (!box) {
      throw new Error("combat canvas bounding box is missing");
    }

    await canvas.click({
      position: { x: box.width * 0.2, y: box.height * 0.22 },
    });
    await expect(page.getByTestId("combat-target-hint")).toContainText(
      /cannot reach that target/i,
    );
    await expect(page.getByTestId("combat-feedback")).toContainText(
      /invalid target for heavy slash/i,
    );

    await canvas.click({
      position: { x: box.width * 0.2, y: box.height * 0.74 },
    });
    await expect(page.getByTestId("combat-feedback")).toContainText(
      /heavy slash used on vg/i,
    );
    await expect(page.getByTestId("combat-resource")).toContainText(/1$/);
    await expect(page.getByTestId("combat-skill-quick-shot")).toBeDisabled();
  });

  test("renders raid result/reward card for already-claimed outcome", async ({
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
    await mockBattleSocketWithOutcome(page);
    await page.route("**/v1/raids", async (route) => {
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
    await page.getByTestId("primary-cta").click();

    await expect(page.getByTestId("raid-result-reward")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByTestId("raid-result-reward")).toContainText(
      /raid completed/i,
    );
    await expect(page.getByTestId("reward-claim-state")).toContainText(
      /already claimed/i,
    );
    await expect(page.getByTestId("cta-repeat-raid")).toBeVisible();
  });
});
