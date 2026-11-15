"use client";

import { useEffect, useRef, useState, type FormEvent, type PointerEvent as RPointerEvent } from "react";
import { Box, ButtonBase, Chip, InputBase, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import { GREETING, SUGGESTED, type ChatMode } from "@/data/chatKnowledge";
import { LABEL, reply } from "./chatEngine";
import Robot from "./Robot";

const FAB_RIGHT = 8;
const FAB_BOTTOM = 14;
const PANEL_BOTTOM = 72;
const THINK_MS = 550;
const TALK_MS = 1600;

const MIN_W = 280;
const MIN_H = 320;
const EDGE = 8;
const STORE_KEY = "eter-chat-rect";

type Rect = { x: number; y: number; w: number; h: number };
type Corner = "nw" | "ne" | "sw" | "se";

const clamp = (v: number, lo: number, hi: number) => Math.min(Math.max(v, lo), Math.max(lo, hi));

/** Mantiene el panel dentro de la ventana y con un tamano usable. */
function fit(r: Rect): Rect {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const w = clamp(r.w, MIN_W, vw - EDGE * 2);
  const h = clamp(r.h, MIN_H, vh - EDGE * 2);
  return { w, h, x: clamp(r.x, EDGE, vw - w - EDGE), y: clamp(r.y, EDGE, vh - h - EDGE) };
}

const INK = "#1d2433";
const MUTED = "#5b6b8c";
const LINE = "#e1e6f0";
const ACCENT = "#3b5aa8";

type Msg = { id: number; from: "bot" | "user"; text: string; chips?: string[] };

const MODES: { value: ChatMode; label: string }[] = [
  { value: "explorar", label: "Explorar" },
  { value: "cientifico", label: "Cient\u00edfico" },
];

/** Convierte las direcciones web del texto en enlaces que abren en otra pestana. */
function linkify(text: string, onDark: boolean) {
  return text.split(/(https?:\/\/[^\s]+)/g).map((part, i) =>
    /^https?:\/\//.test(part) ? (
      <a
        key={i}
        href={part}
        target="_blank"
        rel="noopener noreferrer"
        style={{ color: onDark ? "#fff" : ACCENT, textDecoration: "underline" }}
      >
        {part}
      </a>
    ) : (
      part
    ),
  );
}

let nextId = 1;
const greet = (mode: ChatMode): Msg => ({ id: nextId++, from: "bot", text: GREETING[mode], chips: SUGGESTED[mode] });

