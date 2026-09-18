import { Incident } from "./reports";

const API_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export type Routing = { authority_id: number | null; jurisdiction: string; source: string; reason: string; confidence: string; manual_review_required: boolean };
export type Assignment = { assigned_to: string; assigned_by: string; created_at: string };
export type OperatorIncident = { incident: Incident; routing: Routing | null; assignment: Assignment | null };
export type History = { previous_status: string; new_status: string; actor: string; source: string; created_at: string };

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...init, headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...init?.headers } });
  if (response.status === 401) throw new Error("The operator token was not accepted.");
  if (response.status === 403) throw new Error("This token is not permitted to perform that action.");
  if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(body?.detail ?? "The operator request failed."); }
  return response.json() as Promise<T>;
}
export const getQueue = (token: string, status = "") => request<OperatorIncident[]>(`/operator/incidents${status ? `?status=${status}` : ""}`, token);
export const getHistory = (token: string, id: number) => request<History[]>(`/operator/incidents/${id}/history`, token);
export const assignIncident = (token: string, id: number, assigned_to: string) => request<Assignment>(`/operator/incidents/${id}/assignment`, token, { method: "POST", body: JSON.stringify({ assigned_to }) });
export const addNote = (token: string, id: number, content: string) => request(`/operator/incidents/${id}/notes`, token, { method: "POST", body: JSON.stringify({ content }) });
export const updateStatus = (token: string, id: number, status: string) => request<Incident>(`/incidents/${id}`, token, { method: "PATCH", body: JSON.stringify({ status }) });
