"use client";
import { useRef, useState } from "react";
import { Sparkles, Upload } from "lucide-react";
import { Badge, Button, Card, Empty, ErrorBox, Field, Loading, Notice, PageHeader, Table, Td, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { dateTime, pct, riskColor } from "@/lib/format";
import type { PredictionRecord } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

type Form = Record<string, string | number>;
type Result = { model_version: number; id: number; probability: number; label: number; risk: string };

const YN = ["Yes", "No"];
const ADDON = ["No internet service", "No", "Yes"];
const CHOICES: Record<string, string[]> = {
  gender: ["Female", "Male"], Partner: YN, Dependents: YN, PhoneService: YN, PaperlessBilling: YN,
  MultipleLines: ["No phone service", "No", "Yes"], InternetService: ["DSL", "Fiber optic", "No"],
  OnlineSecurity: ADDON, OnlineBackup: ADDON, DeviceProtection: ADDON, TechSupport: ADDON, StreamingTV: ADDON, StreamingMovies: ADDON,
  Contract: ["Month-to-month", "One year", "Two year"],
  PaymentMethod: ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"],
  SeniorCitizen: ["0", "1"],
};
const NUMERIC = ["tenure", "MonthlyCharges", "TotalCharges"];

export default function PredictionsPage() {
  const sample = useApi<Form>("/api/predict/sample");
  const history = useApi<{ total: number; items: PredictionRecord[] }>("/api/predictions?limit=25");
  const act = useAction();
  const batch = useAction();
  const fileRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState<Form | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const values = form ?? sample.data;

  const submit = async () => {
    if (!values) return;
    const body = { ...values, SeniorCitizen: Number(values.SeniorCitizen), tenure: Number(values.tenure), MonthlyCharges: Number(values.MonthlyCharges), TotalCharges: values.TotalCharges === "" ? null : Number(values.TotalCharges) };
    const r = await act.run(() => api.post<Result>("/api/predict", body));
    if (r) { setResult(r); void history.reload(); }
  };

  return (
    <>
      <PageHeader title="Predictions" subtitle="Scores customers with the current champion model. Every prediction is logged and later feeds drift monitoring." />
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Card title="Single customer" right={<Button variant="secondary" className="!px-2 !py-1 text-xs" onClick={() => { setForm(null); setResult(null); }}>Reset to sample</Button>}>
          {!values ? (sample.error ? <ErrorBox message={sample.error} /> : <Loading />) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {Object.keys(values).map((k) => (
                <Field key={k} label={k}>
                  {CHOICES[k] ? (
                    <select className={inputCls} value={String(values[k])} onChange={(e) => setForm({ ...values, [k]: e.target.value })}>
                      {CHOICES[k].map((o) => <option key={o}>{o}</option>)}
                    </select>
                  ) : (
                    <input type={NUMERIC.includes(k) ? "number" : "text"} step="any" min={0} className={inputCls} value={values[k] ?? ""} onChange={(e) => setForm({ ...values, [k]: e.target.value })} />
                  )}
                </Field>
              ))}
            </div>
          )}
          <div className="mt-4"><Button busy={act.busy} onClick={() => void submit()}><Sparkles className="h-4 w-4" /> Predict churn</Button></div>
          {act.error && <div className="mt-3"><ErrorBox message={act.error} /></div>}
        </Card>

        <div className="space-y-4">
          <Card title="Result">
            {!result ? <Empty title="No prediction yet">Fill the form and press Predict.</Empty> : (
              <div className="text-center">
                <div className={`text-4xl font-semibold ${riskColor(result.risk)}`}>{pct(result.probability)}</div>
                <div className="mt-1 text-sm text-slate-400">probability of churn</div>
                <div className="mx-auto mt-4 h-2 w-full overflow-hidden rounded-full bg-navy-700"><div className={`h-full ${result.risk === "high" ? "bg-bad" : result.risk === "medium" ? "bg-warn" : "bg-ok"}`} style={{ width: `${result.probability * 100}%` }} /></div>
                <div className="mt-4 flex justify-center gap-2"><Badge>{`${result.risk} risk`}</Badge><Badge>{result.label ? "likely to churn" : "likely to stay"}</Badge></div>
                <div className="mt-3 text-xs text-slate-500">Served by champion v{result.model_version}</div>
              </div>
            )}
          </Card>
          <Card title="Batch CSV">
            <p className="mb-3 text-xs text-slate-400">Upload customers (feature columns, no label needed; up to 5000 rows). All rows are logged for monitoring.</p>
            <input ref={fileRef} type="file" accept=".csv" className="mb-3 block w-full text-sm text-slate-300 file:mr-3 file:rounded-lg file:border-0 file:bg-navy-600 file:px-3 file:py-2 file:text-sm file:text-white" />
            <Button variant="secondary" busy={batch.busy} onClick={() => {
              const f = fileRef.current?.files?.[0];
              if (!f) return void batch.run(async () => { throw new Error("Choose a CSV file first"); });
              void batch.run(() => api.upload<{ count: number; churn_rate: number; model_version: number }>("/api/predict/batch", f), (r) => `Scored ${r.count} customers with v${r.model_version}; predicted churn rate ${pct(r.churn_rate)}.`).then(() => history.reload());
            }}><Upload className="h-4 w-4" /> Score file</Button>
            <div className="mt-3 space-y-2">{batch.error && <ErrorBox message={batch.error} />}{batch.notice && <Notice message={batch.notice} />}</div>
          </Card>
        </div>
      </div>

      <Card title={`Prediction log${history.data ? ` · ${history.data.total.toLocaleString()} total` : ""}`} className="mt-4">
        {history.loading && !history.data ? <Loading /> : !history.data?.items.length ? <Empty title="No predictions logged yet" /> : (
          <Table head={["ID", "Model", "Probability", "Label", "Contract", "Tenure", "Monthly", "Time"]}>
            {history.data.items.map((p) => (
              <tr key={p.id}><Td>#{p.id}</Td><Td>v{p.model_version}</Td><Td>{pct(p.probability)}</Td><Td>{p.label ? <Badge kind="error">churn</Badge> : <Badge kind="ok">stay</Badge>}</Td>
                <Td>{p.input.Contract}</Td><Td>{p.input.tenure}</Td><Td>{p.input.MonthlyCharges}</Td><Td>{dateTime(p.created_at)}</Td></tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
