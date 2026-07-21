import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { CeluWidget } from "./features/chatbot/CeluWidget";
import { api } from "./lib/api";
import "./index.css";

const queryClient = new QueryClient();

function Portal() {
  const [open, setOpen] = useState(false);
  const products = useQuery({ queryKey: ["products"], queryFn: api.products });
  const incidents = useQuery({
    queryKey: ["active-incidents"],
    queryFn: api.activeIncidents,
    refetchInterval: 15000,
  });

  useEffect(() => {
    document.title = "SupportMind AI — Soporte inteligente";
  }, []);

  const banner = incidents.data?.[0];

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0 opacity-40">
        <div className="absolute left-[12%] top-[18%] h-64 w-64 rounded-full bg-cyan-400/20 blur-3xl animate-float" />
        <div className="absolute right-[8%] top-[40%] h-72 w-72 rounded-full bg-teal-300/15 blur-3xl animate-float" />
      </div>

      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div>
          <p className="text-sm tracking-[0.25em] text-cyan-300/80">SUPPORTMIND AI</p>
          <p className="text-xs text-[var(--muted)]">Powered by CELU</p>
        </div>
        <a
          href="http://localhost:5174"
          className="rounded-full border border-white/15 px-4 py-2 text-sm text-[var(--muted)] hover:border-cyan-300/40 hover:text-white"
        >
          Portal agentes
        </a>
      </header>

      {banner && (
        <div className="relative z-10 mx-auto mb-4 max-w-6xl px-6 animate-slide-up">
          <div className="rounded-2xl border border-amber-300/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
            {banner.public_message}
          </div>
        </div>
      )}

      <main className="relative z-10 mx-auto grid max-w-6xl gap-10 px-6 pb-28 pt-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <section className="animate-slide-up">
          <h1 className="mb-4 text-5xl font-semibold leading-tight tracking-tight md:text-6xl">
            SupportMind AI
          </h1>
          <p className="mb-3 text-xl text-cyan-100/90">Soporte técnico que piensa con vos.</p>
          <p className="max-w-xl text-[var(--muted)]">
            CELU te guía con decisiones claras, resuelve lo que puede y escala a un agente humano
            solo cuando hace falta — con contexto completo y cero fricción.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="rounded-full bg-gradient-to-r from-teal-300 to-cyan-400 px-6 py-3 text-sm font-semibold text-[#042033] shadow-[0_10px_40px_rgba(45,212,191,0.35)]"
            >
              Hablar con CELU
            </button>
            <span className="rounded-full border border-white/15 px-5 py-3 text-sm text-[var(--muted)]">
              Multiple choice · sin texto libre
            </span>
          </div>
        </section>

        <section className="relative animate-float rounded-[2rem] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[0_30px_100px_rgba(0,0,0,0.35)] backdrop-blur-xl">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-300 to-cyan-400 text-lg font-bold text-[#042033]">
              C
            </div>
            <div>
              <p className="font-semibold">CELU Online</p>
              <p className="text-xs text-teal-200/80">Guided Decision Engine</p>
            </div>
          </div>
          <div className="space-y-3 text-sm text-[var(--muted)]">
            <p className="rounded-2xl bg-white/5 px-4 py-3 text-[var(--text)]">
              Hola, soy CELU. Te voy a hacer preguntas de opción múltiple para diagnosticar tu
              celular.
            </p>
            <p className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3">
              Mi celular no enciende
            </p>
            <p className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3">
              Se reinicia solo / boot loop
            </p>
          </div>
        </section>
      </main>

      <button
        type="button"
        aria-label="Abrir CELU"
        onClick={() => setOpen(true)}
        className="animate-pulse-ring fixed bottom-6 right-6 z-40 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-teal-300 to-cyan-400 text-xl font-bold text-[#042033] shadow-[0_12px_40px_rgba(45,212,191,0.45)]"
      >
        C
      </button>

      <CeluWidget
        open={open}
        onClose={() => setOpen(false)}
        products={products.data ?? []}
      />
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Portal />
    </QueryClientProvider>
  );
}
