"use client";
import { useRef, useState } from "react";
import { Database, Download, Sparkles, Upload } from "lucide-react";
import { Badge, Button, Card, Empty, ErrorBox, Field, Loading, Notice, PageHeader, Table, Td, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { dateTime, pct, shortHash } from "@/lib/format";
import type { Dataset } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

type Result = { dataset: Dataset; created: boolean };
type Preview = { columns: string[]; rows: Record<string, string>[]; missing: Record<string, number> };

export default function DatasetsPage() {
  const list = useApi<Dataset[]>("/api/datasets");
  const act = useAction();
  const fileRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [rows, setRows] = useState(5000);
  const [drift, setDrift] = useState(false);
  const [preview, setPreview] = useState<{ id: number; data: Preview } | null>(null);

  const done = async (p: Promise<Result | undefined>) => {
    const r = await p;
    if (r) await list.reload();
  };
  const msg = (r: Result) =>
    r.created ? `Registered "${r.dataset.name}" v${r.dataset.version} (${r.dataset.rows} rows).` : `Identical file already registered as dataset #${r.dataset.id}; nothing new was added.`;

  const showPreview = async (id: number) => {
    const data = await act.run(() => api.get<Preview>(`/api/datasets/${id}/preview`));
    if (data) setPreview({ id, data });
  };

  return (
    <>
      <PageHeader title="Dataset Management" subtitle="Every file is hashed (SHA-256) and registered as a version. Training runs record the exact dataset version they used." />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Upload CSV">
          <div className="space-y-3">
            <Field label="Dataset name (optional)"><input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="telco-q4" /></Field>
            <input ref={fileRef} type="file" accept=".csv" className="block w-full text-sm text-slate-300 file:mr-3 file:rounded-lg file:border-0 file:bg-navy-600 file:px-3 file:py-2 file:text-sm file:text-white" />
            <Button busy={act.busy} onClick={() => {
              const f = fileRef.current?.files?.[0];
              if (!f) return void act.run(async () => { throw new Error("Choose a CSV file first"); });
              void done(act.run(() => api.upload<Result>("/api/datasets/upload", f, { name }), msg));
            }}><Upload className="h-4 w-4" /> Upload &amp; register</Button>
            <p className="text-xs text-slate-500">Needs the IBM Telco columns plus a <code>Churn</code> column (Yes/No) and at least 200 rows.</p>
          </div>
        </Card>
        <Card title="IBM Telco dataset">
          <p className="mb-3 text-sm text-slate-400">Downloads the public IBM Telco Customer Churn CSV (7,043 rows). Needs internet once; the file is stored locally.</p>
          <Button busy={act.busy} onClick={() => void done(act.run(() => api.post<Result>("/api/datasets/download-telco"), msg))}>
            <Download className="h-4 w-4" /> Download dataset
          </Button>
        </Card>
        <Card title="Synthetic generator">
          <div className="space-y-3">
            <Field label="Rows"><input type="number" min={500} max={50000} className={inputCls} value={rows} onChange={(e) => setRows(Number(e.target.value))} /></Field>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={drift} onChange={(e) => setDrift(e.target.checked)} /> Shifted distribution (for drift demos)
            </label>
            <Button variant="secondary" busy={act.busy} onClick={() => void done(act.run(() => api.post<Result>("/api/datasets/generate", { rows, drift, seed: Math.floor(Math.random() * 10000) }), msg))}>
              <Sparkles className="h-4 w-4" /> Generate
            </Button>
          </div>
        </Card>
      </div>

      <div className="mt-4 space-y-3">
        {act.error && <ErrorBox message={act.error} />}
        {act.notice && <Notice message={act.notice} />}
      </div>

      <Card title="Dataset versions" className="mt-4">
        {list.loading && !list.data ? <Loading /> : list.error ? <ErrorBox message={list.error} /> : !list.data?.length ? (
          <Empty title="No datasets yet">Upload a CSV, download the IBM dataset, or generate synthetic data to begin.</Empty>
        ) : (
          <Table head={["ID", "Name", "Ver", "Rows", "Churn rate", "Source", "SHA-256", "DVC", "Created", ""]}>
            {list.data.map((d) => (
              <tr key={d.id}>
                <Td>#{d.id}</Td><Td>{d.name}</Td><Td>v{d.version}</Td><Td>{d.rows.toLocaleString()}</Td><Td>{pct(d.churn_rate)}</Td>
                <Td><Badge>{d.source}</Badge></Td><Td className="font-mono text-xs">{shortHash(d.sha256)}</Td>
                <Td>{d.dvc_tracked ? <Badge kind="ok">tracked {shortHash(d.dvc_md5)}</Badge> : <Badge kind="skipped">not tracked</Badge>}</Td>
                <Td>{dateTime(d.created_at)}</Td>
                <Td><button className="text-xs text-brand hover:underline" onClick={() => void showPreview(d.id)}>Preview</button></Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>

      {preview && (
        <Card title={`Preview of dataset #${preview.id}`} className="mt-4" right={<button className="text-xs text-slate-400 hover:text-white" onClick={() => setPreview(null)}>Close</button>}>
          {Object.keys(preview.data.missing).length > 0 && (
            <p className="mb-3 text-xs text-amber-300">Missing/blank cells: {Object.entries(preview.data.missing).map(([c, n]) => `${c} (${n})`).join(", ")}. Handled in the pipeline (imputation), never dropped silently.</p>
          )}
          <Table head={preview.data.columns}>
            {preview.data.rows.map((r, i) => <tr key={i}>{preview.data.columns.map((c) => <Td key={c} className="text-xs">{r[c]}</Td>)}</tr>)}
          </Table>
        </Card>
      )}

      <Card title="Versioning with DVC (local cache, no remote)" className="mt-4" right={<Database className="h-4 w-4 text-slate-500" />}>
        <p className="mb-2 text-sm text-slate-400">The app registers every dataset itself. To also version a file with DVC from the project root:</p>
        <pre className="scroll-thin overflow-x-auto rounded-lg bg-navy-950 p-3 text-xs text-slate-300">{`dvc init                      # once (needs git)
python scripts/prepare_data.py
dvc add data/telco_churn.csv
git add data/telco_churn.csv.dvc data/.gitignore && git commit -m "track dataset v1"
# after the file changes:
dvc add data/telco_churn.csv && git commit -am "dataset v2"
dvc repro                     # re-trains only when data, code or params changed`}</pre>
      </Card>
    </>
  );
}
