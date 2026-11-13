"use client";
import { RotateCcw } from "lucide-react";
import { Badge, Button, Card, Empty, ErrorBox, Loading, Notice, PageHeader, Table, Td } from "@/components/ui";
import { api } from "@/lib/api";
import { dateTime, label, num } from "@/lib/format";
import type { ModelsResponse } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

export default function RegistryPage() {
  const { data, error, loading, reload } = useApi<ModelsResponse>("/api/models");
  const act = useAction();
  const go = async (fn: () => Promise<unknown>, ok: string) => { if ((await act.run(fn, () => ok)) !== undefined) await reload(); };
  const hasPrevious = data?.versions.some((v) => v.status === "previous");

  return (
    <>
      <PageHeader
        title="Model Registry"
        subtitle="Versions registered in MLflow. The champion serves predictions; the previous champion is always kept so you can roll back instantly."
        actions={<Button variant="secondary" disabled={!hasPrevious} busy={act.busy} onClick={() => void go(() => api.post("/api/models/rollback"), "Rolled back to the previous champion.")}><RotateCcw className="h-4 w-4" /> Roll back</Button>}
      />
      <div className="mb-4 space-y-3">{act.error && <ErrorBox message={act.error} />}{act.notice && <Notice message={act.notice} />}</div>
      <Card title={data ? `Registered model: ${data.model_name}` : "Versions"}>
        {loading && !data ? <Loading /> : error ? <ErrorBox message={error} /> : !data?.versions.length ? (
          <Empty title="No model versions yet">Train a model to register version 1.</Empty>
        ) : (
          <Table head={["Version", "Status", "Algorithm", "ROC-AUC", "F1", "Recall", "Precision", "Dataset", "Created", "Note", "Actions"]}>
            {data.versions.map((v) => (
              <tr key={v.version}>
                <Td><strong>v{v.version}</strong></Td><Td><Badge kind={v.status}>{v.status}</Badge></Td><Td>{label(v.algorithm)}</Td>
                <Td>{num(v.metrics.roc_auc)}</Td><Td>{num(v.metrics.f1)}</Td><Td>{num(v.metrics.recall)}</Td><Td>{num(v.metrics.precision)}</Td>
                <Td>#{v.dataset_id}</Td><Td>{dateTime(v.created_at)}</Td>
                <Td className="max-w-xs truncate text-xs text-slate-400" ><span title={v.note ?? ""}>{v.note ?? "—"}</span></Td>
                <Td>
                  <div className="flex gap-2">
                    {v.status !== "champion" && <Button variant="secondary" className="!px-2 !py-1 text-xs" disabled={act.busy} onClick={() => void go(() => api.post(`/api/models/${v.version}/promote`), `v${v.version} is now the champion.`)}>Promote</Button>}
                    {v.status === "challenger" && <Button variant="danger" className="!px-2 !py-1 text-xs" disabled={act.busy} onClick={() => void go(() => api.post(`/api/models/${v.version}/reject`, { reason: "Rejected manually" }), `v${v.version} rejected.`)}>Reject</Button>}
                  </div>
                </Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
      <p className="mt-3 text-xs text-slate-500">Promotion moves the MLflow alias <code>champion</code>. Rollback swaps <code>champion</code> and <code>previous</code>. Nothing is deleted.</p>
    </>
  );
}
