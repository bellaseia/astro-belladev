"""
metadata.py
-----------
Lector de metadatos de sesion: extrae informacion de cada frame
(exposicion, ganancia, temperatura, timestamp) y genera una linea
temporal de la sesion de captura.

Permite visualizar:
- FWHM a lo largo de la noche (evolucion del seeing)
- Temperatura del sensor vs tiempo
- Drift del tracking (elongacion)
- Exposicion y ganancia de cada frame
- Nube de puntos calidad vs hora

Fuentes de metadatos:
- Headers FITS (EXPOSURE, GAIN, CCD-TEMP, DATE-OBS, etc.)
- EXIF de archivos RAW (via rawpy)
"""

import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class FrameMetadata:
    """Metadatos extraidos de un frame individual."""
    index: int = 0
    filename: str = ""
    timestamp: str = ""
    exposure_seconds: float = 0.0
    gain: float = 0.0
    iso: int = 0
    sensor_temp_c: float = 0.0
    filter_name: str = ""
    object_name: str = ""
    ra: float = 0.0
    dec: float = 0.0
    focal_length_mm: float = 0.0
    pixel_size_um: float = 0.0
    binning: int = 1
    fwhm: float = 0.0
    elongation: float = 1.0
    background_level: float = 0.0
    background_noise: float = 0.0
    star_count: int = 0

    def to_dict(self):
        return {
            "index": self.index,
            "filename": self.filename,
            "timestamp": self.timestamp,
            "exposure": self.exposure_seconds,
            "gain": self.gain,
            "iso": self.iso,
            "temp": self.sensor_temp_c,
            "filter": self.filter_name,
            "object": self.object_name,
            "fwhm": self.fwhm,
            "elongation": self.elongation,
            "bg_level": self.background_level,
            "bg_noise": self.background_noise,
            "stars": self.star_count,
        }


def extract_fits_metadata(path, header=None):
    """Extrae metadatos de un header FITS."""
    meta = FrameMetadata()
    meta.filename = Path(path).name

    if header is None:
        from .io_fits import load_fits
        _, header = load_fits(str(path))

    meta.exposure_seconds = float(header.get("EXPOSURE",
                                  header.get("EXPTIME", 0)))
    meta.gain = float(header.get("GAIN", header.get("EGAIN", 0)))
    meta.iso = int(header.get("ISOSPEED", header.get("ISO", 0)))
    meta.sensor_temp_c = float(header.get("CCD-TEMP",
                                header.get("SENSOR-T", 0)))
    meta.filter_name = str(header.get("FILTER", ""))
    meta.object_name = str(header.get("OBJECT", ""))
    meta.focal_length_mm = float(header.get("FOCALLEN", 0))
    meta.pixel_size_um = float(header.get("XPIXSZ", 0))
    meta.binning = int(header.get("XBINNING", 1))

    date_obs = header.get("DATE-OBS", "")
    if date_obs:
        meta.timestamp = str(date_obs)

    ra = header.get("RA", header.get("OBJCTRA", None))
    dec = header.get("DEC", header.get("OBJCTDEC", None))
    if ra is not None:
        meta.ra = float(ra) if not isinstance(ra, str) else 0
    if dec is not None:
        meta.dec = float(dec) if not isinstance(dec, str) else 0

    return meta


def extract_raw_metadata(path):
    """Extrae metadatos basicos de un archivo RAW."""
    meta = FrameMetadata()
    meta.filename = Path(path).name

    try:
        import rawpy
        raw = rawpy.imread(str(path))
        meta.filename = Path(path).name
        raw.close()
    except Exception:
        pass

    return meta


