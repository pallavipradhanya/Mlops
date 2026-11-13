"use client";
import { AlertTriangle, CheckCircle2, Inbox, Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ title, right, children, className = "" }: {
  title?: string; right?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`rounded-xl border border-navy-700 bg-navy-800 p-5 shadow-sm ${className}`}>
      {(title || right) && (
        <div className="mb-4 flex items-center justify-between gap-2">
          {title && <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">{title}</h2>}
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

export function Metric({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: ReactNode; tone?: "ok" | "warn" | "bad" }) {
  const color = tone === "ok" ? "text-ok" : tone === "warn" ? "text-warn" : tone === "bad" ? "text-bad" : "text-white";
  return (
    <div className="rounded-xl border border-navy-700 bg-navy-800 p-4">
      <div className="text-xs font-medium uppercase tracking-wider text-slate-400">{label}</div>
      <div className={`mt-2 text-2xl font-semibold ${color}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

const BADGE: Record<string, string> = {
  champion: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  promoted: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  completed: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  ok: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  challenger: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  previous: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  archived: "bg-slate-500/10 text-slate-400 border-slate-600/30",
  skipped: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  rejected: "bg-red-500/15 text-red-300 border-red-500/30",
  error: "bg-red-500/15 text-red-300 border-red-500/30",
  drift: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  insufficient_data: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  no_model: "bg-amber-500/15 text-amber-300 border-amber-500/30",
};

export function Badge({ children, kind }: { children: ReactNode; kind?: string }) {
  const cls = BADGE[kind ?? String(children)] ?? "bg-slate-500/15 text-slate-300 border-slate-500/30";
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${cls}`}>{children}</span>;
}

export function Button({ variant = "primary", busy, children, className = "", ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger"; busy?: boolean;
}) {
  const styles = {
    primary: "bg-brand text-white hover:bg-blue-500",
    secondary: "border border-navy-600 bg-navy-700 text-slate-200 hover:bg-navy-600",
    danger: "border border-red-500/40 bg-red-500/10 text-red-300 hover:bg-red-500/20",
  }[variant];
  return (
    <button
      {...rest}
      disabled={rest.disabled || busy}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
    >
      {busy && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export const inputCls =
  "w-full rounded-lg border border-navy-600 bg-navy-900 px-3 py-2 text-sm text-white outline-none focus:border-brand";

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wider text-slate-400">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export function Loading({ text = "Loading…" }: { text?: string }) {
  return (
    <div className="flex items-center gap-2 py-10 text-sm text-slate-400">
      <Loader2 className="h-4 w-4 animate-spin" /> {text}
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> <span>{message}</span>
    </div>
  );
}

export function Notice({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">
      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> <span>{message}</span>
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center">
      <Inbox className="h-8 w-8 text-slate-500" />
      <div className="text-sm font-medium text-slate-300">{title}</div>
      {children && <div className="max-w-md text-sm text-slate-400">{children}</div>}
    </div>
  );
}

export function Table({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <div className="scroll-thin overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-navy-700 text-xs uppercase tracking-wider text-slate-400">
            {head.map((h) => <th key={h} className="whitespace-nowrap px-3 py-2 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-navy-700/70">{children}</tbody>
      </table>
    </div>
  );
}

export const Td = ({ children, className = "" }: { children: ReactNode; className?: string }) => (
  <td className={`whitespace-nowrap px-3 py-2.5 text-slate-200 ${className}`}>{children}</td>
);

export const chartTheme = {
  grid: "#26345a", axis: "#94a3b8", tooltip: { background: "#111a2e", border: "1px solid #26345a", borderRadius: 8, color: "#e5ecff" },
  colors: ["#4f8cff", "#34d399", "#fbbf24", "#f87171", "#a78bfa"],
};
