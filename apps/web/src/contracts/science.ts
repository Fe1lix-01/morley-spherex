/** Respuesta real de GET /api/v1/ml/barnard/preview. */
export interface BarnardPreview {
  object: string;
  source: string;
  detector: string;
  mode: string;
  reference_date: string;
  science_date: string;
  wavelength_um_approx: number;
  image_url: string;
  shape: [number, number];
  valid_pixels: number;
  total_pixels: number;
  valid_fraction: number;
  center_pixel_valid: boolean;
  cnn_inference_performed: boolean;
  scientifically_validated: boolean;
  limitations: string[];
}

/** Respuesta real de GET /api/v1/ml/demo. Sólo datos sintéticos. */
export interface CnnDemoResult {
  model: string;
  score_real_like: number;
  trained_on: string;
  scientifically_validated: boolean;
  note: string;
}

export interface CnnDemoResponse {
  status: string;
  mode: string;
  scientifically_validated: boolean;
  result: CnnDemoResult;
}
