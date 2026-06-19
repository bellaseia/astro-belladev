"""
mosaic.py
---------
Creacion de mosaicos: unir multiples paneles en una imagen grande.

Los mosaicos permiten fotografiar objetos mas grandes que el campo
de vision de la camara, capturando paneles con solapamiento y
uniendolos despues.

Tambien incluye HDR multiscale: combinar exposiciones cortas y
largas para capturar todo el rango dinamico (ej: nucleo brillante
de galaxia + brazos debiles).
"""

import numpy as np
import cv2


def detect_overlap(panel1, panel2, min_overlap_percent=10):
    """
    Detecta la region de solapamiento entre dos paneles
    usando deteccion de features (ORB) y matching.

    Devuelve
    --------
    transform : matriz 3x3 de homografia o None si no hay match.
    n_matches : numero de puntos coincidentes.
    """
    gray1 = panel1.mean(axis=-1) if panel1.ndim == 3 else panel1
    gray2 = panel2.mean(axis=-1) if panel2.ndim == 3 else panel2

    max_val1 = np.max(gray1) if np.max(gray1) > 0 else 1.0
    max_val2 = np.max(gray2) if np.max(gray2) > 0 else 1.0
    img1 = (gray1 / max_val1 * 255).astype(np.uint8)
    img2 = (gray2 / max_val2 * 255).astype(np.uint8)

    orb = cv2.ORB_create(nfeatures=2000)
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)

    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        return None, 0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)

    if len(matches) < 10:
        return None, len(matches)

    pts1 = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    pts2 = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(pts2, pts1, cv2.RANSAC, 5.0)
    n_inliers = int(np.sum(mask)) if mask is not None else 0

    if n_inliers < 8:
        return None, n_inliers

    return H, n_inliers


def stitch_two_panels(panel1, panel2, homography=None):
    """
    Une dos paneles en uno usando la homografia calculada.
    Si no se da homografia, la calcula automaticamente.
    """
    if homography is None:
        homography, n_matches = detect_overlap(panel1, panel2)
        if homography is None:
            raise ValueError(
                "No se pudo detectar solapamiento entre los paneles. "
                "Asegurate de que tienen region comun."
            )

    h1, w1 = panel1.shape[:2]
    h2, w2 = panel2.shape[:2]

    corners2 = np.float32([
        [0, 0], [w2, 0], [w2, h2], [0, h2]
    ]).reshape(-1, 1, 2)
    corners2_transformed = cv2.perspectiveTransform(corners2, homography)

    all_corners = np.concatenate([
        np.float32([[0, 0], [w1, 0], [w1, h1], [0, h1]]).reshape(-1, 1, 2),
        corners2_transformed,
    ])

    x_min = int(np.floor(all_corners[:, 0, 0].min()))
    y_min = int(np.floor(all_corners[:, 0, 1].min()))
    x_max = int(np.ceil(all_corners[:, 0, 0].max()))
    y_max = int(np.ceil(all_corners[:, 0, 1].max()))

    translation = np.array([
        [1, 0, -x_min],
        [0, 1, -y_min],
        [0, 0, 1],
    ], dtype=np.float64)

    out_w = x_max - x_min
    out_h = y_max - y_min

    H_adjusted = translation @ homography

    if panel2.ndim == 3:
        warped2 = cv2.warpPerspective(
            panel2.astype(np.float32), H_adjusted, (out_w, out_h)
        )
    else:
        warped2 = cv2.warpPerspective(
            panel2.astype(np.float32), H_adjusted, (out_w, out_h)
        )

    result = np.zeros((out_h, out_w) + panel1.shape[2:], dtype=np.float32)
    result[-y_min:-y_min+h1, -x_min:-x_min+w1] = panel1.astype(np.float32)

    mask1 = np.zeros((out_h, out_w), dtype=np.float32)
    mask1[-y_min:-y_min+h1, -x_min:-x_min+w1] = 1.0

    mask2 = (warped2.mean(axis=-1) if warped2.ndim == 3 else warped2) > 0
    mask2 = mask2.astype(np.float32)

    overlap = mask1 * mask2

    if warped2.ndim == 3:
        for c in range(warped2.shape[-1]):
            overlap_region = overlap > 0
            result[..., c] = np.where(
                overlap_region,
                (result[..., c] + warped2[..., c]) / 2,
                np.where(mask2 > 0, warped2[..., c], result[..., c])
            )
    else:
        overlap_region = overlap > 0
        result = np.where(
            overlap_region,
            (result + warped2) / 2,
            np.where(mask2 > 0, warped2, result)
        )

    return result


def stitch_panels(panels, order=None):
    """
    Une multiples paneles en un mosaico.

    Parametros
    ----------
    panels : list of numpy arrays
        Los paneles a unir.
    order : list of int o None
        Orden de union. Si None, une secuencialmente.
    """
    if len(panels) < 2:
        return panels[0].copy() if panels else None

    if order is not None:
        panels = [panels[i] for i in order]

    result = panels[0]
    for i in range(1, len(panels)):
        result = stitch_two_panels(result, panels[i])

    return result


def hdr_combine(short_exposure, long_exposure, blend_width=0.1):
    """
    HDR multiscale: combina exposiciones cortas y largas.

    La exposicion corta preserva detalle en zonas brillantes
    (nucleo de galaxia, estrellas brillantes) sin saturar.
    La exposicion larga captura la senal debil (brazos de galaxia,
    nebulosa tenue).

    Parametros
    ----------
    short_exposure : numpy array
        Imagen de exposicion corta (highlights preservados).
    long_exposure : numpy array
        Imagen de exposicion larga (mas senal debil).
    blend_width : float (0-1)
        Ancho de la zona de transicion entre corta y larga.
    """
    if short_exposure.shape != long_exposure.shape:
        raise ValueError("Las exposiciones deben tener el mismo tamano")

    short = short_exposure.astype(np.float32)
    long = long_exposure.astype(np.float32)

    short_max = np.max(short) if np.max(short) > 0 else 1.0
    long_max = np.max(long) if np.max(long) > 0 else 1.0

    short_norm = short / short_max
    long_norm = long / long_max

    if short_norm.ndim == 3:
        lum_long = long_norm.mean(axis=-1)
    else:
        lum_long = long_norm

    threshold = np.percentile(lum_long, 95)
    low = threshold * (1.0 - blend_width)
    high = threshold

    if high > low:
        weight_short = np.clip((lum_long - low) / (high - low), 0, 1)
    else:
        weight_short = (lum_long > threshold).astype(np.float32)

    if short_norm.ndim == 3:
        weight_short = weight_short[..., np.newaxis]

    result = long_norm * (1 - weight_short) + short_norm * weight_short

    return np.clip(result * long_max, 0, None).astype(np.float32)
