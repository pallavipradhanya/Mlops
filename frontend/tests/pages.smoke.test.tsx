/**
 * Renders every page against fixtures captured from the real backend (tests/fixtures/*.json),
 * so a change in an API response shape breaks CI instead of the dashboard.
 */
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import datasets from "./fixtures/datasets.json";
import experiments from "./fixtures/experiments.json";
import models from "./fixtures/models.json";
import overview from "./fixtures/overview.json";
import predictions from "./fixtures/predictions.json";
import reports from "./fixtures/reports.json";
import retraining from "./fixtures/retraining.json";
import sample from "./fixtures/sample.json";
import settings from "./fixtures/settings.json";
import system from "./fixtures/system.json";
import activity from "./fixtures/activity.json";
import health from "./fixtures/health.json";

vi.mock("next/link", () => ({ default: ({ href, children }: { href: string; children: ReactNode }) => <a href={href}>{children}</a> }));

const routes: Record<string, unknown> = {
  "/api/health": health, "/api/overview": overview, "/api/datasets": datasets, "/api/experiments": experiments,
  "/api/models": models, "/api/predict/sample": sample, "/api/predictions?limit=25": predictions,
  "/api/monitoring/reports": reports, "/api/retraining/history": retraining, "/api/settings": settings,
  "/api/system": system, "/api/activity?limit=40": activity,
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    const key = String(url).replace(/^https?:\/\/[^/]+/, "");
    if (!(key in routes)) return new Response(JSON.stringify({ detail: `unmocked ${key}` }), { status: 500 });
    return new Response(JSON.stringify(routes[key]), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
});

const pages: [string, () => Promise<{ default: () => ReactNode }>, RegExp][] = [
  ["overview", () => import("../app/page"), /Champion model/],
  ["datasets", () => import("../app/datasets/page"), /Dataset versions/],
  ["training", () => import("../app/training/page"), /Configure run/],
  ["experiments", () => import("../app/experiments/page"), /All runs/],
  ["registry", () => import("../app/registry/page"), /Registered model: churn-model/],
  ["predictions", () => import("../app/predictions/page"), /Prediction log/],
  ["monitoring", () => import("../app/monitoring/page"), /Report history/],
  ["retraining", () => import("../app/retraining/page"), /Retraining history/],
  ["settings", () => import("../app/settings/page"), /Activity log/],
];

describe("pages render with real API response shapes", () => {
  it.each(pages)("%s", async (_name, load, expected) => {
    const Page = (await load()).default;
    render(<Page />);
    await waitFor(() => expect(screen.getAllByText(expected).length).toBeGreaterThan(0), { timeout: 4000 });
    expect(screen.queryByText(/Cannot reach the backend/)).toBeNull();
  });

  it("registry shows the champion row and a rollback control", async () => {
    const Page = (await import("../app/registry/page")).default;
    render(<Page />);
    await waitFor(() => expect(screen.getAllByText("champion").length).toBeGreaterThan(0));
    expect(screen.getByText(/Roll back/)).toBeTruthy();
  });

  it("monitoring shows the feature drift table for a completed report", async () => {
    const Page = (await import("../app/monitoring/page")).default;
    render(<Page />);
    await waitFor(() => expect(screen.getByText("Feature-level drift")).toBeTruthy());
    expect(screen.getAllByText("MonthlyCharges").length).toBeGreaterThan(0);
  });
});
