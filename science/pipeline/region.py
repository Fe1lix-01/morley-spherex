"""Small convex sky regions in ICRS; edges are great-circle segments."""
import os
import numpy as np
from astropy.coordinates import SkyCoord
from astropy import units as u
from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_ARCMIN = float(os.getenv("ROI_MAX_ARCMIN", "20"))


class Coordinate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    ra: float = Field(ge=0, lt=360)
    dec: float = Field(ge=-90, le=90)

    def sky(self):
        return SkyCoord(self.ra * u.deg, self.dec * u.deg, frame="icrs")


class Region(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    center: Coordinate
    corners: list[Coordinate] = Field(min_length=4, max_length=4)
    width_arcmin: float = Field(gt=0, le=MAX_ARCMIN)
    height_arcmin: float = Field(gt=0, le=MAX_ARCMIN)

    @model_validator(mode="after")
    def geometry(self):
        p = SkyCoord([c.ra for c in self.corners] * u.deg,
                     [c.dec for c in self.corners] * u.deg)
        lengths = p.separation(p[[1, 2, 3, 0]]).arcmin
        actual = [max(lengths[0], lengths[2]), max(lengths[1], lengths[3])]
        if min(lengths) < 0.001 or max(actual) > MAX_ARCMIN + 1e-7:
            raise ValueError("La región supera el límite angular o es degenerada")
        if not np.allclose(actual, [self.width_arcmin, self.height_arcmin], rtol=0.01, atol=0.001):
            raise ValueError("Las dimensiones no coinciden con las esquinas")
        v = p.cartesian.xyz.value.T
        normals = np.cross(v, np.roll(v, -1, axis=0))
        center = self.center.sky().cartesian.xyz.value
        signs = normals @ center
        if not (np.all(signs > 1e-12) or np.all(signs < -1e-12)):
            raise ValueError("El centro debe estar dentro de un cuadrilátero convexo ordenado")
        orientation = np.sign(signs[0])
        if np.any((normals @ v.T) * orientation < -1e-12):
            raise ValueError("Esquinas no convexas o cruzadas")
        if max(self.center.sky().separation(p).arcmin) > np.hypot(*actual):
            raise ValueError("Centro incompatible con las esquinas")
        return self

    def contains(self, sky):
        v = np.array([c.sky().cartesian.xyz.value for c in self.corners])
        n = np.cross(v, np.roll(v, -1, axis=0))
        sign = np.sign(n @ self.center.sky().cartesian.xyz.value)
        xyz = sky.icrs.cartesian.xyz.value
        return np.all(np.einsum("ij,j...->i...", n * sign[:, None], xyz) >= -1e-14, axis=0)

    def boundary(self, samples=65):
        points = []
        for a, b in zip(self.corners, self.corners[1:] + self.corners[:1]):
            start, end = a.sky(), b.sky()
            points.append(start.directional_offset_by(start.position_angle(end),
                          start.separation(end) * np.linspace(0, 1, samples)))
        return SkyCoord(np.concatenate([p.ra.deg for p in points]) * u.deg,
                        np.concatenate([p.dec.deg for p in points]) * u.deg)


def centered_region(ra, dec, size_arcmin=10):
    """Programmatic square in a local tangent plane, same convention as the UI."""
    r, d = np.deg2rad([ra, dec])
    c = np.array([np.cos(d)*np.cos(r), np.cos(d)*np.sin(r), np.sin(d)])
    east = np.array([-np.sin(r), np.cos(r), 0])
    north = np.array([-np.sin(d)*np.cos(r), -np.sin(d)*np.sin(r), np.cos(d)])
    half = np.tan(np.deg2rad(size_arcmin / 120))
    corners = []
    for x, y in [(-1, 1), (1, 1), (1, -1), (-1, -1)]:
        v = c + half * (x*east + y*north)
        corners.append(Coordinate(ra=float(np.rad2deg(np.arctan2(v[1], v[0])) % 360),
                                  dec=float(np.rad2deg(np.arctan2(v[2], np.hypot(v[0], v[1]))))))
    lengths = [corners[i].sky().separation(corners[(i+1)%4].sky()).arcmin for i in range(4)]
    return Region(center=Coordinate(ra=ra, dec=dec), corners=corners,
                  width_arcmin=max(lengths[0], lengths[2]), height_arcmin=max(lengths[1], lengths[3]))
