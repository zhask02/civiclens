import { useEffect, useState } from "react";
import { getReport, getReports, ReportDetail, ReportListItem } from "./api/reports";

const stages = [["submitted", "Report received"], ["analyzed", "Report reviewed"], ["assigned", "Dispatched to repair crew"], ["in_progress", "Repair in progress"], ["resolved", "Road repaired"]] as const;
const label = (value: string | null) => value ? value[0].toUpperCase() + value.slice(1) : "Pending";
const date = (value: string) => new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));

export function StatusTimeline({ status }: { status: string }) {
  const current = stages.findIndex(([value]) => value === status);
  return <ol className="timeline" aria-label="Report lifecycle">{stages.map(([value, text], index) => <li key={value} className={index < current ? "done" : index === current ? "current" : "upcoming"}><span aria-hidden="true">{index < current ? "✓" : index === current ? "●" : "○"}</span><div><strong>{text}</strong>{index === current && <small>Current status</small>}</div></li>)}</ol>;
}

export function MyReports({ openReport }: { openReport: (id: number) => void }) {
  const [reports, setReports] = useState<ReportListItem[] | null>(null); const [error, setError] = useState("");
  useEffect(() => { getReports().then(setReports).catch(error => setError(error.message)); }, []);
  return <main className="shell"><header><p className="brand">CivicLens</p><h1>Reports</h1><p>Track the pothole reports in CivicLens.</p></header>{error ? <p className="error" role="alert">{error}</p> : reports === null ? <p className="notice" role="status">Loading reports…</p> : reports.length === 0 ? <section className="empty"><h2>No pothole reports yet.</h2><p>Start by reporting a pothole you see on the road.</p><a href="#/">Report a pothole</a></section> : <div className="report-list">{reports.map(report => <button className="report-row" key={report.report_id} onClick={() => openReport(report.report_id)}><span><strong>Report #{report.report_id}</strong><small>{date(report.created_at)}</small><p>{report.description}</p></span><span className="report-meta"><b>{label(report.status)}</b>{report.severity && <small>{label(report.severity)} severity</small>}</span></button>)}</div>}</main>;
}

function Details({ report }: { report: ReportDetail }) {
  return <main className="shell"><a className="back" href="#/reports">← Reports</a><header><p className="eyebrow">{label(report.incident.status)}</p><h1>Report #{report.report_id}</h1><p>Submitted {date(report.incident.created_at)}</p></header>{report.evidence_url && <img className="report-photo" src={report.evidence_url} alt={`Evidence for report ${report.report_id}`} />}<section className="detail-section"><h2>What you reported</h2><p>{report.incident.description}</p></section><section className="detail-section"><h2>Location</h2><p>{report.incident.latitude.toFixed(6)}, {report.incident.longitude.toFixed(6)}</p></section>{report.analysis && <section className="detail-section"><h2>Assessment</h2><dl><dt>Issue</dt><dd>Pothole</dd><dt>Severity</dt><dd>{label(report.analysis.severity)}</dd><dt>Priority</dt><dd>{label(report.analysis.priority_level)}</dd></dl>{report.analysis.requires_review && <p className="notice">This report may need additional review.</p>}</section>}<section className="detail-section"><h2>What happens next</h2><StatusTimeline status={report.incident.status} /></section></main>;
}

export function ReportDetailPage({ reportId }: { reportId: number }) {
  const [report, setReport] = useState<ReportDetail | null>(null); const [error, setError] = useState("");
  useEffect(() => { getReport(reportId).then(setReport).catch(error => setError(error.message)); }, [reportId]);
  if (error) return <main className="shell"><a className="back" href="#/reports">← Reports</a><p className="error" role="alert">{error}</p></main>;
  if (!report) return <main className="shell"><p className="notice" role="status">Loading report…</p></main>;
  return <Details report={report} />;
}
