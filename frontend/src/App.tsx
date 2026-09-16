import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { Report, submitReport } from "./api/reports";

const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
const maxBytes = 10 * 1024 * 1024;
const statusLabel: Record<string, string> = { submitted: "Report received", analyzed: "Report reviewed", assigned: "Dispatched to repair crew", in_progress: "Repair in progress", resolved: "Road repaired" };
const title = (value: string | null) => value ? value[0].toUpperCase() + value.slice(1) : "Pending";

function MapPicker({ latitude, longitude, onChange }: { latitude: string; longitude: string; onChange: (latitude: string, longitude: string) => void }) {
  const [notice, setNotice] = useState("");
  const useLocation = () => {
    if (!navigator.geolocation) return setNotice("We couldn't access your location. Select your location on the map.");
    setNotice("Locating you…");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => { onChange(coords.latitude.toFixed(6), coords.longitude.toFixed(6)); setNotice("Location found. Confirm or adjust it below."); },
      () => setNotice("We couldn't access your location. Select your location on the map."),
    );
  };
  return <section className="field-group"><div className="field-heading"><h2>2. Confirm location</h2><p>Choose your location before submitting.</p></div>
    <button type="button" className="secondary" onClick={useLocation}>Use current location</button>
    <div className="map" aria-label="Location map preview" role="img"><span className="map-grid" /><span className="map-pin" /> <strong>Location preview</strong><small>{latitude && longitude ? `${latitude}, ${longitude}` : "Select a location"}</small></div>
    {notice && <p className="notice" role="status">{notice}</p>}
    <div className="coordinates"><label>Latitude<input aria-label="Latitude" type="number" step="any" value={latitude} onChange={e => onChange(e.target.value, longitude)} /></label><label>Longitude<input aria-label="Longitude" type="number" step="any" value={longitude} onChange={e => onChange(latitude, e.target.value)} /></label></div>
  </section>;
}

function Result({ report, onNew }: { report: Report; onNew: () => void }) {
  const duplicate = report.analysis.duplicate_analysis;
  return <main className="shell result"><p className="eyebrow">Report received</p><h1>Thank you for reporting this pothole.</h1><p className="report-number">Report #{report.report_id}</p><div className="result-card"><dl><dt>Issue</dt><dd>Pothole detected</dd><dt>Severity</dt><dd>{title(report.incident.severity)}</dd><dt>Priority</dt><dd>{title(report.analysis.analysis.priority_level)}</dd><dt>Status</dt><dd>{statusLabel[report.incident.status]}</dd></dl></div>{duplicate && <aside className="notice"><strong>A nearby report may describe the same pothole.</strong><br />Your report was still received.</aside>}<button onClick={onNew}>Report another pothole</button></main>;
}

export function App() {
  const [description, setDescription] = useState(""); const [latitude, setLatitude] = useState(""); const [longitude, setLongitude] = useState("");
  const [photo, setPhoto] = useState<File | null>(null); const [preview, setPreview] = useState(""); const [error, setError] = useState(""); const [submitting, setSubmitting] = useState(false); const [report, setReport] = useState<Report | null>(null);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  const selectPhoto = (event: ChangeEvent<HTMLInputElement>) => { const file = event.target.files?.[0]; setError(""); if (!file) return; if (!allowedTypes.includes(file.type)) return setError("Use a JPEG, PNG, or WEBP image."); if (file.size > maxBytes) return setError("Photo must be 10 MB or less."); if (preview) URL.revokeObjectURL(preview); setPhoto(file); setPreview(URL.createObjectURL(file)); };
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(""); if (!photo) return setError("Add a photo before submitting."); if (description.trim().length < 5) return setError("Describe the pothole in at least 5 characters."); const lat = Number(latitude), lng = Number(longitude); if (!Number.isFinite(lat) || lat < -90 || lat > 90 || !Number.isFinite(lng) || lng < -180 || lng > 180) return setError("Select a valid location before submitting."); setSubmitting(true); try { const received = await submitReport({ description: description.trim(), latitude: lat, longitude: lng, photo }); setReport(received); } catch (reason) { setError(reason instanceof Error ? reason.message : "We couldn't submit your report. Please try again."); } finally { setSubmitting(false); } };
  if (report) return <Result report={report} onNew={() => setReport(null)} />;
  return <main className="shell"><header><p className="brand">CivicLens</p><h1>Report a pothole</h1><p>Help your city find and repair damaged roads.</p></header><form onSubmit={submit} noValidate><section className="field-group"><div className="field-heading"><h2>1. Add photo</h2><p>Take a clear photo of the pothole.</p></div>{preview ? <div className="preview"><img src={preview} alt="Selected pothole" /><button type="button" className="text-button" onClick={() => { URL.revokeObjectURL(preview); setPreview(""); setPhoto(null); }}>Remove photo</button></div> : <label className="upload"><input aria-label="Add photo" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={selectPhoto} /><span>Add photo</span><small>JPEG, PNG, or WEBP · 10 MB maximum</small></label>}</section><MapPicker latitude={latitude} longitude={longitude} onChange={(lat, lng) => { setLatitude(lat); setLongitude(lng); }} /><section className="field-group"><div className="field-heading"><h2>3. What did you notice?</h2><p>Keep it short and helpful.</p></div><label className="sr-only" htmlFor="description">Description</label><textarea id="description" placeholder="Describe the pothole..." value={description} onChange={e => setDescription(e.target.value)} maxLength={1000} /></section>{error && <p className="error" role="alert">{error}</p>}<button className="submit" disabled={submitting}>{submitting ? "Submitting report…" : "Submit report"}</button></form></main>;
}
