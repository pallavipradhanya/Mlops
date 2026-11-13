"use client";
import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { Badge, Button, Card, ErrorBox, Field, Loading, Notice, PageHeader, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { dateTime, label } from "@/lib/format";
import type { Activity, SettingsResponse, SystemInfo } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

const HINTS: Record<string, string> = {
  drift_share_threshold: "Share of drifted features that counts as dataset drift (0–1)",
  min_current_rows: "Logged predictions needed before drift is tested",
  monitoring_window: "Most recent predictions used as the current dataset",
  min_roc_auc: "Absolute ROC-AUC floor for promoting any model",
  min_improvement: "Margin a candidate must beat the champion by on F1 and ROC-AUC (negative = tolerance)",
  schedule_hours: "Scheduled retraining interval in hours (0 = off)",
};

export default function SettingsPage() {
  const cfg = useApi<SettingsResponse>("/api/settings");
  const sys = useApi<SystemInfo>("/api/system");
  const health = useApi<{ status: string; database: string; mlflow: string }>("/api/health");
  const log = useApi<Activity[]>("/api/activity?limit=40");
  const act = useAction();
  const [draft, setDraft] = useState<Record<string, string>>({});

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (cfg.data) setDraft(Object.fromEntries(Object.entries(cfg.data.values).map(([k, v]) => [k, String(v)])));
  }, [cfg.data]);

  const save = async () => {
    const values = Object.fromEntries(Object.entries(draft).map(([k, v]) => [k, Number(v)]));
    if (await act.run(() => api.put("/api/settings", { values }), () => "Settings saved.")) { await cfg.reload(); await sys.reload(); }
  };

  return (
    <>
      <PageHeader title="System Settings" subtitle="Thresholds are stored in SQLite and take effect immediately." />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Monitoring & retraining thresholds">
          {!cfg.data ? (cfg.error ? <ErrorBox message={cfg.error} /> : <Loading />) : (
            <div className="space-y-4">
              {Object.keys(cfg.data.values).map((k) => (
                <Field key={k} label={label(k)} hint={`${HINTS[k] ?? ""} · allowed ${cfg.data!.limits[k][0]} to ${cfg.data!.limits[k][1]}`}>
                  <input type="number" step="any" className={inputCls} value={draft[k] ?? ""} onChange={(e) => setDraft({ ...draft, [k]: e.target.value })} />
                </Field>
              ))}
              <div className="flex gap-2">
                <Button busy={act.busy} onClick={() => void save()}>Save settings</Button>
                <Button variant="secondary" onClick={() => setDraft(Object.fromEntries(Object.entries(cfg.data!.defaults).map(([k, v]) => [k, String(v)])))}>Restore defaults</Button>
              </div>
              {act.error && <ErrorBox message={act.error} />}{act.notice && <Notice message={act.notice} />}
            </div>
          )}
        </Card>

        <div className="space-y-4">
          <Card title="Service health">
            {health.error ? <ErrorBox message={health.error} /> : !health.data ? <Loading /> : (
              <ul className="space-y-2 text-sm">
                {[["API", health.data.status], ["SQLite", health.data.database], ["MLflow", health.data.mlflow]].map(([n, s]) => (
                  <li key={n} className="flex justify-between"><span className="text-slate-400">{n}</span><Badge kind={s === "ok" ? "ok" : "error"}>{s}</Badge></li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Environment" right={sys.data && <a className="inline-flex items-center gap-1 text-xs text-brand hover:underline" target="_blank" rel="noreferrer" href={sys.data.mlflow_ui_url}>MLflow UI <ExternalLink className="h-3 w-3" /></a>}>
            {!sys.data ? <Loading /> : (
              <dl className="space-y-2 text-sm">
                {Object.entries(sys.data.versions).map(([k, v]) => <div key={k} className="flex justify-between"><dt className="text-slate-400">{k}</dt><dd>{v}</dd></div>)}
                <div className="flex justify-between"><dt className="text-slate-400">Scheduler</dt><dd>{sys.data.scheduler.enabled ? `on · next ${dateTime(sys.data.scheduler.next_run)}` : "off"}</dd></div>
                <div className="flex justify-between gap-4"><dt className="shrink-0 text-slate-400">Tracking URI</dt><dd className="truncate text-xs" title={sys.data.mlflow_tracking_uri}>{sys.data.mlflow_tracking_uri}</dd></div>
                <div className="flex justify-between gap-4"><dt className="shrink-0 text-slate-400">Database</dt><dd className="truncate text-xs" title={sys.data.database_url}>{sys.data.database_url}</dd></div>
              </dl>
            )}
          </Card>
        </div>
      </div>

      <Card title="Activity log" className="mt-4">
        {!log.data ? (log.error ? <ErrorBox message={log.error} /> : <Loading />) : (
          <ul className="max-h-96 divide-y divide-navy-700 overflow-y-auto text-sm">
            {log.data.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span className="flex items-center gap-2"><Badge>{a.event}</Badge><span className="text-slate-300">{a.message}</span></span>
                <span className="text-xs text-slate-500">{dateTime(a.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
