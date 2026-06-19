"""
annotate.py
-----------
Anotacion visual de imagenes astronomicas.

Dibuja sobre la imagen: circulos alrededor de objetos, etiquetas
con nombres, escala angular, brujula N/E. Para compartir resultados
en redes sociales, foros de astrofotografia o documentacion.

Con el plate solving, las anotaciones se generan automaticamente
a partir del catalogo. Sin plate solving, el usuario puede
anotar manualmente.
"""

import numpy as np
import cv2
import math


def _ensure_uint8(data):
    """Convierte a uint8 para dibujar con OpenCV."""
    if data.dtype == np.uint8:
        return data.copy()
    dmax = np.max(data) if np.max(data) > 0 else 1.0
    return np.clip(data / dmax * 255, 0, 255).astype(np.uint8)


def _ensure_rgb(data):
    """Asegura que la imagen es RGB (3 canales)."""
    if data.ndim == 2:
        return np.stack([data, data, data], axis=-1)
    return data


def annotate_circle(image, x, y, radius, color=(255, 200, 0),
                     thickness=1, label="", font_scale=0.5):
    """
    Dibuja un circulo con etiqueta en la imagen.

    Parametros
    ----------
    x, y : float
        Centro del circulo en pixeles.
    radius : float
        Radio en pixeles.
    color : tuple (R, G, B)
        Color del circulo y texto.
    label : str
        Texto a mostrar junto al circulo.
    """
    result = _ensure_rgb(image).copy()
    img_uint8 = _ensure_uint8(result)

    center = (int(x), int(y))
    r = max(int(radius), 5)

    cv2.circle(img_uint8, center, r, color, thickness)

    if label:
        text_x = int(x + r + 5)
        text_y = int(y - 5)
        cv2.putText(img_uint8, label, (text_x, text_y),
                     cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                     color, 1, cv2.LINE_AA)

    return img_uint8


