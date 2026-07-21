import { useState } from "react";
import { Navigate, NavLink, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, AuthError } from "./lib/api";
import { useAuthStore } from "./store/auth";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof AuthError) return false;
        return failureCount < 1;
      },
      refetchOnWindowFocus: false,
    },
  },
});

const nav = [
  ["/", "Dashboard"],
  ["/tickets", "Tickets"],
  ["/alerts", "Alertas"],
  ["/incidents", "Incidentes"],
  ["/users", "Usuarios"],
  ["/metrics", "Métricas"],
  ["/history", "Historial"],
  ["/settings", "Configuración"],
] as const;

function Shell({ children }: { children: React.ReactNode }) {
  const logout = useAuthStore((s) => s.logout);
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  return (
    <div className="mx-auto flex min-h-screen max-w-[1440px]">
      <aside className="flex w-64 flex-col border-r border-[var(--line)] bg-white/80 px-4 py-6 backdrop-blur">
        <div className="mb-8 px-2">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-700">SupportMind AI</p>
          <h1 className="text-lg font-semibold text-slate-900">Agent Console</h1>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {nav.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-4 border-t border-[var(--line)] pt-4 text-sm text-slate-500">
          <p className="font-medium text-slate-800">{me.data?.full_name ?? "…"}</p>
          <p className="mb-3 text-xs">{me.data?.email}</p>
          <button type="button" onClick={logout} className="text-xs text-rose-700 hover:underline">
            Cerrar sesión
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  );
}

function LoginPage() {
  const setToken = useAuthStore((s) => s.setToken);
  const navigate = useNavigate();
  const [email, setEmail] = useState("lucia@supportmind.ai");
  const [password, setPassword] = useState("Agent123!");
  const [error, setError] = useState<string | null>(null);
  const login = useMutation({
    mutationFn: () => api.login(email, password),
    onSuccess: (data) => {
      setToken(data.access_token);
      localStorage.setItem("sm_refresh_token", data.refresh_token);
      navigate("/");
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          login.mutate();
        }}
        className="w-full max-w-md rounded-2xl border border-[var(--line)] bg-white p-8 shadow-sm"
      >
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">SupportMind AI</p>
        <h1 className="mb-1 text-2xl font-semibold">Portal de agentes</h1>
        <p className="mb-6 text-sm text-slate-500">Ingresá con tu cuenta ITSM</p>
        <label className="mb-3 block text-sm">
          Email
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="mb-4 block text-sm">
          Password
          <input
            type="password"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <p className="mb-3 text-sm text-rose-600">{error}</p>}
        <button
          type="submit"
          className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white"
        >
          Entrar
        </button>
      </form>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-2xl border border-[var(--line)] bg-white p-5 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function DashboardPage() {
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: api.metrics, refetchInterval: 10000 });
  const alerts = useQuery({ queryKey: ["alerts"], queryFn: api.alerts });
  const tickets = useQuery({ queryKey: ["tickets"], queryFn: api.tickets });
  const m = metrics.data;
  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <p className="text-sm text-slate-500">Operación en tiempo real · CELU + agentes humanos</p>
      </header>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Tickets abiertos" value={m?.open_tickets ?? "—"} />
        <Stat label="Alertas pendientes" value={m?.pending_alerts ?? "—"} />
        <Stat label="Incidentes activos" value={m?.active_incidents ?? "—"} />
        <Stat label="P1" value={m?.avg_priority_p1 ?? "—"} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-[var(--line)] bg-white p-5">
          <h3 className="mb-3 font-semibold">Alertas CELU</h3>
          <div className="space-y-2">
            {(alerts.data ?? []).slice(0, 5).map((a) => (
              <div key={a.id} className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm">
                {a.public_title} · {a.ticket_count} tickets / {a.window_seconds}s
              </div>
            ))}
            {!alerts.data?.length && <p className="text-sm text-slate-500">Sin alertas pendientes</p>}
          </div>
        </section>
        <section className="rounded-2xl border border-[var(--line)] bg-white p-5">
          <h3 className="mb-3 font-semibold">Últimos tickets</h3>
          <div className="space-y-2">
            {(tickets.data ?? []).slice(0, 6).map((t) => (
              <NavLink key={t.id} to={`/tickets/${t.id}`} className="block rounded-xl border border-slate-100 px-3 py-2 text-sm hover:bg-slate-50">
                <span className="font-medium">{t.number}</span> · {t.priority} · {t.status} — {t.summary_ai.slice(0, 70)}…
              </NavLink>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function TicketsPage() {
  const tickets = useQuery({ queryKey: ["tickets"], queryFn: api.tickets });
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold">Tickets</h2>
      <div className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Número</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Prioridad</th>
              <th className="px-4 py-3">Cliente</th>
              <th className="px-4 py-3">Categoría</th>
              <th className="px-4 py-3">SLA</th>
            </tr>
          </thead>
          <tbody>
            {(tickets.data ?? []).map((t) => (
              <tr key={t.id} className="border-t border-slate-100 hover:bg-slate-50/80">
                <td className="px-4 py-3">
                  <NavLink className="font-medium text-teal-800 hover:underline" to={`/tickets/${t.id}`}>
                    {t.number}
                  </NavLink>
                </td>
                <td className="px-4 py-3">{t.status}</td>
                <td className="px-4 py-3">{t.priority}</td>
                <td className="px-4 py-3">
                  {t.customer_first_name} {t.customer_last_name}
                </td>
                <td className="px-4 py-3">{t.category}</td>
                <td className="px-4 py-3">
                  {t.sla_remaining_seconds != null
                    ? `${Math.floor(t.sla_remaining_seconds / 60)}m`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TicketDetailPage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const ticket = useQuery({ queryKey: ["ticket", id], queryFn: () => api.ticket(id) });
  const [comment, setComment] = useState("");
  const transition = useMutation({
    mutationFn: (status: string) => api.transition(id, status),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["ticket", id] }),
  });
  const addComment = useMutation({
    mutationFn: () => api.comment(id, comment),
    onSuccess: () => {
      setComment("");
      void qc.invalidateQueries({ queryKey: ["ticket", id] });
    },
  });
  const t = ticket.data;
  if (!t) return <p>Cargando…</p>;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Ticket</p>
          <h2 className="text-2xl font-semibold">{t.number}</h2>
          <p className="text-sm text-slate-500">Creado por {t.created_by} · sentimiento {t.sentiment}</p>
        </div>
        <div className="flex gap-2">
          {["open", "pending", "resolved", "closed"].map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => transition.mutate(s)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs capitalize"
            >
              {s}
            </button>
          ))}
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <section className="space-y-3 rounded-2xl border border-[var(--line)] bg-white p-5 lg:col-span-2">
          <h3 className="font-semibold">Resumen IA</h3>
          <p className="text-sm leading-relaxed text-slate-700">{t.summary_ai}</p>
          <h3 className="pt-2 font-semibold">Conversación CELU</h3>
          <div className="space-y-2">
            {t.conversation_transcript.map((step, i) => (
              <div key={i} className="rounded-xl bg-slate-50 px-3 py-2 text-sm">
                <p className="text-slate-500">{step.prompt}</p>
                <p className="font-medium">{step.answer}</p>
              </div>
            ))}
          </div>
          <h3 className="pt-2 font-semibold">Historial</h3>
          <div className="space-y-2">
            {t.events.map((e, i) => (
              <div key={i} className="border-l-2 border-teal-600 pl-3 text-sm">
                <p className="font-medium">{e.message}</p>
                <p className="text-xs text-slate-500">
                  {e.actor} · {e.event_type}
                </p>
              </div>
            ))}
          </div>
          <form
            className="flex gap-2 pt-2"
            onSubmit={(e) => {
              e.preventDefault();
              addComment.mutate();
            }}
          >
            <input
              className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
              placeholder="Nota interna"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
            <button type="submit" className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white">
              Comentar
            </button>
          </form>
        </section>
        <aside className="space-y-3 rounded-2xl border border-[var(--line)] bg-white p-5 text-sm">
          <Row label="Estado" value={t.status} />
          <Row label="Prioridad" value={t.priority} />
          <Row label="Categoría" value={t.category} />
          <Row label="Cliente" value={`${t.customer_first_name} ${t.customer_last_name}`} />
          <Row label="Email" value={t.customer_email} />
          <Row
            label="SLA restante"
            value={
              t.sla_remaining_seconds != null
                ? `${Math.floor(t.sla_remaining_seconds / 60)} min`
                : "—"
            }
          />
          <Row label="Incidente" value={t.incident_id ?? "—"} />
          <p className="pt-2 text-slate-600">{t.description}</p>
        </aside>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}

function AlertsPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const alerts = useQuery({ queryKey: ["alerts"], queryFn: api.alerts, refetchInterval: 5000 });
  const [reason, setReason] = useState("No corresponde a un incidente sistémico");
  const [detailId, setDetailId] = useState<string | null>(null);
  const [level, setLevel] = useState("l2");
  const [showManual, setShowManual] = useState(false);
  const [manual, setManual] = useState({
    title: "",
    problem_code: "",
    public_message: "",
    fingerprint: "",
    escalation_level: "l2",
  });

  const detail = useQuery({
    queryKey: ["alert-detail", detailId],
    queryFn: () => api.alertDetail(detailId!),
    enabled: Boolean(detailId),
  });

  const accept = useMutation({
    mutationFn: (id: string) => api.acceptAlert(id, level),
    onSuccess: (incident) => {
      void qc.invalidateQueries({ queryKey: ["alerts"] });
      void qc.invalidateQueries({ queryKey: ["incidents"] });
      void qc.invalidateQueries({ queryKey: ["tickets"] });
      navigate(`/incidents/${incident.id}`);
    },
  });
  const reject = useMutation({
    mutationFn: (id: string) => api.rejectAlert(id, reason),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
  const createManual = useMutation({
    mutationFn: () =>
      api.createManualIncident({
        title: manual.title,
        problem_code: manual.problem_code,
        public_message: manual.public_message,
        fingerprint: manual.fingerprint || undefined,
        escalation_level: manual.escalation_level,
      }),
    onSuccess: (incident) => {
      setShowManual(false);
      void qc.invalidateQueries({ queryKey: ["incidents"] });
      void qc.invalidateQueries({ queryKey: ["tickets"] });
      navigate(`/incidents/${incident.id}`);
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Alertas</h2>
          <p className="text-sm text-slate-500">
            CELU propone incidentes. El agente de turno decide y puede escalar a L2/L3.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowManual((v) => !v)}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white"
        >
          Crear alerta / incidente
        </button>
      </div>

      {showManual && (
        <form
          className="space-y-3 rounded-2xl border border-[var(--line)] bg-white p-5"
          onSubmit={(e) => {
            e.preventDefault();
            createManual.mutate();
          }}
        >
          <h3 className="font-semibold">Crear alerta / incidente manual</h3>
          <p className="text-sm text-slate-500">
            Uso exclusivo del agente de turno para convocar equipos de Nivel 2 o 3.
          </p>
          <input
            required
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            placeholder="Título del incidente"
            value={manual.title}
            onChange={(e) => setManual((m) => ({ ...m, title: e.target.value }))}
          />
          <input
            required
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            placeholder="Código de problema (ej: no_power)"
            value={manual.problem_code}
            onChange={(e) => setManual((m) => ({ ...m, problem_code: e.target.value }))}
          />
          <textarea
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            placeholder="Mensaje público / motivo de convocatoria"
            value={manual.public_message}
            onChange={(e) => setManual((m) => ({ ...m, public_message: e.target.value }))}
          />
          <input
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            placeholder="Fingerprint opcional (para asociar tickets existentes)"
            value={manual.fingerprint}
            onChange={(e) => setManual((m) => ({ ...m, fingerprint: e.target.value }))}
          />
          <select
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={manual.escalation_level}
            onChange={(e) => setManual((m) => ({ ...m, escalation_level: e.target.value }))}
          >
            <option value="l2">Escalar a Nivel 2</option>
            <option value="l3">Escalar a Nivel 3</option>
          </select>
          <button type="submit" className="rounded-lg bg-teal-700 px-4 py-2 text-sm text-white">
            Crear incidente padre
          </button>
          {createManual.isError && (
            <p className="text-sm text-rose-600">{(createManual.error as Error).message}</p>
          )}
        </form>
      )}

      <div className="flex items-center gap-2 text-sm">
        <span className="text-slate-500">Al aceptar, escalar a:</span>
        <select
          className="rounded-lg border border-slate-200 px-2 py-1"
          value={level}
          onChange={(e) => setLevel(e.target.value)}
        >
          <option value="l2">Nivel 2</option>
          <option value="l3">Nivel 3</option>
        </select>
      </div>

      <div className="space-y-3">
        {(alerts.data ?? []).map((a) => (
          <div key={a.id} className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
            <h3 className="font-semibold text-amber-950">{a.public_title}</h3>
            <p className="mt-1 text-sm text-amber-900/80">
              Código {a.problem_code} · {a.ticket_count} tickets en {a.window_seconds}s
            </p>
            <p className="mt-2 text-sm">¿Desea crear un incidente?</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setDetailId(detailId === a.id ? null : a.id)}
                className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm"
              >
                Detalle
              </button>
              <button
                type="button"
                onClick={() => accept.mutate(a.id)}
                className="rounded-lg bg-teal-700 px-4 py-2 text-sm text-white"
              >
                Aceptar / crear incidente
              </button>
              <input
                className="min-w-[240px] flex-1 rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              <button
                type="button"
                onClick={() => reject.mutate(a.id)}
                className="rounded-lg border border-rose-300 bg-white px-4 py-2 text-sm text-rose-700"
              >
                Rechazar
              </button>
            </div>

            {detailId === a.id && detail.data && (
              <div className="mt-4 space-y-3 rounded-xl border border-amber-200 bg-white p-4 text-sm">
                <p className="font-medium text-slate-800">¿Por qué es necesaria esta alerta?</p>
                <p className="text-slate-600">{detail.data.reason}</p>
                <p className="text-xs text-slate-500">
                  Fingerprint: {detail.data.fingerprint} · Detectada:{" "}
                  {new Date(detail.data.created_at).toLocaleString()}
                </p>
                <p className="font-medium">Tickets que dispararon la correlación</p>
                <div className="space-y-2">
                  {detail.data.tickets.map((t) => (
                    <div key={t.id} className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                      <p className="font-medium">
                        {t.number} · {t.priority} · {t.status}
                      </p>
                      <p className="text-xs text-slate-500">
                        {t.customer_name} · {t.customer_email} ·{" "}
                        {new Date(t.created_at).toLocaleString()}
                      </p>
                      <p className="mt-1 text-slate-700">{t.summary_ai || t.description}</p>
                    </div>
                  ))}
                  {!detail.data.tickets.length && (
                    <p className="text-slate-500">Sin tickets asociados en el detalle.</p>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
        {!alerts.data?.length && (
          <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
            No hay solicitudes de alerta pendientes
          </p>
        )}
      </div>
    </div>
  );
}

function IncidentsPage() {
  const qc = useQueryClient();
  const { id } = useParams();
  const incidents = useQuery({ queryKey: ["incidents"], queryFn: api.incidents });
  const selectedId = id ?? null;
  const detail = useQuery({
    queryKey: ["incident", selectedId],
    queryFn: () => api.incident(selectedId!),
    enabled: Boolean(selectedId),
  });
  const resolve = useMutation({
    mutationFn: (incidentId: string) => api.resolveIncident(incidentId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["incidents"] });
      if (selectedId) void qc.invalidateQueries({ queryKey: ["incident", selectedId] });
    },
  });

  if (selectedId) {
    const i = detail.data;
    if (!i) return <p>Cargando incidente…</p>;
    return (
      <div className="space-y-5">
        <NavLink to="/incidents" className="text-sm text-teal-800 hover:underline">
          ← Volver a incidentes
        </NavLink>
        <div className="rounded-2xl border border-teal-200 bg-teal-50 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-teal-800">
            Ticket padre incidente
          </p>
          <h2 className="text-2xl font-semibold text-teal-950">{i.number}</h2>
          <p className="mt-1 font-medium">{i.title}</p>
          <p className="mt-2 text-sm text-teal-900/80">{i.public_message}</p>
          <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <Row label="Estado" value={i.status} />
            <Row label="Código" value={i.problem_code} />
            <Row label="Escalamiento" value={(i.escalation_level ?? "l2").toUpperCase()} />
            <Row label="Tickets hijos" value={String(i.ticket_ids?.length ?? 0)} />
            <Row label="Creado" value={new Date(i.created_at).toLocaleString()} />
            <Row label="Fingerprint" value={i.fingerprint ?? "—"} />
          </div>
          {i.status === "active" && (
            <button
              type="button"
              onClick={() => resolve.mutate(i.id)}
              className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white"
            >
              Resolver incidente
            </button>
          )}
        </div>

        <section className="space-y-3">
          <h3 className="text-lg font-semibold">Tickets hijos asociados</h3>
          <p className="text-sm text-slate-500">
            Estos tickets no aparecen en la ticketera principal; viven bajo el incidente padre.
          </p>
          {(i.child_tickets ?? []).map((t) => (
            <div key={t.id} className="rounded-2xl border border-[var(--line)] bg-white p-4 text-sm">
              <p className="font-medium">
                {t.number} · {t.priority} · {t.status}
              </p>
              <p className="text-xs text-slate-500">
                {t.customer_first_name} {t.customer_last_name} · {t.customer_email} ·{" "}
                {new Date(t.created_at).toLocaleString()}
              </p>
              <p className="mt-2 text-slate-700">{t.summary_ai}</p>
              <p className="mt-1 text-slate-500">{t.description}</p>
            </div>
          ))}
          {!i.child_tickets?.length && (
            <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
              Todavía no hay tickets hijos asociados
            </p>
          )}
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold">Incidentes</h2>
      <p className="text-sm text-slate-500">
        Cada incidente es un ticket padre. Los reportes correlacionados viven como hijos.
      </p>
      <div className="grid gap-3">
        {(incidents.data ?? []).map((i) => (
          <div key={i.id} className="rounded-2xl border border-[var(--line)] bg-white p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
                  Ticket padre incidente
                </p>
                <p className="text-xs uppercase text-slate-500">{i.number}</p>
                <h3 className="font-semibold">{i.title}</h3>
                <p className="mt-1 text-sm text-slate-600">{i.public_message}</p>
                <p className="mt-2 text-xs text-slate-500">
                  {i.ticket_ids.length} tickets hijos · {i.status} ·{" "}
                  {(i.escalation_level ?? "l2").toUpperCase()}
                </p>
              </div>
              <div className="flex gap-2">
                <NavLink
                  to={`/incidents/${i.id}`}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                >
                  Ver detalle
                </NavLink>
                {i.status === "active" && (
                  <button
                    type="button"
                    onClick={() => resolve.mutate(i.id)}
                    className="rounded-lg bg-slate-900 px-3 py-2 text-sm text-white"
                  >
                    Resolver
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function UsersPage() {
  const agents = useQuery({ queryKey: ["agents"], queryFn: api.agents });
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold">Usuarios</h2>
      <div className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Roles</th>
              <th className="px-4 py-3">Disponibilidad</th>
            </tr>
          </thead>
          <tbody>
            {(agents.data ?? []).map((a) => (
              <tr key={a.id} className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium">{a.full_name}</td>
                <td className="px-4 py-3">{a.email}</td>
                <td className="px-4 py-3">{a.roles.join(", ")}</td>
                <td className="px-4 py-3">{a.availability}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MetricsPage() {
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: api.metrics });
  const priorityData = Object.entries(metrics.data?.tickets_by_priority ?? {}).map(([name, value]) => ({
    name,
    value,
  }));
  const statusData = Object.entries(metrics.data?.tickets_by_status ?? {}).map(([name, value]) => ({
    name,
    value,
  }));
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Métricas</h2>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Tickets por prioridad" data={priorityData} />
        <ChartCard title="Tickets por estado" data={statusData} />
      </div>
    </div>
  );
}

function ChartCard({ title, data }: { title: string; data: { name: string; value: number }[] }) {
  return (
    <div className="rounded-2xl border border-[var(--line)] bg-white p-5">
      <h3 className="mb-4 font-semibold">{title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="name" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="value" fill="#0f766e" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function HistoryPage() {
  const audit = useQuery({ queryKey: ["audit"], queryFn: api.audit });
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold">Historial / Auditoría</h2>
      <div className="space-y-2">
        {(audit.data ?? []).map((e) => (
          <div key={e.id} className="rounded-xl border border-[var(--line)] bg-white px-4 py-3 text-sm">
            <p className="font-medium">{e.action}</p>
            <p className="text-xs text-slate-500">
              {e.actor} · {e.resource_type}/{e.resource_id} · {new Date(e.created_at).toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function SettingsPage() {
  const trees = useQuery({ queryKey: ["trees"], queryFn: api.trees });
  const sla = useQuery({ queryKey: ["sla"], queryFn: api.sla });
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Configuración</h2>
      <section className="rounded-2xl border border-[var(--line)] bg-white p-5">
        <h3 className="mb-3 font-semibold">Árboles CELU</h3>
        {(trees.data ?? []).map((t) => (
          <div key={t.id} className="border-t border-slate-100 py-2 text-sm first:border-0">
            <p className="font-medium">{t.name}</p>
            <p className="text-slate-500">
              {t.slug} · v{t.version} · {t.is_active ? "activo" : "inactivo"}
            </p>
          </div>
        ))}
      </section>
      <section className="rounded-2xl border border-[var(--line)] bg-white p-5">
        <h3 className="mb-3 font-semibold">Políticas SLA</h3>
        {(sla.data ?? []).map((p) => (
          <div key={p.priority} className="border-t border-slate-100 py-2 text-sm first:border-0">
            {p.priority}: respuesta {p.response_minutes}m · resolución {p.resolution_minutes}m
          </div>
        ))}
      </section>
    </div>
  );
}

function Protected() {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/tickets" element={<TicketsPage />} />
        <Route path="/tickets/:id" element={<TicketDetailPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/incidents/:id" element={<IncidentsPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/metrics" element={<MetricsPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Shell>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/*" element={<Protected />} />
      </Routes>
    </QueryClientProvider>
  );
}
