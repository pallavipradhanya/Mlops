"use client";
import { useState } from "react";
import { Activity } from "lucide-react";
import { Badge, Button, Card, Empty, ErrorBox, Loading, Metric, Notice, PageHeader, Table, Td } from "@/components/ui";
import { API_URL, api } from "@/lib/api";
import { dateTime, num, pct } from "@/lib/format";
import type { MonitoringReport } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

export default function MonitoringPage() {
  const reports = useApi<MonitoringReport[]>("/api/monitoring/reports");
  const act = useAction();
  const [selected, setSelected] = useState<number | null>(null);
  const current = reports.data?.find((r) => r.id === selected) ?? reports.data?.[0] ?? null;

  const run = async () => {
    const r = await act.run(() => api.post<MonitoringReport>("/api/monitoring/run"));
    if (r) { setSelected(r.id); await reports.reload(); }
  };
  const drifted = current?.columns?.filter((c) => c.drifted && c.column !== "prediction") ?? [];
  const featureCols = current?.columns?.filter((c) => c.column !== "prediction") ?? [];

  return (
    <>
      <PageHeader
        title="Model Monitoring"
        subtitle="Evidently compares the champion's training sample (reference) with recently logged predictions (current). Results are never estimated: with too little data you get an explicit 'insufficient data' status."
        actions={<Button busy={act.busy} onClick={() => void run()}><Activity className="h-4 w-4" /> Run drift check</Button>}
      />
      {act.error && <div className="mb-4"><ErrorBox message={act.error} /></div>}
      {reports.loading && !reports.data ? <Loading /> : reports.error ? <ErrorBox message={reports.error} /> : !current ? (
        <Card><Empty title="No drift reports yet">Serve some predictions, then run a drift check. Tip: score a CSV on the Predictions page, or run <code>python scripts/simulate_traffic.py</code>.</Empty></Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Metric label="Status" value={<Badge kind={current.status}>{current.status.replace("_", " ")}</Badge>} hint={`report #${current.id} · ${dateTime(current.created_at)}`} />
            <Metric label="Dataset drift" value={current.dataset_drift === null ? "—" : current.dataset_drift ? "Detected" : "Not detected"} tone={current.dataset_drift === null ? undefined : current.dataset_drift ? "bad" : "ok"} hint={`model v${current.model_version ?? "—"}`} />
            <Metric label="Drifted features" value={current.status === "completed" ? `${drifted.length} / ${featureCols.length}` : "—"} hint={current.status === "completed" ? `${pct(current.drift_share, 0)} vs threshold ${pct(current.threshold, 0)}` : undefined} />
            <Metric label="Rows compared" value={`${current.current_rows} / ${current.reference_rows || "—"}`} hint="current / reference" />
          </div>
          {current.message && (current.status === "completed" ? <div className="mt-4"><Notice message={current.message} /></div> : <div className="mt-4"><ErrorBox message={current.message} /></div>)}

          {current.status === "completed" && current.columns && (
            <div className="mt-4 grid gap-4 lg:grid-cols-[2fr_1fr]">
              <Card title="Feature-level drift">
                <Table head={["Feature", "Test", "Statistic", "Threshold", "Result"]}>
                  {[...featureCols].sort((a, b) => Number(b.drifted) - Number(a.drifted)).map((c) => (
                    <tr key={c.column}><Td>{c.column}</Td><Td className="text-xs text-slate-400">{c.method}</Td><Td>{num(c.value, 4)}</Td><Td>{c.threshold}</Td><Td>{c.drifted ? <Badge kind="error">drifted</Badge> : <Badge kind="ok">stable</Badge>}</Td></tr>
                  ))}
                </Table>
                <p className="mt-2 text-xs text-slate-500">p-value tests are flagged when the statistic is below the threshold. Large samples make tiny shifts significant, so check the effect size in the full report.</p>
              </Card>
              <Card title="Prediction distribution">
                {current.prediction_drift && (
                  <dl className="space-y-3 text-sm">
                    <div className="flex justify-between"><dt className="text-slate-400">Result</dt><dd>{current.prediction_drift.drifted ? <Badge kind="error">shifted</Badge> : <Badge kind="ok">stable</Badge>}</dd></div>
                    <div className="flex justify-between"><dt className="text-slate-400">Mean churn probability</dt><dd>{pct(current.prediction_drift.reference_mean)} → {pct(current.prediction_drift.current_mean)}</dd></div>
                    <div className="flex justify-between"><dt className="text-slate-400">Predicted churn rate</dt><dd>{pct(current.prediction_drift.reference_positive_rate)} → {pct(current.prediction_drift.current_positive_rate)}</dd></div>
                  </dl>
                )}
                <p className="mt-4 rounded-lg bg-navy-900 p-3 text-xs text-slate-400">Drift means inputs changed. It does <em>not</em> prove the model got worse; retraining only promotes a new model if it beats the champion on held-out data.</p>
              </Card>
            </div>
          )}

          {current.has_html && (
            <Card title="Full Evidently report" className="mt-4" right={<a className="text-xs text-brand hover:underline" target="_blank" rel="noreferrer" href={`${API_URL}/api/monitoring/reports/${current.id}/html`}>Open in new tab</a>}>
              <iframe title={`Drift report ${current.id}`} src={`${API_URL}/api/monitoring/reports/${current.id}/html`} className="h-[640px] w-full rounded-lg border border-navy-700 bg-white" />
            </Card>
          )}

          <Card title="Report history" className="mt-4">
            <Table head={["Report", "Status", "Model", "Rows", "Drift share", "Dataset drift", "Time", ""]}>
              {reports.data!.map((r) => (
                <tr key={r.id} className={r.id === current.id ? "bg-brand-soft/30" : ""}>
                  <Td>#{r.id}</Td><Td><Badge kind={r.status}>{r.status.replace("_", " ")}</Badge></Td><Td>v{r.model_version ?? "—"}</Td><Td>{r.current_rows}</Td>
                  <Td>{pct(r.drift_share, 0)}</Td><Td>{r.dataset_drift === null ? "—" : r.dataset_drift ? "yes" : "no"}</Td><Td>{dateTime(r.created_at)}</Td>
                  <Td><button className="text-xs text-brand hover:underline" onClick={() => setSelected(r.id)}>View</button></Td>
                </tr>
              ))}
            </Table>
          </Card>
        </>
      )}
    </>
  );
}