export default function ChatBot() {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<ChatMode>("explorar");
  const [msgs, setMsgs] = useState<Msg[]>(() => [greet("explorar")]);
  const [text, setText] = useState("");
  const [thinking, setThinking] = useState(false);
  const [talking, setTalking] = useState(false);
  const [side, setSide] = useState<"left" | "right">("left");
  const [hop, setHop] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [msgs, open, thinking]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) setRect(fit(JSON.parse(raw) as Rect));
    } catch {
      /* sin almacenamiento: se usa la posicion de siempre */
    }
    const onResize = () => setRect((r) => (r ? fit(r) : r));
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    const t = timers.current;
    return () => t.forEach(clearTimeout);
  }, []);

  function later(fn: () => void, ms: number) {
    timers.current.push(setTimeout(fn, ms));
  }

  function changeMode(next: ChatMode | null) {
    if (!next || next === mode) return;
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setThinking(false);
    setTalking(false);
    setMode(next);
    setMsgs([greet(next)]);
    setSide("left");
    setHop((h) => h + 1);
  }

  function ask(q: string) {
    const question = q.trim();
    if (!question || thinking) return;
    const r = reply(question, mode);
    setMsgs((m) => [...m, { id: nextId++, from: "user", text: question }]);
    setText("");
    setThinking(true);
    later(() => {
      setMsgs((m) => [...m, { id: nextId++, from: "bot", text: r.text, chips: r.chips }]);
      setThinking(false);
      setSide((s) => (s === "left" ? "right" : "left"));
      setHop((h) => h + 1);
      setTalking(true);
      later(() => setTalking(false), TALK_MS);
    }, THINK_MS);
  }

  /** Arrastra o redimensiona el panel. corner = null significa mover. */
  function startGesture(e: RPointerEvent, corner: Corner | null) {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    const el = panelRef.current;
    if (!el) return;
    e.preventDefault();
    const b = el.getBoundingClientRect();
    const start: Rect = { x: b.left, y: b.top, w: b.width, h: b.height };
    const px = e.clientX;
    const py = e.clientY;
    let last: Rect = start;
    const prevSelect = document.body.style.userSelect;
    document.body.style.userSelect = "none";

    const move = (ev: PointerEvent) => {
      const dx = ev.clientX - px;
      const dy = ev.clientY - py;
      let next: Rect;
      if (!corner) {
        next = fit({ ...start, x: start.x + dx, y: start.y + dy });
      } else {
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const west = corner.includes("w");
        const north = corner.includes("n");
        const w = clamp(west ? start.w - dx : start.w + dx, MIN_W, vw - EDGE * 2);
        const h = clamp(north ? start.h - dy : start.h + dy, MIN_H, vh - EDGE * 2);
        next = fit({ w, h, x: west ? start.x + start.w - w : start.x, y: north ? start.y + start.h - h : start.y });
      }
      last = next;
      setRect(next);
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
      document.body.style.userSelect = prevSelect;
      try {
        localStorage.setItem(STORE_KEY, JSON.stringify(last));
      } catch {
        /* nada */
      }
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    setRect(start);
  }

  function resetPlace() {
    setRect(null);
    try {
      localStorage.removeItem(STORE_KEY);
    } catch {
      /* nada */
    }
  }

  const CORNERS: { c: Corner; sx: Record<string, string | number> }[] = [
    { c: "nw", sx: { top: 0, left: 0, cursor: "nwse-resize" } },
    { c: "ne", sx: { top: 0, right: 0, cursor: "nesw-resize" } },
    { c: "sw", sx: { bottom: 0, left: 0, cursor: "nesw-resize" } },
    { c: "se", sx: { bottom: 0, right: 0, cursor: "nwse-resize" } },
  ];

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    ask(text);
  }

  const ROBOT = 60;

  return (
    <>
      <style>{`@keyframes eter-hop { 0% { transform: translateY(0); } 35% { transform: translateY(-14px); } 65% { transform: translateY(0); } 80% { transform: translateY(-4px); } 100% { transform: translateY(0); } }
@media (prefers-reduced-motion: reduce) { .eter-hop { animation: none !important; } }`}</style>

      {open && (
        <Box
          ref={panelRef}
          role="dialog"
          aria-label="Asistente de ayuda"
          style={rect ? { left: rect.x, top: rect.y, width: rect.w, height: rect.h, right: "auto", bottom: "auto" } : undefined}
          sx={{
            position: "fixed",
            right: FAB_RIGHT,
            bottom: PANEL_BOTTOM,
            width: "min(92vw, 390px)",
            height: "min(74vh, 560px)",
            display: "flex",
            flexDirection: "column",
            zIndex: 1300,
            borderRadius: 4,
            overflow: "hidden",
            color: INK,
            background: "rgba(255,255,255,0.74)",
            backdropFilter: "blur(18px) saturate(1.3)",
            WebkitBackdropFilter: "blur(18px) saturate(1.3)",
            border: "1px solid rgba(255,255,255,0.55)",
            boxShadow: "0 16px 48px rgba(10,20,50,0.35)",
          }}
        >
          {CORNERS.map(({ c, sx }) => (
            <Box
              key={c}
              onPointerDown={(e) => startGesture(e, c)}
              aria-hidden
              sx={{ position: "absolute", width: 18, height: 18, zIndex: 3, touchAction: "none", ...sx }}
            />
          ))}
          {/* Encabezado: el robot cambia de lado cuando responde */}
          <Box
            onPointerDown={(e) => startGesture(e, null)}
            onDoubleClick={resetPlace}
            title="Arrastra para mover. Doble clic para volver a su lugar."
            sx={{
              position: "relative",
              height: 76,
              background: "rgba(246,248,253,0.55)",
              borderBottom: "1px solid rgba(255,255,255,0.6)",
              flexShrink: 0,
              cursor: "grab",
              touchAction: "none",
              "&:active": { cursor: "grabbing" },
            }}
          >
            <Box
              sx={{
                position: "absolute",
                top: 8,
                left: side === "left" ? 14 : `calc(100% - ${ROBOT + 14}px)`,
                transition: "left .6s cubic-bezier(.3,1.2,.4,1)",
              }}
            >
              <Box key={hop} className="eter-hop" sx={{ animation: hop ? "eter-hop .7s ease-out" : "none" }}>
                <Robot size={ROBOT} glasses={mode === "cientifico"} active={thinking || talking} />
              </Box>
            </Box>
            <Box
              sx={{
                position: "absolute",
                top: 0,
                bottom: 0,
                [side === "left" ? "left" : "right"]: ROBOT + 28,
                [side === "left" ? "right" : "left"]: 14,
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                textAlign: side === "left" ? "left" : "right",
              }}
            >
              <Typography sx={{ fontWeight: 700, lineHeight: 1.2 }}>{"Asistente \u00c9TER"}</Typography>
              <Typography variant="caption" sx={{ color: MUTED }}>
                {thinking ? "Pensando..." : mode === "cientifico" ? "Modo cient\u00edfico" : "Te explico el visor"}
              </Typography>
            </Box>
          </Box>

          <Box sx={{ p: 1.25, flexShrink: 0 }}>
            <ToggleButtonGroup
              exclusive
              fullWidth
              size="small"
              value={mode}
              onChange={(_, v) => changeMode(v)}
              aria-label="Modo del asistente"
              sx={{
                "& .MuiToggleButton-root": { color: MUTED, border: `1px solid ${LINE}`, textTransform: "none", fontWeight: 600 },
                "& .Mui-selected": { color: ACCENT, background: "#e8eefc !important" },
              }}
            >
              {MODES.map((m) => (
                <ToggleButton key={m.value} value={m.value}>
                  {m.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>

          <Box role="log" aria-live="polite" sx={{ flex: 1, overflowY: "auto", px: 1.5, pb: 1.5, display: "flex", flexDirection: "column", gap: 1 }}>
            {msgs.map((m) => (
              <Box key={m.id} sx={{ alignSelf: m.from === "user" ? "flex-end" : "flex-start", maxWidth: "90%" }}>
                <Box
                  sx={{
                    px: 1.5,
                    py: 1,
                    borderRadius: 2.5,
                    color: m.from === "user" ? "#fff" : INK,
                    background: m.from === "user" ? "rgba(59,90,168,0.92)" : "rgba(241,244,251,0.78)",
                  }}
                >
                  <Typography variant="body2" sx={{ whiteSpace: "pre-line", overflowWrap: "anywhere" }}>
                    {linkify(m.text, m.from === "user")}
                  </Typography>
                </Box>
                {m.chips && (
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mt: 0.75 }}>
                    {m.chips.map((id) => (
                      <Chip
                        key={id}
                        size="small"
                        clickable
                        variant="outlined"
                        label={LABEL[id] ?? id}
                        onClick={() => ask(LABEL[id] ?? id)}
                        sx={{ color: ACCENT, borderColor: "#c9d4ee", height: "auto", "& .MuiChip-label": { whiteSpace: "normal", py: 0.5 } }}
                      />
                    ))}
                  </Box>
                )}
              </Box>
            ))}
            {thinking && (
              <Box sx={{ alignSelf: "flex-start", px: 1.5, py: 1, borderRadius: 2.5, background: "rgba(241,244,251,0.78)", color: MUTED }}>
                <Typography variant="body2">...</Typography>
              </Box>
            )}
            <div ref={endRef} />
          </Box>

          <Box component="form" onSubmit={onSubmit} sx={{ display: "flex", gap: 1, p: 1.25, borderTop: "1px solid rgba(255,255,255,0.6)", background: "rgba(255,255,255,0.35)", flexShrink: 0 }}>
            <InputBase
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Escribe tu pregunta..."
              inputProps={{ "aria-label": "Tu pregunta" }}
              sx={{ flex: 1, color: INK, px: 1.5, py: 0.5, borderRadius: 2, background: "rgba(241,244,251,0.85)" }}
            />
            <ButtonBase
              type="submit"
              disabled={thinking}
              sx={{ px: 2, borderRadius: 2, color: "#fff", fontWeight: 600, background: ACCENT, "&.Mui-disabled": { opacity: 0.6 } }}
            >
              Enviar
            </ButtonBase>
          </Box>
        </Box>
      )}

      <ButtonBase
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        sx={{
          position: "fixed",
          right: FAB_RIGHT,
          bottom: FAB_BOTTOM,
          zIndex: 1300,
          pl: 0.75,
          pr: 2,
          py: 0.5,
          gap: 0.75,
          borderRadius: 999,
          color: INK,
          fontWeight: 600,
          background: "#fff",
          border: `1px solid ${LINE}`,
          boxShadow: "0 6px 20px rgba(10,20,50,0.35)",
        }}
      >
        <Robot size={40} glasses={mode === "cientifico"} />
        {open ? "Cerrar" : "Ayuda"}
      </ButtonBase>
    </>
  );
}
