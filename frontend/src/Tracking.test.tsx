import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { getReport, getReports } from "./api/reports";
import { MyReports, ReportDetailPage, StatusTimeline } from "./Tracking";

vi.mock("./api/reports", () => ({ getReports: vi.fn(), getReport: vi.fn() }));
const list = vi.mocked(getReports); const detail = vi.mocked(getReport);
const item = { report_id: 8, description: "Pothole near gate", category: "pothole", severity: "high", status: "analyzed", created_at: "2026-09-16T10:00:00" };
const report = { report_id: 8, incident: { id: 8, description: "Pothole near gate", latitude: 12.9, longitude: 80.2, category: "pothole", severity: "high", status: "in_progress", confidence: .9, created_at: "2026-09-16T10:00:00" }, evidence: null, evidence_url: null, analysis: { category: "pothole", severity: "high", priority_level: "high", requires_review: false } };
beforeEach(() => { list.mockReset(); detail.mockReset(); }); afterEach(cleanup);
test("shows loading then submitted reports", async () => { list.mockResolvedValue([item]); render(<MyReports openReport={() => undefined} />); expect(screen.getByText("Loading reports…")).toBeInTheDocument(); expect(await screen.findByText("Report #8")).toBeInTheDocument(); });
test("shows an empty state", async () => { list.mockResolvedValue([]); render(<MyReports openReport={() => undefined} />); expect(await screen.findByText("No pothole reports yet.")).toBeInTheDocument(); });
test("shows report detail and backend-driven timeline", async () => { detail.mockResolvedValue(report); render(<ReportDetailPage reportId={8} />); expect(await screen.findByText("Pothole near gate")).toBeInTheDocument(); expect(screen.getByText("Repair in progress")).toBeInTheDocument(); });
test("shows not-found errors", async () => { detail.mockRejectedValue(new Error("Report not found.")); render(<ReportDetailPage reportId={999} />); expect(await screen.findByRole("alert")).toHaveTextContent("Report not found"); });
test("marks timeline stages from status", () => { render(<StatusTimeline status="resolved" />); expect(screen.getByText("Road repaired")).toBeInTheDocument(); expect(document.querySelectorAll(".timeline .done")).toHaveLength(4); });
