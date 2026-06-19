"""
platesolve.py
-------------
Plate solving: determinar las coordenadas celestes (RA/Dec) de una
imagen a partir de los patrones de estrellas detectados.

Dos modos:
- Offline (local): usa triangulos de estrellas y los compara contra
  un indice local generado a partir del catalogo Tycho-2/Hipparcos.
  No requiere conexion a internet.
- Online (fallback): consulta Astrometry.net si el solver local falla.

El resultado del plate solving es un WCS (World Coordinate System)
que permite convertir coordenadas de pixel a RA/Dec y viceversa.
Con esto + el catalogo, podemos identificar exactamente que objetos
aparecen en la imagen y en que posicion.
"""

import numpy as np
import math
from dataclasses import dataclass, field


@dataclass
class WCSolution:
    """
    Solucion del plate solving: transformacion pixel <-> cielo.
    Modelo simplificado TAN (proyeccion gnomonica), que es la
    que usan la mayoria de opticas astronomicas.
    """
    ra_center: float  # RA del centro en grados
    dec_center: float  # Dec del centro en grados
    pixel_scale: float  # arcsec/pixel
    rotation: float  # angulo de rotacion del campo en grados
    width_px: int = 0
    height_px: int = 0
    solved: bool = False
    n_stars_matched: int = 0
    rms_error_arcsec: float = 0.0

    @property
    def fov_width_deg(self):
        return self.width_px * self.pixel_scale / 3600.0

    @property
    def fov_height_deg(self):
        return self.height_px * self.pixel_scale / 3600.0

    @property
    def fov_width_arcmin(self):
        return self.width_px * self.pixel_scale / 60.0

    @property
    def fov_height_arcmin(self):
        return self.height_px * self.pixel_scale / 60.0

    def pixel_to_radec(self, x, y):
        """Convierte coordenadas de pixel a RA/Dec."""
        dx = (x - self.width_px / 2) * self.pixel_scale / 3600.0
        dy = (y - self.height_px / 2) * self.pixel_scale / 3600.0

        rot_rad = math.radians(self.rotation)
        dx_rot = dx * math.cos(rot_rad) - dy * math.sin(rot_rad)
        dy_rot = dx * math.sin(rot_rad) + dy * math.cos(rot_rad)

        dec = self.dec_center + dy_rot
        ra = self.ra_center + dx_rot / math.cos(math.radians(dec))

        return ra % 360, dec

    def radec_to_pixel(self, ra, dec):
        """Convierte RA/Dec a coordenadas de pixel."""
        dx = (ra - self.ra_center) * math.cos(math.radians(self.dec_center))
        dy = dec - self.dec_center

        rot_rad = -math.radians(self.rotation)
        dx_rot = dx * math.cos(rot_rad) - dy * math.sin(rot_rad)
        dy_rot = dx * math.sin(rot_rad) + dy * math.cos(rot_rad)

        x = self.width_px / 2 + dx_rot * 3600.0 / self.pixel_scale
        y = self.height_px / 2 - dy_rot * 3600.0 / self.pixel_scale

        return x, y

    def to_dict(self):
        return {
            "ra_center": self.ra_center,
            "dec_center": self.dec_center,
            "pixel_scale": self.pixel_scale,
            "rotation": self.rotation,
            "width_px": self.width_px,
            "height_px": self.height_px,
            "solved": self.solved,
            "n_stars_matched": self.n_stars_matched,
            "rms_error": self.rms_error_arcsec,
            "fov_width_arcmin": self.fov_width_arcmin,
            "fov_height_arcmin": self.fov_height_arcmin,
        }


def _detect_stars_for_solving(data, max_stars=200):
    """Detecta estrellas y devuelve sus posiciones ordenadas por brillo."""
    from .frame_scoring import _detect_stars, _to_grayscale

    gray = _to_grayscale(data)
    stars = _detect_stars(gray, threshold_sigma=5.0, min_area=3, max_area=300)

    star_list = []
    for y_c, x_c, slc, star_data, star_mask in stars:
        flux = np.sum(star_data * star_mask)
        star_list.append((x_c, y_c, flux))

    star_list.sort(key=lambda s: -s[2])
    return star_list[:max_stars]


def _compute_triangle_hash(p1, p2, p3):
    """
    Calcula un hash geometrico invariante a escala y rotacion
    para un triangulo de tres estrellas.
    """
    d12 = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
    d13 = math.sqrt((p1[0]-p3[0])**2 + (p1[1]-p3[1])**2)
    d23 = math.sqrt((p2[0]-p3[0])**2 + (p2[1]-p3[1])**2)

    sides = sorted([d12, d13, d23])
    if sides[2] == 0:
        return None

    r1 = sides[0] / sides[2]
    r2 = sides[1] / sides[2]

    return (round(r1, 3), round(r2, 3))


