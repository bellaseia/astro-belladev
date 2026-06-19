"""
planner.py
----------
Planificador de sesiones de astrofotografia.

Dado tu ubicacion, fecha y equipo, calcula:
- Que objetos del catalogo son visibles esta noche.
- A que hora culminan (maxima altura sobre el horizonte).
- Cuantas horas utiles tienes para cada target.
- Recomendacion de targets ordenados por prioridad.

Tambien incluye perfiles de equipo y adaptacion a contaminacion luminica.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class EquipmentProfile:
    """Perfil del equipo del usuario."""
    name: str = "Mi Equipo"
    telescope_focal_mm: float = 800.0
    telescope_aperture_mm: float = 200.0
    camera_pixel_um: float = 3.76
    camera_width_px: int = 6248
    camera_height_px: int = 4176
    filter_type: str = "broadband"  # broadband, Ha, OIII, SII, LRGB
    mount_type: str = "EQ"  # EQ, AltAz
    bortle_class: int = 5  # 1-9 escala Bortle

    @property
    def focal_ratio(self):
        if self.telescope_aperture_mm > 0:
            return self.telescope_focal_mm / self.telescope_aperture_mm
        return 0

    @property
    def pixel_scale_arcsec(self):
        """Escala de pixel en arcsec/pixel."""
        if self.telescope_focal_mm > 0:
            return self.camera_pixel_um / self.telescope_focal_mm * 206.265
        return 0

    @property
    def fov_width_arcmin(self):
        return self.camera_width_px * self.pixel_scale_arcsec / 60.0

    @property
    def fov_height_arcmin(self):
        return self.camera_height_px * self.pixel_scale_arcsec / 60.0

    @property
    def fov_width_deg(self):
        return self.fov_width_arcmin / 60.0

    @property
    def fov_height_deg(self):
        return self.fov_height_arcmin / 60.0

    @property
    def resolution_rating(self):
        """Evaluacion del muestreo: ideal es 2-3 arcsec/px para seeing tipico."""
        ps = self.pixel_scale_arcsec
        if ps < 0.5:
            return "sobremuestreado (considerar binning 2x2)"
        elif ps < 1.0:
            return "alto muestreo (bueno para seeing excelente)"
        elif ps < 2.0:
            return "muestreo optimo"
        elif ps < 4.0:
            return "muestreo aceptable"
        else:
            return "submuestreado (considerar barlow o focal mas larga)"

    def suggested_exposure(self):
        """Sugiere tiempo de exposicion segun Bortle y apertura."""
        base_seconds = {
            1: 300, 2: 300, 3: 240, 4: 180,
            5: 120, 6: 90, 7: 60, 8: 30, 9: 15,
        }
        base = base_seconds.get(self.bortle_class, 120)

        if self.focal_ratio > 0:
            ratio_factor = (self.focal_ratio / 5.0) ** 2
            base = int(base * ratio_factor)

        return min(max(base, 10), 600)

    def to_dict(self):
        return {
            "name": self.name,
            "telescope_focal_mm": self.telescope_focal_mm,
            "telescope_aperture_mm": self.telescope_aperture_mm,
            "camera_pixel_um": self.camera_pixel_um,
            "camera_width_px": self.camera_width_px,
            "camera_height_px": self.camera_height_px,
            "filter_type": self.filter_type,
            "mount_type": self.mount_type,
            "bortle_class": self.bortle_class,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class ObserverLocation:
    """Ubicacion del observador."""
    latitude: float = 38.0  # grados (positivo = norte)
    longitude: float = -1.0  # grados (positivo = este)
    altitude_m: float = 200
    timezone_offset: int = 1  # horas respecto a UTC
    name: str = "Mi ubicacion"


@dataclass
class VisibilityWindow:
    """Ventana de visibilidad de un objeto."""
    object_id: str
    object_name: str
    max_altitude_deg: float
    transit_time_hours: float  # hora local de transito
    rise_time_hours: float
    set_time_hours: float
    hours_above_30deg: float
    is_circumpolar: bool = False
    score: float = 0.0
    common_name: str = ""


def _altitude_at_hour_angle(dec_deg, lat_deg, ha_deg):
    """Calcula altitud de un objeto dado su angulo horario."""
    dec_r = math.radians(dec_deg)
    lat_r = math.radians(lat_deg)
    ha_r = math.radians(ha_deg)

    sin_alt = (math.sin(dec_r) * math.sin(lat_r) +
               math.cos(dec_r) * math.cos(lat_r) * math.cos(ha_r))
    sin_alt = max(-1, min(1, sin_alt))
    return math.degrees(math.asin(sin_alt))


def _max_altitude(dec_deg, lat_deg):
    """Altitud maxima (en transito por el meridiano)."""
    return _altitude_at_hour_angle(dec_deg, lat_deg, 0)


def _hours_above_altitude(dec_deg, lat_deg, min_alt_deg=30):
    """Horas por encima de una altitud minima."""
    cos_ha = ((math.sin(math.radians(min_alt_deg)) -
               math.sin(math.radians(dec_deg)) * math.sin(math.radians(lat_deg))) /
              (math.cos(math.radians(dec_deg)) * math.cos(math.radians(lat_deg))))

    if cos_ha <= -1:
        return 24.0
    if cos_ha >= 1:
        return 0.0

    ha = math.degrees(math.acos(cos_ha))
    return ha / 15.0 * 2


def calculate_visibility(catalog, location, date=None, min_altitude=30,
                          min_hours=1.0, max_magnitude=12.0):
    """
    Calcula la visibilidad de todos los objetos del catalogo
    para una ubicacion y fecha dada.

    Parametros
    ----------
    catalog : AstroCatalog
    location : ObserverLocation
    date : datetime o None (usa hoy)
    min_altitude : float
        Altitud minima para considerar un objeto "visible" (grados).
    min_hours : float
        Horas minimas por encima de min_altitude.
    max_magnitude : float
        Magnitud maxima (objetos mas debiles se excluyen).

    Devuelve
    --------
    Lista de VisibilityWindow ordenada por score (mejor primero).
    """
    if date is None:
        date = datetime.now()

    results = []

    for obj in catalog.all_objects():
        if obj.magnitude > max_magnitude and obj.magnitude < 90:
            continue

        max_alt = _max_altitude(obj.dec, location.latitude)
        if max_alt < min_altitude:
            continue

        hours_visible = _hours_above_altitude(
            obj.dec, location.latitude, min_altitude
        )

        if hours_visible < min_hours:
            continue

        is_circumpolar = _altitude_at_hour_angle(
            obj.dec, location.latitude, 180
        ) > 0

        score = 0.0
        score += min(max_alt / 90.0, 1.0) * 40
        score += min(hours_visible / 8.0, 1.0) * 30
        if obj.magnitude < 90:
            score += max(0, (12 - obj.magnitude) / 12.0) * 15
        score += min(obj.size_arcmin / 30.0, 1.0) * 15

        window = VisibilityWindow(
            object_id=obj.id,
            object_name=obj.name,
            max_altitude_deg=max_alt,
            transit_time_hours=0,
            rise_time_hours=0,
            set_time_hours=0,
            hours_above_30deg=hours_visible,
            is_circumpolar=is_circumpolar,
            score=score,
            common_name=obj.common_name,
        )
        results.append(window)

    results.sort(key=lambda w: -w.score)
    return results


def suggest_targets(catalog, location, equipment=None, date=None, top_n=10):
    """
    Recomienda los mejores targets para esta noche.

    Tiene en cuenta la ubicacion, equipo (FOV, apertura) y
    condiciones (Bortle).
    """
    windows = calculate_visibility(catalog, location, date)

    if equipment is not None:
        fov_max = max(equipment.fov_width_arcmin, equipment.fov_height_arcmin)

        for w in windows:
            obj = catalog.get(w.object_id)
            if obj is None:
                continue

            if obj.size_arcmin > 0 and fov_max > 0:
                fill_ratio = obj.size_arcmin / fov_max
                if 0.3 < fill_ratio < 0.8:
                    w.score *= 1.2
                elif fill_ratio > 2.0:
                    w.score *= 0.7

    windows.sort(key=lambda w: -w.score)
    return windows[:top_n]


def get_bortle_processing_hints(bortle_class):
    """
    Devuelve ajustes de procesamiento recomendados segun la escala
    Bortle del lugar de captura.
    """
    hints = {
        1: {
            "description": "Cielo excelente (sin contaminacion)",
            "abe_grid": 6, "abe_degree": 2,
            "denoise_lum": 0.2, "denoise_chrom": 0.1,
            "stretch_midtone": 0.20,
            "suggested_exposure_mult": 1.0,
        },
        2: {
            "description": "Cielo muy oscuro",
            "abe_grid": 6, "abe_degree": 2,
            "denoise_lum": 0.3, "denoise_chrom": 0.15,
            "stretch_midtone": 0.22,
            "suggested_exposure_mult": 1.0,
        },
        3: {
            "description": "Cielo rural oscuro",
            "abe_grid": 8, "abe_degree": 3,
            "denoise_lum": 0.4, "denoise_chrom": 0.2,
            "stretch_midtone": 0.23,
            "suggested_exposure_mult": 0.9,
        },
        4: {
            "description": "Cielo rural/suburbano",
            "abe_grid": 8, "abe_degree": 3,
            "denoise_lum": 0.5, "denoise_chrom": 0.25,
            "stretch_midtone": 0.25,
            "suggested_exposure_mult": 0.8,
        },
        5: {
            "description": "Cielo suburbano",
            "abe_grid": 10, "abe_degree": 3,
            "denoise_lum": 0.6, "denoise_chrom": 0.3,
            "stretch_midtone": 0.27,
            "suggested_exposure_mult": 0.7,
        },
        6: {
            "description": "Cielo suburbano brillante",
            "abe_grid": 12, "abe_degree": 4,
            "denoise_lum": 0.7, "denoise_chrom": 0.35,
            "stretch_midtone": 0.28,
            "suggested_exposure_mult": 0.5,
        },
        7: {
            "description": "Transicion suburbano/urbano",
            "abe_grid": 14, "abe_degree": 4,
            "denoise_lum": 0.8, "denoise_chrom": 0.4,
            "stretch_midtone": 0.30,
            "suggested_exposure_mult": 0.4,
        },
        8: {
            "description": "Cielo urbano",
            "abe_grid": 16, "abe_degree": 5,
            "denoise_lum": 0.9, "denoise_chrom": 0.5,
            "stretch_midtone": 0.32,
            "suggested_exposure_mult": 0.3,
        },
        9: {
            "description": "Centro de ciudad",
            "abe_grid": 18, "abe_degree": 5,
            "denoise_lum": 1.0, "denoise_chrom": 0.6,
            "stretch_midtone": 0.35,
            "suggested_exposure_mult": 0.2,
        },
    }
    return hints.get(bortle_class, hints[5])


def print_session_plan(targets, equipment=None, location=None):
    """Imprime el plan de sesion de forma legible."""
    print("\n  PLAN DE SESION")
    print("  " + "=" * 55)

    if location:
        print(f"  Ubicacion: {location.name} "
              f"({location.latitude:.1f}N, {location.longitude:.1f}E)")
    if equipment:
        print(f"  Equipo: {equipment.name}")
        print(f"    Focal: {equipment.telescope_focal_mm}mm "
              f"f/{equipment.focal_ratio:.1f}")
        print(f"    Pixel scale: {equipment.pixel_scale_arcsec:.2f}\"/px")
        print(f"    FOV: {equipment.fov_width_arcmin:.0f}' x "
              f"{equipment.fov_height_arcmin:.0f}'")
        print(f"    Muestreo: {equipment.resolution_rating}")
        print(f"    Bortle: {equipment.bortle_class}")
        print(f"    Exposicion sugerida: {equipment.suggested_exposure()}s")

    print(f"\n  {'#':>3} {'Objeto':<12} {'Nombre':<25} "
          f"{'Alt max':>7} {'Horas':>5} {'Score':>5}")
    print("  " + "-" * 65)

    for i, t in enumerate(targets):
        name = t.common_name or t.object_name
        if len(name) > 24:
            name = name[:22] + ".."
        circ = " *" if t.is_circumpolar else ""
        print(f"  {i+1:>3} {t.object_id:<12} {name:<25} "
              f"{t.max_altitude_deg:>5.1f}d {t.hours_above_30deg:>5.1f}h "
              f"{t.score:>5.0f}{circ}")

    print(f"\n  * = circumpolar (visible toda la noche)")
