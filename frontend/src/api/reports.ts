export type Incident = { id: number; description: string; latitude: number; longitude: number; category: string | null; severity: string | null; status: string; confidence: number | null; created_at: string };
export type Evidence = { id: number; incident_id: number; storage_path: string; file_type: string; created_at: string };
export type Analysis = { priority_level: string; requires_review: boolean; severity: string; category: string };
export type SubmittedReport = { report_id: number; incident: Incident; evidence: Evidence; analysis: { analysis: Analysis; duplicate_analysis: { incident_id: number; status: string } | null } };
export type ReportListItem = Pick<Incident, "description" | "category" | "severity" | "status" | "created_at"> & { report_id: number };
export type ReportDetail = { report_id: number; incident: Incident; evidence: Evidence | null; evidence_url: string | null; analysis: Analysis | null };

const API_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export class ReportApiError extends Error { constructor(message: string, public status?: number) { super(message); } }

async function request<T>(path: string): Promise<T> {
  try {
    const response = await fetch(`${API_URL}${path}`);
    if (response.status === 404) throw new ReportApiError("Report not found.", 404);
    if (!response.ok) throw new ReportApiError("Unable to load this report. Please try again.", response.status);
    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof ReportApiError) throw error;
    throw new ReportApiError("Unable to connect. Please check your connection and try again.");
  }
}

export const getReports = () => request<ReportListItem[]>("/reports");
export const getReport = (reportId: number) => request<ReportDetail>(`/reports/${reportId}`);

export async function submitReport(input: { description: string; latitude: number; longitude: number; photo: File }): Promise<SubmittedReport> {
  const form = new FormData();
  form.append("description", input.description); form.append("latitude", String(input.latitude)); form.append("longitude", String(input.longitude)); form.append("photo", input.photo);
  try {
    const response = await fetch(`${API_URL}/reports`, { method: "POST", body: form });
    if (response.status === 422) throw new ReportApiError("We couldn't confirm a pothole from this image. Please try another photo.", 422);
    if (!response.ok) throw new ReportApiError("We couldn't submit your report. Please try again.", response.status);
    return response.json() as Promise<SubmittedReport>;
  } catch (error) {
    if (error instanceof ReportApiError) throw error;
    throw new ReportApiError("Unable to connect. Please check your connection and try again.");
  }
}
