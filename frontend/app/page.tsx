"use client";
import Link from "next/link";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Card, Empty, ErrorBox, Loading, Metric, PageHeader, chartTheme } from "@/components/ui";
import { dateTime, num, pct } from "@/lib/format";
import type { Overview } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function OverviewPage() {
  const { data, error, loading } = useApi<Overview>("/api/overview");
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;
  const { counts, champion, last_drift_report: drift, last_retraining: retrain } = data;

  return (
    <>
      <PageHeader title="Overview" subtitle="Live status of the whole ML lifecycle: data, models, serving, drift and retraining." />
      {!champion && (
        <Card className="mb-6">
          <Empty title="No model is deployed yet">
            Start by <Link className="text-brand underline" href="/datasets">adding a dataset</Link>, then{" "}
            <Link className="text-brand underline" href="/training">train a model</Link>. The first model you train goes live automatically.
          </Empty>
        </Card>
      )}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Metric label="Champion model" value={champion ? `v${champion.version}` : "—"} hint={champion ? champion.algorithm.replace("_", " ") : "none deployed"} />
        <Metric label="ROC-AUC" value={num(champion?.metrics.roc_auc)} hint="held-out test set" />
        <Metric label="F1-score" value={num(champion?.metrics.f1)} hint={`recall ${pct(champion?.metrics.recall)}`} />
        <Metric label="Predictions served" value={counts.predictions.toLocaleString()} hint="logged to SQLite" />
        <Metric label="Datasets" value={counts.datasets} hint="versioned" />
        <Metric label="Experiment runs" value={counts.experiments} hint={`${counts.models} registered versions`} />
        <Metric
          label="Data drift"
          value={!drift ? "Not run" : drift.status !== "completed" ? "Waiting" : drift.dataset_drift ? "Detected" : "None"}
          tone={drift?.status === "completed" ? (drift.dataset_drift ? "bad" : "ok") : undefined}
          hint={drift ? (drift.status === "completed" ? `${pct(drift.drift_share, 0)} of features drifted` : drift.status.replace("_", " ")) : "run a drift check"}
        />
        <Metric label="Last retraining" value={retrain ? retrain.status : "None yet"} hint={retrain ? dateTime(retrain.created_at) : `${counts.retraining_runs} runs`} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card title="Model quality by registered version">
          {data.model_history.length === 0 ? <Empty title="No registered versions yet" /> : (
            <div className="h-64">
              <ResponsiveContainer>
                <LineChart data={data.model_history.map((m) => ({ ...m, name: `v${m.version}` }))}>
                  <CartesianGrid stroke={chartTheme.grid} strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke={chartTheme.axis} fontSize={12} />
                  <YAxis domain={[0, 1]} stroke={chartTheme.axis} fontSize={12} />
                  <Tooltip contentStyle={chartTheme.tooltip} formatter={(v) => Number(v).toFixed(3)} />
                  <Legend />
                  <Line type="monotone" dataKey="roc_auc" name="ROC-AUC" stroke={chartTheme.colors[0]} strokeWidth={2} />
                  <Line type="monotone" dataKey="f1" name="F1" stroke={chartTheme.colors[1]} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
        <Card title="Predictions per day">
          {data.predictions_per_day.length === 0 ? <Empty title="No predictions logged yet" /> : (
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={data.predictions_per_day}>
                  <CartesianGrid stroke={chartTheme.grid} strokeDasharray="3 3" />
                  <XAxis dataKey="date" stroke={chartTheme.axis} fontSize={12} />
                  <YAxis allowDecimals={false} stroke={chartTheme.axis} fontSize={12} />
                  <Tooltip contentStyle={chartTheme.tooltip} />
                  <Bar dataKey="count" name="Predictions" fill={chartTheme.colors[0]} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      <Card title="Recent activity" className="mt-4">
        {data.recent_activity.length === 0 ? <Empty title="Nothing has happened yet" /> : (
          <ul className="divide-y divide-navy-700">
            {data.recent_activity.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
                <span className="flex items-center gap-2"><Badge kind={a.event.split(".")[1]}>{a.event}</Badge><span className="text-slate-300">{a.message}</span></span>
                <span className="text-xs text-slate-500">{dateTime(a.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
