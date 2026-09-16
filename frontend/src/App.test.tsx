import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "./App";
import { submitReport } from "./api/reports";

vi.mock("./api/reports", () => ({ submitReport: vi.fn() }));
const mockedSubmit = vi.mocked(submitReport);
const photo = new File(["photo"], "pothole.jpg", { type: "image/jpeg" });
const report = { report_id: 1042, incident: { id: 1042, description: "Large pothole", latitude: 12.9, longitude: 80.2, category: "pothole", severity: "high", status: "analyzed", confidence: .9, created_at: "2026-09-16T10:00:00" }, evidence: { id: 4, incident_id: 1042, storage_path: "x", file_type: "image/jpeg", created_at: "2026-09-16T10:00:00" }, analysis: { analysis: { priority_level: "high", requires_review: false }, duplicate_analysis: null } };

function renderValidForm() {
  render(<App />);
  fireEvent.change(screen.getByLabelText("Add photo"), { target: { files: [photo] } });
  fireEvent.change(screen.getByLabelText("Latitude"), { target: { value: "12.9" } });
  fireEvent.change(screen.getByLabelText("Longitude"), { target: { value: "80.2" } });
  fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Large pothole near gate" } });
}

function submit() { fireEvent.submit(screen.getByRole("button", { name: "Submit report" }).closest("form")!); }

beforeEach(() => mockedSubmit.mockReset());
afterEach(cleanup);

test("renders the citizen report flow", () => { render(<App />); expect(screen.getByRole("heading", { name: "Report a pothole" })).toBeInTheDocument(); });
test("requires a photo before submission", () => { render(<App />); submit(); expect(screen.getByRole("alert")).toHaveTextContent("Add a photo"); });
test("rejects unsupported image types", () => { render(<App />); fireEvent.change(screen.getByLabelText("Add photo"), { target: { files: [new File(["x"], "x.gif", { type: "image/gif" })] } }); expect(screen.getByRole("alert")).toHaveTextContent("JPEG, PNG, or WEBP"); });
test("submits once and displays the returned report", async () => { mockedSubmit.mockResolvedValue(report); renderValidForm(); submit(); await waitFor(() => expect(screen.getByText("Report #1042")).toBeInTheDocument()); expect(mockedSubmit).toHaveBeenCalledTimes(1); expect(screen.getByText("Report reviewed")).toBeInTheDocument(); });