def annotate_objects_from_catalog(image, annotations, color=(255, 200, 0),
                                   font_scale=0.45, min_radius=8):
    """
    Anota objetos del catalogo en la imagen.
    Usa la salida de platesolve.annotate_image().

    Parametros
    ----------
    annotations : list of dict
        Salida de platesolve.annotate_image(), cada dict tiene:
        x_px, y_px, size_px, label, type.
    """
    result = _ensure_rgb(image)
    img = _ensure_uint8(result)

    type_colors = {
        "Galaxia": (255, 180, 50),
        "Nebulosa de emision": (255, 80, 80),
        "Nebulosa de reflexion": (80, 150, 255),
        "Nebulosa planetaria": (0, 255, 200),
        "Cumulo abierto": (200, 255, 100),
        "Cumulo globular": (255, 255, 100),
        "Remanente de supernova": (255, 100, 255),
        "Region HII": (255, 60, 60),
    }

    for ann in annotations:
        c = type_colors.get(ann.get("type", ""), color)
        x = int(ann["x_px"])
        y = int(ann["y_px"])
        r = max(int(ann.get("size_px", 20) / 2), min_radius)

        cv2.circle(img, (x, y), r, c, 1)

        small_r = max(r // 4, 2)
        cv2.drawMarker(img, (x, y), c, cv2.MARKER_CROSS, small_r, 1)

        label = ann.get("label", "")
        if label:
            text_x = x + r + 5
            text_y = y - 5
            cv2.putText(img, label, (text_x, text_y),
                         cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                         c, 1, cv2.LINE_AA)

    return img


def annotate_compass(image, rotation_deg=0, x=None, y=None, size=50,
                      color=(255, 255, 255)):
    """
    Dibuja una brujula N/E en la imagen.

    Parametros
    ----------
    rotation_deg : float
        Angulo de rotacion del campo (del plate solving).
    x, y : int o None
        Posicion de la brujula. None = esquina inferior izquierda.
    size : int
        Tamano de la brujula en pixeles.
    """
    result = _ensure_rgb(image)
    img = _ensure_uint8(result)
    h, w = img.shape[:2]

    if x is None:
        x = 30 + size
    if y is None:
        y = h - 30 - size

    rot_rad = math.radians(rotation_deg)

    n_dx = int(size * math.sin(rot_rad))
    n_dy = int(-size * math.cos(rot_rad))
    e_dx = int(size * math.cos(rot_rad))
    e_dy = int(size * math.sin(rot_rad))

    cv2.arrowedLine(img, (x, y), (x + n_dx, y + n_dy), color, 2, tipLength=0.2)
    cv2.putText(img, "N", (x + n_dx - 5, y + n_dy - 8),
                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

    cv2.arrowedLine(img, (x, y), (x + e_dx, y + e_dy), color, 1, tipLength=0.2)
    cv2.putText(img, "E", (x + e_dx + 5, y + e_dy + 5),
                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

    return img


def annotate_scale_bar(image, pixel_scale_arcsec, bar_length_arcmin=5,
                        x=None, y=None, color=(255, 255, 255)):
    """
    Dibuja una barra de escala angular.

    Parametros
    ----------
    pixel_scale_arcsec : float
        Escala de pixel en arcsec/pixel.
    bar_length_arcmin : float
        Longitud de la barra en arcminutos.
    """
    result = _ensure_rgb(image)
    img = _ensure_uint8(result)
    h, w = img.shape[:2]

    if pixel_scale_arcsec <= 0:
        return img

    bar_px = int(bar_length_arcmin * 60 / pixel_scale_arcsec)

    if bar_px > w * 0.5:
        bar_length_arcmin = bar_length_arcmin / 2
        bar_px = int(bar_length_arcmin * 60 / pixel_scale_arcsec)

    if bar_px < 20:
        bar_length_arcmin = bar_length_arcmin * 2
        bar_px = int(bar_length_arcmin * 60 / pixel_scale_arcsec)

    if x is None:
        x = w - bar_px - 30
    if y is None:
        y = h - 30

    cv2.line(img, (x, y), (x + bar_px, y), color, 2)
    cv2.line(img, (x, y - 5), (x, y + 5), color, 1)
    cv2.line(img, (x + bar_px, y - 5), (x + bar_px, y + 5), color, 1)

    if bar_length_arcmin >= 60:
        label = f"{bar_length_arcmin / 60:.0f} deg"
    elif bar_length_arcmin >= 1:
        label = f"{bar_length_arcmin:.0f}'"
    else:
        label = f'{bar_length_arcmin * 60:.0f}"'

    text_x = x + bar_px // 2 - 15
    cv2.putText(img, label, (text_x, y - 10),
                 cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    return img


def annotate_text(image, text, x, y, font_scale=0.6,
                   color=(255, 255, 255), thickness=1,
                   background=True):
    """
    Escribe texto en la imagen con fondo opcional para legibilidad.
    """
    result = _ensure_rgb(image)
    img = _ensure_uint8(result)

    if background:
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX,
                                        font_scale, thickness)
        cv2.rectangle(img, (x - 2, y - th - 4), (x + tw + 2, y + 4),
                       (0, 0, 0), -1)

    cv2.putText(img, text, (x, y),
                 cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                 color, thickness, cv2.LINE_AA)

    return img


def annotate_full(image, wcs_solution=None, catalog=None,
                   equipment=None, show_compass=True,
                   show_scale=True, show_objects=True,
                   show_info=True):
    """
    Anotacion completa automatica: objetos + brujula + escala + info.

    Parametros
    ----------
    wcs_solution : WCSolution o None
        Solucion del plate solving.
    catalog : AstroCatalog o None
        Catalogo astronomico.
    equipment : EquipmentProfile o None
        Perfil del equipo.
    """
    result = _ensure_rgb(image)
    img = _ensure_uint8(result)

    if show_objects and wcs_solution and catalog and wcs_solution.solved:
        from .platesolve import annotate_image as plate_annotate
        annotations = plate_annotate(image, wcs_solution, catalog)
        img = annotate_objects_from_catalog(img, annotations)

    if show_compass and wcs_solution and wcs_solution.solved:
        img = annotate_compass(img, rotation_deg=wcs_solution.rotation)

    if show_scale and wcs_solution and wcs_solution.pixel_scale > 0:
        img = annotate_scale_bar(img, wcs_solution.pixel_scale)

    if show_info:
        info_lines = []
        if wcs_solution and wcs_solution.solved:
            info_lines.append(
                f"RA: {wcs_solution.ra_center:.3f}  "
                f"Dec: {wcs_solution.dec_center:.3f}"
            )
            info_lines.append(
                f"FOV: {wcs_solution.fov_width_arcmin:.0f}' x "
                f"{wcs_solution.fov_height_arcmin:.0f}'"
            )
        if equipment:
            info_lines.append(f"{equipment.name}")
            info_lines.append(
                f"{equipment.pixel_scale_arcsec:.2f}\"/px  "
                f"f/{equipment.focal_ratio:.1f}"
            )

        for i, line in enumerate(info_lines):
            img = annotate_text(img, line, 10, 20 + i * 20,
                                 font_scale=0.4)

    return img
