
declare module "aladin-lite" {
  export interface HiPSLayer {
  setCuts(min: number, max: number, format?: string): void;
  getCuts(): number[];
  setBrightness(value: number): void;
  setContrast(value: number): void;
  setGamma(value: number): void;
  setSliceNumber(slice: number): void;

  setFrequency(options: {
    value: number;
    unit: "m";
  }): void;
}

  export interface AladinInstance {
    setBaseImageLayer(source: string | HiPSLayer): void;
    getBaseImageLayer(): HiPSLayer;
    setProjection(projection: string): void;
    setFoV(fov: number): void;
    gotoRaDec(ra: number, dec: number): void;
    remove(): void;
    pix2world(x: number, y: number, frame?: string): number[] | null;
    world2pix(ra: number, dec: number): number[] | null;
    getRaDec(): number[];
  getSize?(): number[];
  }

  interface HiPSOptions {
    name?: string;
    imgFormat?: string;
    minCut?: number;
    maxCut?: number;
    stretch?: string;
    successCallback?: (layer: HiPSLayer) => void;
    errorCallback?: (error: unknown) => void;
  }

  interface AladinAPI {
    init: Promise<void>;

    HiPS(url: string, options?: HiPSOptions): HiPSLayer;

    aladin(
      selector: string,
      options: {
        survey: string;
        target?: string;
        fov?: number;
        projection?: string;
        cooFrame?: string;
        log: boolean;
      }
    ): AladinInstance;
  }

  const A: AladinAPI;
  export default A;
}
