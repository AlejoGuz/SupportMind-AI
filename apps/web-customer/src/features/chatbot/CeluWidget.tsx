import { useEffect, useMemo, useState } from "react";
import { api, type ChatNode, type Product } from "../../lib/api";

type Message = { role: "celu" | "user"; text: string };

type Props = {
  open: boolean;
  onClose: () => void;
  products: Product[];
};

export function CeluWidget({ open, onClose, products }: Props) {
  const [node, setNode] = useState<ChatNode | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [productId, setProductId] = useState("");
  const [ticketNumber, setTicketNumber] = useState<string | null>(null);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    order_number: "",
    description: "",
  });
  const [error, setError] = useState<string | null>(null);

  const showEscalateForm = node?.node_type === "escalate" && !node.outcome && !ticketNumber;
  const done = Boolean(node?.outcome) || Boolean(ticketNumber);

  useEffect(() => {
    if (!open || node || !productId) return;
    void (async () => {
      setLoading(true);
      try {
        const started = await api.startSession(productId);
        setNode(started);
        setMessages([{ role: "celu", text: started.prompt }]);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error al iniciar CELU");
      } finally {
        setLoading(false);
      }
    })();
  }, [open, node, productId]);

  const productName = useMemo(
    () => products.find((p) => p.id === productId)?.name ?? "tu equipo",
    [products, productId],
  );

  async function choose(optionId: string, label: string) {
    if (!node || loading) return;
    setLoading(true);
    setError(null);
    setMessages((m) => [...m, { role: "user", text: label }]);
    try {
      const next = await api.answer(node.session_id, optionId);
      setNode(next);
      setMessages((m) => [...m, { role: "celu", text: next.prompt }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error en el flujo");
    } finally {
      setLoading(false);
    }
  }

  async function submitTicket(e: React.FormEvent) {
    e.preventDefault();
    if (!node) return;
    setLoading(true);
    setError(null);
    try {
      const ticket = (await api.escalate(node.session_id, {
        ...form,
        product_id: productId || products[0]?.id,
        description: form.description || `Soporte para ${productName}`,
      })) as { number: string; incident_id?: string | null };
      setTicketNumber(ticket.number);
      const linked = ticket.incident_id
        ? ` Tu reporte quedó asociado al incidente padre y no aparecerá suelto en la cola principal.`
        : " Un agente de Nivel 1 te contactará pronto.";
      setMessages((m) => [
        ...m,
        {
          role: "celu",
          text: `Ticket ${ticket.number} creado.${linked}`,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear el ticket");
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed bottom-24 right-6 z-50 w-[min(420px,calc(100vw-2rem))] animate-slide-up overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--panel)] shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl">
      <header className="flex items-center justify-between border-b border-[var(--border)] px-4 py-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--accent)]">SupportMind AI</p>
          <h2 className="text-lg font-semibold">CELU</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg px-2 py-1 text-sm text-[var(--muted)] hover:bg-white/5"
        >
          Cerrar
        </button>
      </header>

      <div className="max-h-[52vh] space-y-3 overflow-y-auto px-4 py-4">
        {!productId && products.length > 0 && (
          <div className="rounded-xl border border-[var(--border)] bg-black/20 p-3">
            <p className="mb-2 text-sm text-[var(--muted)]">Seleccioná tu producto</p>
            <select
              className="w-full rounded-lg border border-[var(--border)] bg-[#0a1628] px-3 py-2 text-sm"
              value={productId}
              onChange={(e) => {
                setProductId(e.target.value);
                setNode(null);
                setMessages([]);
                setTicketNumber(null);
              }}
            >
              <option value="">Elegir producto…</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.brand} — {p.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {node?.blocked_message && (
          <div className="rounded-xl border border-amber-300/40 bg-amber-400/10 px-3 py-2 text-sm text-amber-100">
            {node.blocked_message}
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={`${msg.role}-${idx}`}
            className={`max-w-[90%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
              msg.role === "celu"
                ? "bg-gradient-to-br from-cyan-500/15 to-teal-400/10 text-[var(--text)]"
                : "ml-auto bg-white/10"
            }`}
          >
            {msg.role === "celu" && (
              <span className="mb-1 block text-[10px] uppercase tracking-wider text-[var(--accent)]">
                CELU
              </span>
            )}
            {msg.text}
          </div>
        ))}

        {node && !done && node.options.length > 0 && (
          <div className="grid gap-2 pt-1">
            {node.options.map((opt) => (
              <button
                key={opt.id}
                type="button"
                disabled={loading || !productId}
                onClick={() => void choose(opt.id, opt.label)}
                className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-left text-sm transition hover:border-teal-300/60 hover:bg-teal-300/15 disabled:opacity-40"
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}

        {showEscalateForm && (
          <form onSubmit={submitTicket} className="space-y-2 rounded-xl border border-[var(--border)] p-3">
            <p className="text-sm text-[var(--muted)]">Completá tus datos para abrir el ticket</p>
            {(
              [
                ["first_name", "Nombre", "text"],
                ["last_name", "Apellido", "text"],
                ["email", "Correo (ej: vos@email.com)", "email"],
                ["phone", "Teléfono", "tel"],
                ["order_number", "Nº de pedido", "text"],
                ["description", "Descripción del problema (mín. 3 caracteres)", "text"],
              ] as const
            ).map(([key, label, type]) => (
              <input
                key={key}
                required
                type={type}
                minLength={key === "description" ? 3 : 1}
                placeholder={label}
                className="w-full rounded-lg border border-[var(--border)] bg-[#0a1628] px-3 py-2 text-sm"
                value={form[key]}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              />
            ))}
            <button
              type="submit"
              disabled={loading || !productId}
              className="w-full rounded-xl bg-gradient-to-r from-teal-400 to-cyan-400 px-3 py-2 text-sm font-semibold text-[#042033]"
            >
              Crear ticket con CELU
            </button>
          </form>
        )}

        {error && <p className="text-sm text-rose-300">{error}</p>}
        {loading && <p className="text-xs text-[var(--muted)]">CELU está pensando…</p>}
      </div>
    </div>
  );
}
