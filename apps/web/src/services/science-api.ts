import type {
  BarnardPreview,
  CnnDemoResponse,
} from "@/contracts/science";

// Matches the existing eter-api.ts convention.
// NEXT_PUBLIC_API_URL should include /api/v1, e.g. http://127.0.0.1:8002/api/v1.
const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000/api/v1"
).replace(/\/+$/, "");

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`Science API ${response.status}: ${path}`);
  }

  return (await response.json()) as T;
}

export const scienceApi = {
  getBarnardPreview(): Promise<BarnardPreview> {
    return getJson<BarnardPreview>("/ml/barnard/preview");
  },

  getCnnDemo(): Promise<CnnDemoResponse> {
    return getJson<CnnDemoResponse>("/ml/demo");
  },

  /** IMAGE endpoint is a binary PNG, not a JSON API. */
  getBarnardImageUrl(preview: BarnardPreview): string {
    // Backend returns /api/v1/ml/barnard/preview/image (root-relative).
    // Resolve it against the backend origin, never against the Next.js origin.
    return new URL(preview.image_url, `${API_BASE_URL}/`).toString();
  },
};
