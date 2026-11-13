"use client";
import { Activity, Database, FlaskConical, LayoutDashboard, Menu, Package, RefreshCw, Settings, Sparkles, Table2, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { useApi } from "@/lib/useApi";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/datasets", label: "Datasets", icon: Database },
  { href: "/training", label: "Model Training", icon: FlaskConical },
  { href: "/experiments", label: "Experiments", icon: Table2 },
  { href: "/registry", label: "Model Registry", icon: Package },
  { href: "/predictions", label: "Predictions", icon: Sparkles },
  { href: "/monitoring", label: "Monitoring", icon: Activity },
  { href: "/retraining", label: "Retraining", icon: RefreshCw },
  { href: "/settings", label: "Settings", icon: Settings },
];

function BackendStatus() {
  const { data, error } = useApi<{ status: string; mlflow: string }>("/api/health");
  const ok = data?.status === "ok" && data.mlflow === "ok";
  const text = error ? "Backend offline" : !data ? "Connecting…" : ok ? "All services online" : "MLflow unreachable";
  return (
    <div className="flex items-center gap-2 text-xs text-slate-400">
      <span className={`h-2 w-2 rounded-full ${error ? "bg-bad" : ok ? "bg-ok" : "bg-warn"}`} /> {text}
    </div>
  );
}

export default function Shell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const nav = (
    <nav className="flex-1 space-y-1 px-3 py-4">
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? path === "/" : path.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            onClick={() => setOpen(false)}
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
              active ? "bg-brand-soft text-white" : "text-slate-400 hover:bg-navy-700 hover:text-white"
            }`}
          >
            <Icon className="h-4 w-4" /> {label}
          </Link>
        );
      })}
    </nav>
  );
  const brand = (
    <div className="flex items-center gap-2 px-5 py-5">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-sm font-bold text-white">M</div>
      <div>
        <div className="text-base font-semibold leading-tight text-white">MLOps360</div>
        <div className="text-[11px] text-slate-400">Churn model lifecycle</div>
      </div>
    </div>
  );
  return (
    <div className="min-h-screen lg:flex">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-navy-700 bg-navy-950 lg:flex">
        {brand}
        {nav}
        <div className="border-t border-navy-700 p-4"><BackendStatus /></div>
      </aside>

      <header className="flex items-center justify-between border-b border-navy-700 bg-navy-950 px-4 py-3 lg:hidden">
        <div className="flex items-center gap-2 text-white"><div className="flex h-7 w-7 items-center justify-center rounded-md bg-brand text-xs font-bold">M</div> MLOps360</div>
        <button aria-label="Toggle menu" onClick={() => setOpen(!open)} className="rounded-md p-1.5 text-slate-300 hover:bg-navy-700">
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </header>
      {open && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div className="flex w-64 flex-col bg-navy-950">{brand}{nav}<div className="border-t border-navy-700 p-4"><BackendStatus /></div></div>
          <div className="flex-1 bg-black/60" onClick={() => setOpen(false)} />
        </div>
      )}

      <main className="min-w-0 flex-1 px-4 py-6 sm:px-8 lg:py-8">
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
