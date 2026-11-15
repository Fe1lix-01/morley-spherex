import {
  FALLBACK,
  FALLBACK_SCI,
  KNOWLEDGE,
  SUGGESTED,
  SYNONYMS,
  type ChatMode,
  type Entry,
} from "@/data/chatKnowledge";

/**
 * Buscador de respuestas del asistente (sin modelo, sin costo).
 * Tolera faltas de ortografia (b/v, c/s/z, h muda, ll/y...), letras de mas o de menos,
 * letras cambiadas de lugar, plurales, palabras cortadas y sinonimos. Pondera mas las palabras
 * poco comunes (IDF) y siempre responde con texto de la base: nunca inventa.
 */

const STOP = new Set(["como", "funciona", "funcionan", "funcionar", "funcionamiento",
  "el", "la", "los", "las", "de", "del", "que", "es", "un", "una", "unos", "unas", "y", "e", "en", "a", "para",
  "por", "con", "se", "como", "me", "mi", "mis", "lo", "al", "su", "sus", "o", "si", "no", "hay", "son", "te", "tu",
  "puedo", "quiero", "saber", "dime", "favor", "hola", "cual", "cuales", "q", "k", "pq", "xq", "porfa", "pues",
  "muestra", "muestran", "esto", "eso", "esta", "este", "ese", "esa", "algo", "bien", "mas", "muy", "ya", "le",
  "les", "ser", "era", "fue", "hacer", "hace", "donde", "cuando", "cuanto", "cuantos", "cuantas", "quien", "quiere",
  "gustaria", "tiene", "tienen", "sirve", "sirven", "sirva", "visor",
]);

const MIN_SCORE = 4;
const MIN_SINGLE = 3.8;
const MAYBE_SCORE = 2.2;

export const MAYBE = "No estoy seguro de haberte entendido. Quiz\u00e1 te refieras a alguna de estas:";

const norm = (s: string) =>
  s
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

/** Quita plural simple (filtros -> filtro). */
const stem = (t: string) => (t.length > 4 ? t.replace(/(es|s)$/, "") : t);

/** Clave fonetica del espanol: junta variantes de escritura (b/v, c/s/z, h muda, ll/y, qu/k...). */
function phon(w: string): string {
  return w
    .replace(/ch/g, "X")
    .replace(/qu/g, "k")
    .replace(/gu(?=[ei])/g, "G")
    .replace(/ll/g, "y")
    .replace(/h/g, "")
    .replace(/c(?=[ei])/g, "s")
    .replace(/c/g, "k")
    .replace(/z/g, "s")
    .replace(/g(?=[ei])/g, "j")
    .replace(/G/g, "g")
    .replace(/v/g, "b")
    .replace(/(.)\1+/g, "$1");
}

const words = (s: string) => norm(s).split(" ").filter((t) => t.length >= 2 && !STOP.has(t));
const tok = (w: string) => phon(stem(w));
const toks = (s: string) => words(s).map(tok);

/** Distancia de edicion con transposiciones (filtors ~ filtros cuenta como 1). */
function within(a: string, b: string, max: number): boolean {
  if (max <= 0) return a === b;
  if (Math.abs(a.length - b.length) > max) return false;
  const d: number[][] = [];
  for (let i = 0; i <= a.length; i++) d[i] = [i];
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const c = a[i - 1] === b[j - 1] ? 0 : 1;
      let v = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) v = Math.min(v, d[i - 2][j - 2] + 1);
      d[i][j] = v;
    }
  }
  return d[a.length][b.length] <= max;
}

const maxDist = (len: number) => (len >= 8 ? 2 : len >= 4 ? 1 : 0);

type Indexed = Omit<Entry, "q"> & {
  label: string;
  mode: ChatMode;
  key: Set<string>;
  q: Set<string>;
  body: Set<string>;
  pool: string[];
  phrases: string[];
  raw: string[];
};

const ALL: Indexed[] = (["explorar", "cientifico"] as ChatMode[]).flatMap((mode) =>
  KNOWLEDGE[mode].map((e) => {
    const key = new Set(e.keys.flatMap(toks));
    const q = new Set(toks(e.q));
    return {
      ...e,
      label: e.q,
      mode,
      key,
      q,
      body: new Set(toks(e.a)),
      pool: [...new Set([...key, ...q])],
      phrases: e.keys.map((k) => toks(k)).filter((t) => t.length > 1).map((t) => t.join(" ")),
      raw: e.keys.map(norm).filter((k) => k.includes(" ")),
    };
  }),
);

export const LABEL: Record<string, string> = Object.fromEntries(ALL.map((e) => [e.id, e.label]));

// Documentos (entradas) en los que aparece cada palabra clave o de pregunta.
const DF = new Map<string, number>();
for (const e of ALL) for (const t of e.pool) DF.set(t, (DF.get(t) ?? 0) + 1);
const idf = (t: string) => Math.log(1 + ALL.length / (DF.get(t) ?? 1));

type QTok = { t: string; w: number };

