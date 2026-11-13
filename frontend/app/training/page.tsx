"use client";
import { useState } from "react";
import { Play } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Button, Card, Empty, ErrorBox, Field, Loading, Notice, PageHeader, chartTheme, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { label, num } from "@/lib/format";
import type { Dataset, Metrics } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

type Run = { algorithm: string; run_id: string; metrics: Metrics; confusion_matrix: number[][] };
type TrainResult = { version: number; stage: string; best_algorithm: string; runs: Run[] };
const ALGOS = ["logistic_regression", "random_forest"] as const;

function Confusion({ m }: { m: number[][] }) {
  const cells = [["True negative", m[0][0], "text-ok"], ["False positive", m[0][1], "text-warn"], ["False negative", m[1][0], "text-bad"], ["True positive", m[1][1], "text-ok"]] as const;
  return (
    <div className="grid grid-cols-2 gap-2 text-center">
      {cells.map(([name, v, c]) => (
        <div key={name} className="rounded-lg border border-navy-700 bg-navy-900 p-3">
          <div className={`text-xl font-semibold ${c}`}>{v}</div><div className="text-[11px] text-slate-400">{name}</div>
        </div>
      ))}
    </div>
  );
}

export default function TrainingPage() {
  const ds = useApi<Dataset[]>("/api/datasets");
  const act = useAction();
  const [datasetId, setDatasetId] = useState<number | null>(null);
  const [algos, setAlgos] = useState<string[]>([...ALGOS]);
  const [result, setResult] = useState<TrainResult | null>(null);
  const selected = datasetId ?? ds.data?.[0]?.id ?? null;

  const train = async () => {
    if (selected === null) return;
    const r = await act.run(() => api.post<TrainResult>("/api/train", { dataset_id: selected, algorithms: algos }),
      (x) => x.stage === "champion" ? `Model v${x.version} registered and deployed (first model).` : `Model v${x.version} registered as challenger. Promote it in the Model Registry when ready.`);
    if (r) setResult(r);
  };

  const chart = result ? ["accuracy", "precision", "recall", "f1", "roc_auc"].map((k) => ({
    metric: label(k), ...Object.fromEntries(result.runs.map((r) => [r.algorithm, r.metrics[k as keyof Metrics]])),
  })) : [];

  return (
    <>
      <PageHeader title="Model Training" subtitle="Trains the selected algorithms on a stratified train/test split. Preprocessing is fit on the training split only (no leakage). Every run is logged to MLflow." />
      <Card title="Configure run">
        {ds.loading && !ds.data ? <Loading /> : !ds.data?.length ? <Empty title="No datasets available">Add one on the Datasets page first.</Empty> : (
          <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
            <Field label="Dataset">
              <select className={inputCls} value={selected ?? ""} onChange={(e) => setDatasetId(Number(e.target.value))}>
                {ds.data.map((d) => <option key={d.id} value={d.id}>#{d.id} · {d.name} v{d.version} · {d.rows} rows</option>)}
              </select>
            </Field>
            <div>
              <span className="mb-1 block text-xs font-medium uppercase tracking-wider text-slate-400">Algorithms</span>
              <div className="flex gap-4 py-2 text-sm">
                {ALGOS.map((a) => (
                  <label key={a} className="flex items-center gap-2">
                    <input type="checkbox" checked={algos.includes(a)} onChange={(e) => setAlgos(e.target.checked ? [...algos, a] : algos.filter((x) => x !== a))} /> {label(a)}
                  </label>
                ))}
              </div>
            </div>
            <Button busy={act.busy} disabled={!algos.length} onClick={() => void train()}><Play className="h-4 w-4" /> {act.busy ? "Training…" : "Train"}</Button>
          </div>
        )}
        <p className="mt-3 text-xs text-slate-500">Hyper-parameters come from <code>params.yaml</code> (tracked by DVC). Training takes a few seconds on a laptop CPU.</p>
      </Card>
      <div className="mt-4 space-y-3">
        {act.error && <ErrorBox message={act.error} />}
        {act.notice && <Notice message={act.notice} />}
      </div>

      {result && (
        <>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card title="Metric comparison" right={<Badge kind={result.stage}>{`v${result.version} → ${result.stage}`}</Badge>}>
              <div className="h-72">
                <ResponsiveContainer>
                  <BarChart data={chart}>
                    <CartesianGrid stroke={chartTheme.grid} strokeDasharray="3 3" />
                    <XAxis dataKey="metric" stroke={chartTheme.axis} fontSize={12} />
                    <YAxis domain={[0, 1]} stroke={chartTheme.axis} fontSize={12} />
                    <Tooltip contentStyle={chartTheme.tooltip} formatter={(v) => Number(v).toFixed(3)} />
                    <Legend />
                    {result.runs.map((r, i) => <Bar key={r.algorithm} dataKey={r.algorithm} name={label(r.algorithm)} fill={chartTheme.colors[i]} radius={[4, 4, 0, 0]} />)}
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-xs text-slate-400">Best model (highest ROC-AUC, tie-break F1): <strong className="text-white">{label(result.best_algorithm)}</strong></p>
            </Card>
            <div className="grid gap-4">
              {result.runs.map((r) => (
                <Card key={r.run_id} title={`${label(r.algorithm)} · confusion matrix`} right={<span className="font-mono text-[11px] text-slate-500">run {r.run_id.slice(0, 8)}</span>}>
                  <div className="grid grid-cols-[1fr_1fr] gap-4">
                    <Confusion m={r.confusion_matrix} />
                    <dl className="space-y-1 text-sm">
                      {Object.entries(r.metrics).map(([k, v]) => (<div key={k} className="flex justify-between"><dt className="text-slate-400">{label(k)}</dt><dd className="font-medium text-white">{num(v)}</dd></div>))}
                    </dl>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </>
      )}
    </>
  );
}
