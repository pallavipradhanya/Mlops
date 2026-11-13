"use client";
import { ExternalLink } from "lucide-react";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Button, Card, Empty, ErrorBox, Loading, PageHeader, Table, Td, chartTheme } from "@/components/ui";
import { dateTime, label, num } from "@/lib/format";
import type { Experiment, SystemInfo } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const KEYS = ["accuracy", "precision", "recall", "f1", "roc_auc"] as const;

export default function ExperimentsPage() {
  const exps = useApi<Experiment[]>("/api/experiments");
  const sys = useApi<SystemInfo>("/api/system");
  const [picked, setPicked] = useState<number[]>([]);
  const [algo, setAlgo] = useState("all");
  const rows = (exps.data ?? []).filter((e) => algo === "all" || e.algorithm === algo);
  const chosen = (exps.data ?? []).filter((e) => picked.includes(e.id));
  const toggle = (id: number) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length < 4 ? [...p, id] : p));
  const best = Math.max(...rows.map((r) => r.metrics.roc_auc), 0);

  return (
    <>
      <PageHeader
        title="Experiment Tracking"
        subtitle="Every training run, with hyper-parameters, metrics and the dataset it used. Select up to 4 runs to compare."
        actions={sys.data && <a href={sys.data.mlflow_ui_url} target="_blank" rel="noreferrer"><Button variant="secondary"><ExternalLink className="h-4 w-4" /> Open MLflow UI</Button></a>}
      />
      {chosen.length >= 2 && (
        <Card title="Run comparison" className="mb-4">
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={KEYS.map((k) => ({ metric: label(k), ...Object.fromEntries(chosen.map((c) => [`#${c.id} ${label(c.algorithm)}`, c.metrics[k]])) }))}>
                <CartesianGrid stroke={chartTheme.grid} strokeDasharray="3 3" />
                <XAxis dataKey="metric" stroke={chartTheme.axis} fontSize={12} /><YAxis domain={[0, 1]} stroke={chartTheme.axis} fontSize={12} />
                <Tooltip contentStyle={chartTheme.tooltip} formatter={(v) => Number(v).toFixed(3)} /><Legend />
                {chosen.map((c, i) => <Bar key={c.id} dataKey={`#${c.id} ${label(c.algorithm)}`} fill={chartTheme.colors[i]} radius={[4, 4, 0, 0]} />)}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}
      <Card title="All runs" right={
        <select className="rounded-lg border border-navy-600 bg-navy-900 px-2 py-1 text-xs text-white" value={algo} onChange={(e) => setAlgo(e.target.value)}>
          <option value="all">All algorithms</option><option value="logistic_regression">Logistic Regression</option><option value="random_forest">Random Forest</option>
        </select>}>
        {exps.loading && !exps.data ? <Loading /> : exps.error ? <ErrorBox message={exps.error} /> : rows.length === 0 ? (
          <Empty title="No experiments yet">Train a model to create the first tracked run.</Empty>
        ) : (
          <Table head={["Compare", "Run", "Algorithm", "Dataset", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC", "Registered", "Trigger", "Date"]}>
            {rows.map((e) => (
              <tr key={e.id} className={e.metrics.roc_auc === best ? "bg-emerald-500/5" : ""}>
                <Td><input type="checkbox" checked={picked.includes(e.id)} onChange={() => toggle(e.id)} aria-label={`Compare run ${e.id}`} /></Td>
                <Td><span className="font-mono text-xs">{e.run_id.slice(0, 8)}</span></Td>
                <Td>{label(e.algorithm)}</Td><Td>#{e.dataset_id}</Td>
                {KEYS.map((k) => <Td key={k}>{num(e.metrics[k])}</Td>)}
                <Td>{e.registered_version ? <Badge kind="challenger">{`v${e.registered_version}`}</Badge> : "—"}</Td>
                <Td><Badge>{e.trigger}</Badge></Td><Td>{dateTime(e.created_at)}</Td>
              </tr>
            ))}
          </Table>
        )}
        <details className="mt-4 text-sm text-slate-400">
          <summary className="cursor-pointer text-slate-300">Hyper-parameters of selected runs</summary>
          {chosen.length === 0 ? <p className="mt-2">Tick a run to see its parameters.</p> : chosen.map((c) => (
            <pre key={c.id} className="scroll-thin mt-2 overflow-x-auto rounded-lg bg-navy-950 p-3 text-xs">#{c.id} {label(c.algorithm)}: {JSON.stringify(c.params)}</pre>
          ))}
        </details>
      </Card>
    </>
  );
}