/** Palabras de la pregunta + sus sinonimos (con un poco menos de peso). */
function expand(text: string): QTok[] {
  const out: QTok[] = [];
  const seen = new Set<string>();
  const add = (t: string, w: number) => {
    if (!seen.has(t)) {
      seen.add(t);
      out.push({ t, w });
    }
  };
  // Palabras pegadas en camelCase (uncertaintyArcsec): tambien se prueba la forma completa.
  for (const raw of text.split(/\s+/)) {
    if (/[a-z][A-Z]/.test(raw)) add(tok(norm(raw).replace(/ /g, "")), 1);
  }
  for (const w of words(text)) {
    add(tok(w), 1);
    for (const s of SYNONYMS[w] ?? SYNONYMS[stem(w)] ?? []) for (const st of toks(s)) add(st, 0.8);
  }
  return out;
}

function score(qt: QTok[], joined: string, rawJoined: string, e: Indexed, mode: ChatMode): number {
  let s = 0;
  let matched = 0;
  for (const { t, w } of qt) {
    let hit = 0;
    if (e.key.has(t)) hit = 3 * idf(t) + (e.q.has(t) ? 1.5 * idf(t) : 0);
    else if (e.q.has(t)) hit = 1.5 * idf(t);
    else if (e.body.has(t)) {
      s += 0.5 * idf(t) * w;
      continue;
    } else if (t.length >= 4) {
      for (const k of e.pool) {
        const near =
          within(t, k, maxDist(t.length)) ||
          (k.length >= 4 && t.startsWith(k)) ||
          (t.length >= 4 && k.startsWith(t) && t.length >= k.length - 4);
        if (near) {
          hit = Math.min(1.8 * idf(k), 3.5);
          break;
        }
      }
    }
    if (hit > 0) matched++;
    s += hit * w;
  }
  for (const p of e.phrases) if (joined.includes(" " + p + " ")) s += 3;
  if (s > 0) s *= 0.6 + (0.4 * matched) / Math.max(1, qt.length);
  for (const p of e.raw) if (rawJoined.includes(" " + p + " ")) s += 6;
  s /= 1 + 0.08 * e.q.size;
  return e.mode === mode ? s * 1.3 : s;
}

const HOW = /(fun[cs]ion|operan?\b|trabaj|mecanism|paso a paso|por dentro|detras|como se (hace|hacen|usa|usan|arma|forma|detecta|detectan|mueve|mueven|predice|aplica|aplican|genera|generan|carga|cargan)|como (uso|usar|empiezo)|explica)/;

export type Ranked = { e: Indexed; s: number };

export function rank(text: string, mode: ChatMode): Ranked[] {
  const qt = expand(text);
  const joined = " " + qt.filter((x) => x.w === 1).map((x) => x.t).join(" ") + " ";
  const rawJoined = " " + norm(text) + " ";
  const how = HOW.test(norm(text));
  return ALL.map((e) => {
    let s = score(qt, joined, rawJoined, e, mode);
    if (s >= 2) s *= how ? (e.how ? 1.35 : 0.85) : e.how ? 0.8 : 1;
    return { e, s };
  }).sort((x, y) => y.s - x.s);
}

export type Decision =
  | { kind: "match"; best: Indexed; alt?: Indexed }
  | { kind: "maybe"; options: Indexed[] }
  | { kind: "none" };

// Vocabulario conocido (claves, preguntas y respuestas) para detectar palabras ajenas al tema.
const VOCAB = new Set<string>();
for (const e of ALL) {
  for (const t of e.pool) VOCAB.add(t);
  for (const t of e.body) VOCAB.add(t);
}
const VOCAB_LIST = [...VOCAB];
function known(t: string): boolean {
  if (VOCAB.has(t)) return true;
  if (t.length < 4) return true;
  return VOCAB_LIST.some((v) => within(t, v, maxDist(t.length)));
}

export function decide(text: string, mode: ChatMode): Decision {
  const res = rank(text, mode);
  const best = res[0];
  const min = expand(text).length === 1 ? MIN_SINGLE : MIN_SCORE;
  const qs = expand(text).filter((x) => x.w === 1).map((x) => x.t);
  const unknown = qs.filter((t) => !known(t)).length;
  const offTopic = unknown >= 1 && qs.length >= 2 && unknown / qs.length >= 0.4 && best && best.s < 12;
  if (best && best.s >= min && !offTopic) {
    const alt = res.find((r) => r.e.id !== best.e.id && r.s >= min && r.s >= best.s * 0.75);
    return { kind: "match", best: best.e, alt: alt?.e };
  }
  if (best && best.s >= MAYBE_SCORE) {
    return { kind: "maybe", options: res.filter((r) => r.s >= MAYBE_SCORE).slice(0, 3).map((r) => r.e) };
  }
  return { kind: "none" };
}

/** Respuesta final: texto y botones de sugerencia. */
export function reply(text: string, mode: ChatMode): { text: string; chips?: string[] } {
  const d = decide(text, mode);
  if (d.kind === "match") {
    const technical = d.best.mode !== mode && mode === "explorar";
    return {
      text: (technical ? "Esto es m\u00e1s t\u00e9cnico (modo Cient\u00edfico):\n" : "") + d.best.a,
      chips: d.alt ? [d.alt.id] : undefined,
    };
  }
  if (d.kind === "maybe") return { text: MAYBE, chips: d.options.map((o) => o.id) };
  return { text: mode === "cientifico" ? FALLBACK_SCI : FALLBACK, chips: SUGGESTED[mode] };
}
