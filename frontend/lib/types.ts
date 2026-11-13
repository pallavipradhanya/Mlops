export type Metrics = { accuracy: number; precision: number; recall: number; f1: number; roc_auc: number };

export type Dataset = {
  id: number; name: string; version: number; sha256: string; rows: number; columns: number;
  churn_rate: number | null; source: string; dvc_tracked: boolean; dvc_md5: string | null; created_at: string;
};
export type Experiment = {
  id: number; run_id: string; algorithm: string; dataset_id: number | null; params: Record<string, unknown>;
  metrics: Metrics; confusion_matrix: number[][]; trigger: string; registered_version: number | null; created_at: string;
};
export type ModelVersion = {
  version: number; run_id: string; algorithm: string; dataset_id: number | null; metrics: Metrics;
  status: "champion" | "previous" | "challenger" | "rejected" | "archived"; note: string | null; created_at: string;
};
export type ModelsResponse = { model_name: string; champion_version: number | null; versions: ModelVersion[] };

export type DriftColumn = { column: string; method: string; threshold: number; value: number; drifted: boolean };
export type MonitoringReport = {
  id: number; status: "completed" | "insufficient_data" | "no_model" | "error"; message: string | null;
  model_version: number | null; reference_rows: number; current_rows: number; dataset_drift: boolean | null;
  drift_share: number | null; threshold: number | null; columns: DriftColumn[] | null;
  prediction_drift: (Partial<DriftColumn> & {
    reference_mean: number; current_mean: number; reference_positive_rate: number; current_positive_rate: number;
  }) | null;
  has_html: boolean; created_at: string;
};
export type RetrainingRun = {
  id: number; trigger: string; status: "skipped" | "promoted" | "rejected" | "error"; drift_detected: boolean | null;
  dataset_id: number | null; candidate_version: number | null; champion_version: number | null;
  candidate_metrics: Metrics | null; champion_metrics: Metrics | null; reason: string | null; created_at: string;
};
export type Activity = { id: number; event: string; message: string; created_at: string };
export type PredictionRecord = {
  id: number; model_version: number; input: Record<string, string | number | null>;
  probability: number; label: number; created_at: string;
};
export type Overview = {
  counts: Record<"datasets" | "experiments" | "models" | "predictions" | "drift_reports" | "retraining_runs", number>;
  champion: ModelVersion | null; last_drift_report: MonitoringReport | null; last_retraining: RetrainingRun | null;
  model_history: ({ version: number; status: string } & Metrics)[];
  predictions_per_day: { date: string; count: number }[]; recent_activity: Activity[];
};
export type SystemInfo = {
  mlflow_ui_url: string; mlflow_tracking_uri: string; database_url: string; model_name: string;
  scheduler: { running: boolean; enabled: boolean; next_run: string | null };
  versions: Record<string, string>; paths: Record<string, string>;
};
export type SettingsResponse = {
  values: Record<string, number>; defaults: Record<string, number>; limits: Record<string, [number, number]>;
};
