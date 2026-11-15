import {workflowApi} from "./workflow-api";
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

const pending = new Map<string, Promise<unknown>>();

function getJson<T>(path: string): Promise<T> {
  const existing = pending.get(path);
  if (existing) return existing as Promise<T>;
  const request = (async () => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(path === "/ml/demo" ? 95000 : 15000),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(`Science API ${response.status}: ${body.detail ?? path}`);
    }
    return await response.json() as T;
  })().finally(() => pending.delete(path));
  pending.set(path, request);
  return request;
}

export const scienceApi = {
  getBarnardPreview(): Promise<BarnardPreview> {
    return getJson<BarnardPreview>("/ml/barnard/preview");
  },

  getCnnDemo(): Promise<CnnDemoResponse> {
    return workflowApi.run<CnnDemoResponse>({kind:"demo"}).then(job=>job.result);
  },

  /** IMAGE endpoint is a binary PNG, not a JSON API. */
  getBarnardImageUrl(preview: BarnardPreview): string {
    // Backend returns /api/v1/ml/barnard/preview/image (root-relative).
    // Resolve it against the backend origin, never against the Next.js origin.
    return new URL(preview.image_url, `${API_BASE_URL}/`).toString();
  },
};
