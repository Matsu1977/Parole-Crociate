import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2, ArrowRight, Users, PenLine } from "lucide-react";
import { createRoom, joinRoom } from "@/lib/api";

const HERO =
  "https://images.unsplash.com/photo-1501843508755-af0829d48618?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200";

export default function Landing() {
  const nav = useNavigate();
  const [mode, setMode] = useState("crea");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);

  const go = async () => {
    if (!name.trim()) {
      toast.error("Inserisci il tuo nome");
      return;
    }
    setLoading(true);
    try {
      if (mode === "crea") {
        const data = await createRoom(name.trim());
        sessionStorage.setItem(`cw_name_${data.state.code}`, name.trim());
        nav(`/stanza/${data.state.code}`);
      } else {
        const c = code.trim().toUpperCase();
        if (c.length < 3) {
          toast.error("Inserisci un codice valido");
          setLoading(false);
          return;
        }
        const data = await joinRoom(c, name.trim());
        sessionStorage.setItem(`cw_name_${c}`, name.trim());
        nav(`/stanza/${c}`);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Qualcosa e' andato storto");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full grid lg:grid-cols-2 relative overflow-hidden">
      <div className="paper-texture absolute inset-0 z-10" />
      {/* Left / hero */}
      <div className="relative hidden lg:block">
        <img src={HERO} alt="" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-[#2c2a29]/45" />
        <div className="relative z-20 h-full flex flex-col justify-between p-12 xl:p-16 text-[#f9f6f0]">
          <div className="font-mono text-xs tracking-[0.35em] uppercase opacity-80">
            Cruciverba Insieme
          </div>
          <div className="fade-up">
            <h1 className="font-serif text-5xl xl:text-6xl leading-[1.05] font-medium">
              Un cruciverba,
              <br />
              due continenti.
            </h1>
            <p className="mt-6 max-w-md text-[#f9f6f0]/85 leading-relaxed">
              Gioca in tempo reale sulla stessa griglia. Ogni lettera che scrivi appare
              subito all'altro capo del mondo. Definizioni ricercate, per una sfida che
              stimola la mente.
            </p>
            <div className="mt-8 flex items-center gap-6 font-mono text-xs tracking-widest uppercase opacity-80">
              <span>Italia</span>
              <span className="h-px w-16 bg-[#f9f6f0]/50" />
              <span>Giappone</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right / form */}
      <div className="relative z-20 flex items-center justify-center p-8 sm:p-12">
        <div className="w-full max-w-md fade-up">
          <div className="lg:hidden mb-8">
            <div className="font-mono text-xs tracking-[0.35em] uppercase text-[#8a8481]">
              Cruciverba Insieme
            </div>
            <h1 className="font-serif text-4xl mt-2 text-[#2c2a29]">Un cruciverba, due continenti</h1>
          </div>

          <div className="flex gap-2 mb-8 p-1 rounded-full bg-[#eae4d9] w-fit">
            {[
              { k: "crea", label: "Crea stanza", icon: PenLine },
              { k: "unisci", label: "Unisciti", icon: Users },
            ].map((t) => (
              <button
                key={t.k}
                data-testid={`tab-${t.k}`}
                onClick={() => setMode(t.k)}
                className={`flex items-center gap-2 px-5 py-2 rounded-full text-sm transition-colors ${
                  mode === t.k ? "bg-[#2c2a29] text-[#f9f6f0]" : "text-[#5c5856] hover:text-[#2c2a29]"
                }`}
              >
                <t.icon size={15} />
                {t.label}
              </button>
            ))}
          </div>

          <h2 className="font-serif text-3xl text-[#2c2a29] mb-1">
            {mode === "crea" ? "Apri un nuovo tavolo" : "Raggiungi il tavolo"}
          </h2>
          <p className="text-sm text-[#8a8481] mb-8">
            {mode === "crea"
              ? "Genereremo un cruciverba impegnativo e ti daremo un codice da condividere."
              : "Inserisci il codice che ti ha condiviso l'altra persona."}
          </p>

          <div className="space-y-6">
            <div>
              <label className="block font-mono text-[0.7rem] tracking-widest uppercase text-[#8a8481] mb-2">
                Il tuo nome
              </label>
              <input
                data-testid="name-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && go()}
                placeholder="es. Mamma"
                className="w-full bg-transparent border-b-2 border-[#d6cec2] focus:border-[#c05c48] outline-none py-2 text-lg text-[#2c2a29] transition-colors"
              />
            </div>

            {mode === "unisci" && (
              <div>
                <label className="block font-mono text-[0.7rem] tracking-widest uppercase text-[#8a8481] mb-2">
                  Codice stanza
                </label>
                <input
                  data-testid="code-input"
                  value={code}
                  onChange={(e) => setCode(e.target.value.toUpperCase())}
                  onKeyDown={(e) => e.key === "Enter" && go()}
                  placeholder="es. ABCD"
                  maxLength={4}
                  className="w-full bg-transparent border-b-2 border-[#d6cec2] focus:border-[#c05c48] outline-none py-2 text-2xl font-mono tracking-[0.4em] uppercase text-[#2c2a29] transition-colors"
                />
              </div>
            )}

            <button
              data-testid="submit-button"
              onClick={go}
              disabled={loading}
              className="group w-full flex items-center justify-center gap-2 rounded-full bg-[#2c2a29] hover:bg-[#5c5856] disabled:opacity-60 text-[#f9f6f0] py-4 text-sm tracking-wide transition-colors"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  {mode === "crea" ? "Preparo il cruciverba…" : "Entro…"}
                </>
              ) : (
                <>
                  {mode === "crea" ? "Crea e gioca" : "Entra nella stanza"}
                  <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
