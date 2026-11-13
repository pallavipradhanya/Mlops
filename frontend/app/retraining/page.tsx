"use client";
import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { Badge, Button, Card, Empty, ErrorBox, Field, Loading, Notice, PageHeader, Table, Td, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { dateTime, num } from "@/lib/format";
import type { Dataset, RetrainingRun, SettingsResponse, SystemInfo } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

export default function RetrainingPage() {
  const history = useApi<RetrainingRun[]>("/api/retraining/history");
  const datasets = useApi<Dataset[]>("/api/datasets");
  const cfg = useApi<SettingsResponse>("/api/settings");
  const sys = useApi<SystemInfo>("/api/system");
  const act = useAction();
  const [datasetId, setDatasetId] = useState<number | null>(null);
  const selected = datasetId ?? datasets.data?.[0]?.id ?? null;

  const trigger = async (t: "manual" | "drift" | "scheduled") => {
    const r = await act.run(() => api.post<RetrainingRun>("/api/retraining/run", { trigger: t, dataset_id: selected }),
      (x) => `Run #${x.id}: ${x.status}. ${x.reason ?? ""}`);
    if (r) await history.reload();
  };
  const v = cfg.data?.values;

  return (
    <>
      <PageHeader title="Automated Retraining" subtitle="Check drift → train a candidate → compare with the champion on the same held-out data → promote only if it passes. The previous champion is always preserved for rollback." />
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Card title="Run retraining now">
          <div className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
            <Field label="Training dataset (new labeled data)">
              <select className={inputCls} value={selected ?? ""} onChange={(e) => setDatasetId(Number(e.target.value))} disabled={!datasets.data?.length}>
                {datasets.data?.map((d) => <option key={d.id} value={d.id}>#{d.id} · {d.name} v{d.version} · {d.rows} rows</option>)}
              </select>
            </Field>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button busy={act.busy} disabled={selected === null} onClick={() => void trigger("manual")}><RefreshCw className="h-4 w-4" /> Manual retrain</Button>
            <Button variant="secondary" busy={act.busy} disabled={selected === null} onClick={() => void trigger("drift")}>Drift-triggered check</Button>
            <Button variant="secondary" busy={act.busy} disabled={selected === null} onClick={() => void trigger("scheduled")}>Run scheduled check</Button>
          </div>
          <ul className="mt-4 space-y-1 text-xs text-slate-400">
            <li><strong className="text-slate-300">Manual</strong>: always trains a candidate.</li>
            <li><strong className="text-slate-300">Drift-triggered</strong>: trains only if Evidently confirms dataset drift (skipped otherwise, including when there is too little data).</li>
            <li><strong className="text-slate-300">Scheduled</strong>: trains if drift is detected or the dataset is newer than the one behind the champion.</li>
          </ul>
          <div className="mt-4 space-y-3">{act.error && <ErrorBox message={act.error} />}{act.notice && <Notice message={act.notice} />}</div>
        </Card>
        <Card title="Promotion rules">
          {!v ? <Loading /> : (
            <ul className="space-y-2 text-sm text-slate-300">
              <li>ROC-AUC ≥ <strong className="text-white">{v.min_roc_auc}</strong></li>
              <li>F1 and ROC-AUC ≥ champion + <strong className="text-white">{v.min_improvement}</strong></li>
              <li>Drift threshold: <strong className="text-white">{Math.round(v.drift_share_threshold * 100)}%</strong> of features</li>
              <li>Schedule: <strong className="text-white">{v.schedule_hours ? `every ${v.schedule_hours} h` : "disabled"}</strong>{sys.data?.scheduler.next_run && <span className="block text-xs text-slate-500">next run {dateTime(sys.data.scheduler.next_run)}</span>}</li>
            </ul>
          )}
          <p className="mt-3 text-xs text-slate-500">Edit these on the Settings page. Windows Task Scheduler alternative: <code>scripts/schedule_retraining.ps1</code>.</p>
        </Card>
      </div>

      <Card title="Retraining history" className="mt-4">
        {history.loading && !history.data ? <Loading /> : history.error ? <ErrorBox message={history.error} /> : !history.data?.length ? <Empty title="No retraining runs yet" /> : (
          <Table head={["Run", "Trigger", "Outcome", "Drift", "Dataset", "Champion → Candidate", "ROC-AUC (champ → cand)", "F1 (champ → cand)", "Reason", "Time"]}>
            {history.data.map((r) => (
              <tr key={r.id}>
                <Td>#{r.id}</Td><Td><Badge>{r.trigger}</Badge></Td><Td><Badge kind={r.status}>{r.status}</Badge></Td>
                <Td>{r.drift_detected === null ? "n/a" : r.drift_detected ? "yes" : "no"}</Td><Td>{r.dataset_id ? `#${r.dataset_id}` : "—"}</Td>
                <Td>{r.champion_version ? `v${r.champion_version}` : "—"} → {r.candidate_version ? `v${r.candidate_version}` : "—"}</Td>
                <Td>{num(r.champion_metrics?.roc_auc)} → {num(r.candidate_metrics?.roc_auc)}</Td>
                <Td>{num(r.champion_metrics?.f1)} → {num(r.candidate_metrics?.f1)}</Td>
                <Td className="max-w-md whitespace-normal text-xs text-slate-400">{r.reason}</Td><Td>{dateTime(r.created_at)}</Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
