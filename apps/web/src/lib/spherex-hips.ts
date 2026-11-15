/**
 * Aladin 3.8.2 addresses legacy HiPS cubes uniformly in frequency and ignores
 * data_cube_crval3_arr. Use the bin center to address the requested file index.
 * This is a transport coordinate, NOT the physical wavelength of the channel.
 * Physical labels must continue to come from spherexChannels.ts / product tables.
 * Bounds/depth: official spherex_allsky_cube/properties (DR1).
 */
export function spherexFrameAddress(channel: number): number {
  if (!Number.isInteger(channel) || channel < 1 || channel > 102) {
    throw new RangeError("Canal SPHEREx fuera de rango");
  }
  const minWavelength = 7.43e-7;
  const maxWavelength = 5.009e-6;
  const fraction = (channel - 1 + 0.5) / 102;
  return 1 / (1 / maxWavelength + fraction * (1 / minWavelength - 1 / maxWavelength));
}