def analyze_session_metadata(metadata_list):
    """
    Analiza los metadatos de toda la sesion y genera estadisticas
    y la linea temporal.

    Devuelve
    --------
    dict con resumen, alertas y datos para graficos.
    """
    if not metadata_list:
        return {"empty": True}

    n = len(metadata_list)

    exposures = [m.exposure_seconds for m in metadata_list if m.exposure_seconds > 0]
    temps = [m.sensor_temp_c for m in metadata_list if m.sensor_temp_c != 0]
    fwhms = [m.fwhm for m in metadata_list if 0 < m.fwhm < 90]
    elongs = [m.elongation for m in metadata_list if 1.0 <= m.elongation < 90]
    star_counts = [m.star_count for m in metadata_list if m.star_count > 0]

    summary = {
        "total_frames": n,
        "total_exposure_minutes": sum(exposures) / 60.0 if exposures else 0,
        "object": metadata_list[0].object_name,
        "filter": metadata_list[0].filter_name,
    }

    if exposures:
        summary["exposure_per_frame"] = exposures[0]
        summary["exposure_consistent"] = all(
            abs(e - exposures[0]) < 0.1 for e in exposures
        )

    if temps:
        summary["temp_min"] = min(temps)
        summary["temp_max"] = max(temps)
        summary["temp_range"] = max(temps) - min(temps)

    if fwhms:
        summary["fwhm_median"] = float(np.median(fwhms))
        summary["fwhm_best"] = min(fwhms)
        summary["fwhm_worst"] = max(fwhms)

    if elongs:
        summary["elongation_median"] = float(np.median(elongs))
        summary["elongation_worst"] = max(elongs)

    if star_counts:
        summary["stars_median"] = int(np.median(star_counts))

    # Alertas
    alerts = []

    if temps and (max(temps) - min(temps)) > 5:
        alerts.append({
            "severity": "warning",
            "message": f"Temperatura del sensor vario {max(temps)-min(temps):.1f}C "
                       f"durante la sesion ({min(temps):.1f} a {max(temps):.1f}C)",
        })

    if fwhms:
        fwhm_trend = fwhms[-min(5, len(fwhms)):]
        fwhm_start = fwhms[:min(5, len(fwhms))]
        if np.mean(fwhm_trend) > np.mean(fwhm_start) * 1.5:
            alerts.append({
                "severity": "warning",
                "message": "El seeing empeoro significativamente al final de la sesion",
            })

    if elongs and max(elongs) > 2.0:
        bad_frames = sum(1 for e in elongs if e > 1.5)
        alerts.append({
            "severity": "warning",
            "message": f"{bad_frames} frames con elongacion > 1.5 "
                       f"(tracking problems)",
        })

    summary["alerts"] = alerts

    # Datos para graficos (linea temporal)
    timeline = {
        "frame_index": list(range(n)),
        "fwhm": fwhms if fwhms else [],
        "elongation": elongs if elongs else [],
        "temperature": temps if temps else [],
        "star_count": star_counts if star_counts else [],
    }
    summary["timeline"] = timeline

    return summary


def enrich_with_quality(metadata_list, frames):
    """
    Enriquece los metadatos con metricas de calidad medidas
    directamente de los frames (FWHM, elongacion, ruido).
    """
    from .frame_scoring import score_frame

    for i, (meta, frame) in enumerate(zip(metadata_list, frames)):
        score = score_frame(frame, index=i)
        meta.fwhm = score.fwhm
        meta.elongation = score.elongation
        meta.background_noise = score.background_noise
        meta.star_count = score.star_count

    return metadata_list


def print_session_summary(summary):
    """Imprime resumen de la sesion."""
    print("\n  RESUMEN DE SESION")
    print("  " + "=" * 50)

    if summary.get("empty"):
        print("  (sin datos)")
        return

    print(f"  Frames: {summary['total_frames']}")
    print(f"  Exposicion total: {summary.get('total_exposure_minutes', 0):.1f} min")

    if summary.get("object"):
        print(f"  Objeto: {summary['object']}")
    if summary.get("filter"):
        print(f"  Filtro: {summary['filter']}")

    if "fwhm_median" in summary:
        print(f"  FWHM: mediana {summary['fwhm_median']:.2f}px "
              f"(mejor {summary['fwhm_best']:.2f}, peor {summary['fwhm_worst']:.2f})")

    if "elongation_median" in summary:
        print(f"  Elongacion: mediana {summary['elongation_median']:.2f} "
              f"(peor {summary['elongation_worst']:.2f})")

    if "temp_min" in summary:
        print(f"  Temperatura: {summary['temp_min']:.1f} a "
              f"{summary['temp_max']:.1f}C "
              f"(rango {summary['temp_range']:.1f}C)")

    alerts = summary.get("alerts", [])
    if alerts:
        print(f"\n  ALERTAS:")
        for a in alerts:
            print(f"    [{a['severity']}] {a['message']}")
