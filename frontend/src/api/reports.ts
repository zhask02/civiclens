export type Report = {
  report_id: number;
  incident: { id: number; description: string; latitude: number; longitude: number; category: string | null; severity: string | null; status: string; confidence: number | null; created_at: string };
  evidence: { id: number; incident_id: number; storage_path: string; file_type: string; created_at: string };
  analysis: { analysis: { priority_level: string; requires_review: boolean }; duplicate_analysis: { incident_id: number; status: string } | null };
};

const API_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function submitReport(input: { description: string; latitude: number; longitude: number; photo: File }): Promise<Report> {
  const form = new FormData();
  form.append("description", input.description);
  form.append("latitude", String(input.latitude));
  form.append("longitude", String(input.longitude));
  form.append("photo", input.photo);
  const response = await fetch(`${API_URL}/reports`, { method: "POST", body: form });
  if (!response.ok) {
    if (response.status === 422) throw new Error("We couldn't confirm a pothole from this image. Please try another photo.");
    throw new Error("We couldn't submit your report. Please try again.");
  }
  return response.json() as Promise<Report>;
}