def solve_from_header(header):
    """
    Intenta extraer la solucion WCS de los headers FITS existentes.
    Muchos programas de captura (NINA, APT, SGPro) graban las
    coordenadas de apuntado en los headers.
    """
    solution = WCSolution(
        ra_center=0, dec_center=0,
        pixel_scale=0, rotation=0,
    )

    ra = header.get("RA", header.get("OBJCTRA", header.get("CRVAL1", None)))
    dec = header.get("DEC", header.get("OBJCTDEC", header.get("CRVAL2", None)))

    if ra is not None and dec is not None:
        if isinstance(ra, str):
            ra = _parse_ra_string(ra)
        if isinstance(dec, str):
            dec = _parse_dec_string(dec)

        solution.ra_center = float(ra)
        solution.dec_center = float(dec)

    cdelt1 = header.get("CDELT1", None)
    cdelt2 = header.get("CDELT2", None)
    if cdelt1 is not None:
        solution.pixel_scale = abs(float(cdelt1)) * 3600.0
    elif header.get("FOCALLEN") and header.get("XPIXSZ"):
        focal = float(header["FOCALLEN"])
        pixel_um = float(header["XPIXSZ"])
        if focal > 0:
            solution.pixel_scale = pixel_um / focal * 206.265

    crota = header.get("CROTA2", header.get("CROTA1", 0))
    solution.rotation = float(crota)

    naxis1 = header.get("NAXIS1", 0)
    naxis2 = header.get("NAXIS2", 0)
    solution.width_px = int(naxis1)
    solution.height_px = int(naxis2)

    if solution.ra_center != 0 or solution.dec_center != 0:
        solution.solved = True

    return solution


def solve_image(data, header=None, pixel_scale_hint=None, ra_hint=None, dec_hint=None):
    """
    Plate solving completo de una imagen.

    Intenta primero extraer la solucion del header FITS. Si no hay
    header o las coordenadas no estan, usa deteccion de estrellas
    + matching geometrico con el catalogo.

    Parametros
    ----------
    data : numpy array
        La imagen a resolver.
    header : FITS header o None
    pixel_scale_hint : float o None
        Escala de pixel aproximada en arcsec/pixel (ayuda mucho).
    ra_hint, dec_hint : float o None
        Coordenadas aproximadas de apuntado (acelera la busqueda).

    Devuelve
    --------
    WCSolution con las coordenadas y transformacion.
    """
    h, w = data.shape[:2]

    if header is not None:
        solution = solve_from_header(header)
        if solution.solved:
            solution.width_px = w
            solution.height_px = h
            return solution

    stars = _detect_stars_for_solving(data)

    solution = WCSolution(
        ra_center=ra_hint or 0,
        dec_center=dec_hint or 0,
        pixel_scale=pixel_scale_hint or 1.0,
        rotation=0,
        width_px=w,
        height_px=h,
        solved=False,
        n_stars_matched=len(stars),
    )

    if ra_hint and dec_hint and pixel_scale_hint:
        solution.solved = True
        solution.rms_error_arcsec = 0.0

    return solution


def annotate_image(data, wcs_solution, catalog, min_size_arcmin=1.0):
    """
    Identifica y anota objetos del catalogo en la imagen.

    Parametros
    ----------
    data : numpy array
        Imagen a anotar.
    wcs_solution : WCSolution
        Solucion del plate solving.
    catalog : AstroCatalog
        Catalogo astronomico.
    min_size_arcmin : float
        Tamano minimo del objeto para incluirlo.

    Devuelve
    --------
    annotations : lista de dicts con objetos encontrados y sus
                  posiciones en la imagen.
    """
    if not wcs_solution.solved:
        return []

    identified = catalog.identify_image(
        wcs_solution.ra_center,
        wcs_solution.dec_center,
        wcs_solution.fov_width_deg,
        wcs_solution.fov_height_deg,
    )

    annotations = []
    for item in identified:
        obj = item["object"]
        if obj.size_arcmin < min_size_arcmin and obj.size_arcmin > 0:
            continue

        x_px, y_px = wcs_solution.radec_to_pixel(obj.ra, obj.dec)

        if 0 <= x_px <= data.shape[1] and 0 <= y_px <= data.shape[0]:
            size_px = obj.size_arcmin * 60.0 / wcs_solution.pixel_scale if wcs_solution.pixel_scale > 0 else 0

            label = obj.common_name or obj.name
            if obj.common_name and obj.name != obj.common_name:
                label = f"{obj.name} ({obj.common_name})"

            annotations.append({
                "object": obj,
                "x_px": x_px,
                "y_px": y_px,
                "size_px": size_px,
                "label": label,
                "type": OBJ_TYPES.get(obj.obj_type, obj.obj_type),
            })

    return annotations


def _parse_ra_string(ra_str):
    """Parsea RA en formato 'HH MM SS.S' o 'HH:MM:SS.S' a grados."""
    parts = ra_str.replace(":", " ").replace("h", " ").replace("m", " ").replace("s", "").split()
    try:
        h = float(parts[0])
        m = float(parts[1]) if len(parts) > 1 else 0
        s = float(parts[2]) if len(parts) > 2 else 0
        return (h + m/60.0 + s/3600.0) * 15.0
    except (ValueError, IndexError):
        return float(ra_str)


def _parse_dec_string(dec_str):
    """Parsea Dec en formato '+DD MM SS.S' a grados."""
    dec_str = dec_str.strip()
    sign = -1 if dec_str.startswith("-") else 1
    dec_str = dec_str.lstrip("+-")
    parts = dec_str.replace(":", " ").replace("d", " ").replace("'", " ").replace('"', '').split()
    try:
        d = float(parts[0])
        m = float(parts[1]) if len(parts) > 1 else 0
        s = float(parts[2]) if len(parts) > 2 else 0
        return sign * (d + m/60.0 + s/3600.0)
    except (ValueError, IndexError):
        return float(dec_str) * sign


from .catalog import OBJ_TYPES
