import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { OperatorConsole } from "./Operator";
import { getEvidence, getHistory, getQueue } from "./api/operator";

vi.mock("./api/operator", () => ({
  addNote: vi.fn(),
  assignIncident: vi.fn(),
  getEvidence: vi.fn(),
  getHistory: vi.fn(),
  getQueue: vi.fn(),
  updateStatus: vi.fn(),
}));

const queue = [{ incident: { id: 8, description: "Pothole near gate", latitude: 12.9, longitude: 80.2, category: "pothole", severity: "high", status: "analyzed", confidence: 0.9, created_at: "2026-09-18T10:00:00" }, routing: null, assignment: null }];
const evidence = vi.mocked(getEvidence);
const history = vi.mocked(getHistory);
const getQueueMock = vi.mocked(getQueue);

beforeEach(() => { getQueueMock.mockReset(); history.mockReset(); evidence.mockReset(); getQueueMock.mockResolvedValue(queue); history.mockResolvedValue([]); });
afterEach(cleanup);

async function selectIncident() {
  render(<OperatorConsole />);
  fireEvent.change(screen.getByLabelText("Operator token"), { target: { value: "test-token" } });
  fireEvent.click(screen.getByRole("button", { name: "Open incident queue" }));
  fireEvent.click(await screen.findByRole("button", { name: /#8/i }));
}

test("renders the selected incident evidence image", async () => {
  evidence.mockResolvedValue({ url: "https://storage.example.test/evidence" });
  await selectIncident();
  expect(await screen.findByAltText("Evidence for incident 8")).toHaveAttribute("src", "https://storage.example.test/evidence");
});

test("shows a clear missing-evidence message", async () => {
  evidence.mockResolvedValue({ url: null });
  await selectIncident();
  expect(await screen.findByText("No evidence image available.")).toBeInTheDocument();
});

test("hides a failed image and explains the problem", async () => {
  evidence.mockResolvedValue({ url: "https://storage.example.test/evidence" });
  await selectIncident();
  fireEvent.error(await screen.findByAltText("Evidence for incident 8"));
  await waitFor(() => expect(screen.getByText("Evidence image could not be displayed.")).toBeInTheDocument());
  expect(screen.queryByAltText("Evidence for incident 8")).not.toBeInTheDocument();
});
