// Endpoint específico para AllWISE. No acepta URLs externas del cliente.
const UPSTREAM =
  "https://irsa.ipac.caltech.edu/data/hips/CDS/AllWISE/RGB-W4-W2-W1/";

type Context = { params: Promise<{ path: string[] }> };

function isAllowed(path: string): boolean {
  if (path === "properties" || path === "Moc.fits") return true;
  if (/^Norder[0-8]\/Allsky\.jpg$/.test(path)) return true;
  const tile = /^Norder([0-8])\/Dir(\d{1,7})\/Npix(\d{1,7})\.jpg$/.exec(path);
  if (!tile) return false;
  const [, order, directory, pixel] = tile;
  const index = Number(pixel);
  return index < 12 * 4 ** Number(order)
    && Number(directory) === Math.floor(index / 10000) * 10000;
}

function errorResponse(error: string, status: number): Response {
  return Response.json({ error }, {
    status,
    headers: { "Cache-Control": "no-store" },
  });
}

type Tile = { body: ArrayBuffer; upstream: string; expires: number };
const FALLBACK = "https://hips.china-vo.org/m/CDS_P_allWISE_color/";
const cache = new Map<string, Tile>();
const pending = new Map<string, Promise<Tile>>();
let cacheBytes = 0;
const MAX_CACHE_BYTES = 32 * 1024 * 1024;

async function load(resource: string): Promise<Tile> {
  const cached = cache.get(resource);
  if (cached && cached.expires > Date.now()) return cached;
  if (cached) { cacheBytes -= cached.body.byteLength; cache.delete(resource); }
  const existing = pending.get(resource);
  if (existing) return existing;
  const request = (async () => {
    for (const upstream of [UPSTREAM, FALLBACK]) {
      try {
        const response = await fetch(new URL(resource, upstream), {
          cache: "no-store", redirect: "error", signal: AbortSignal.timeout(6000),
        });
        if (!response.ok) continue;
        const body = await response.arrayBuffer();
        const tile = { body, upstream, expires: Date.now() + 3600000 };
        if (body.byteLength <= MAX_CACHE_BYTES) {
          while (cacheBytes + body.byteLength > MAX_CACHE_BYTES && cache.size) {
            const key = cache.keys().next().value!;
            cacheBytes -= cache.get(key)!.body.byteLength; cache.delete(key);
          }
          cache.set(resource, tile); cacheBytes += body.byteLength;
        }
        return tile;
      } catch { /* Try the documented mirror of the same AllWISE survey. */ }
    }
    throw new Error("AllWISE no disponible en IRSA ni en el espejo HiPS. Reintenta más tarde.");
  })().finally(() => pending.delete(resource));
  pending.set(resource, request);
  return request;
}

export async function GET(_request: Request, { params }: Context): Promise<Response> {
  const resource = (await params).path.join("/");
  if (!isAllowed(resource)) return errorResponse("Recurso HiPS no permitido.", 400);
  try {
    const tile = await load(resource);
    return new Response(tile.body.slice(0), { headers: {
      "Content-Type": resource === "properties" ? "text/plain; charset=utf-8"
        : resource.endsWith(".fits") ? "application/fits" : "image/jpeg",
      "Cache-Control": "public, max-age=3600",
      "X-HiPS-Survey": "AllWISE RGB-W4-W2-W1",
      "X-HiPS-Upstream": tile.upstream,
      "X-Content-Type-Options": "nosniff",
    }});
  } catch (error) {
    return errorResponse((error as Error).message, 503);
  }
}
