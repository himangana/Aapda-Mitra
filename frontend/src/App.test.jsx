import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import React from "react";
import App from "./App";

afterEach(() => vi.restoreAllMocks());

test("renders live-style pending reports in the command-center queue", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => [{
      id: "report-1",
      created_at: "2026-08-13T08:00:00.000Z",
      transcript: "Caller trapped in rising flood water.",
      location: "Sector 12, Delhi",
      disaster_type: "flood",
      urgency_score: 10,
      summary: "Caller trapped in rising flood water.",
      recommended_action: "Immediate emergency dispatch",
      caller_guidance: "Stay on the line if safe.",
      source_status: "Demo safety fallback",
      dispatcher_status: "pending_human_approval",
    }],
  }));

  render(<App />);
  await waitFor(() => expect(screen.getByText("Critical")).toBeTruthy());
  expect(screen.getByText("1")).toBeTruthy();
  expect(screen.getByText("reports awaiting human approval")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Approve dispatch" })).toBeTruthy();
});
