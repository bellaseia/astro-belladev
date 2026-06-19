"""
transform.py
-------------
Transformaciones geométricas de imagen: crop, rotación, flip y binning.

Estas son operaciones básicas que cualquier programa de astrofotografía
necesita. Cada una se expone como acción independiente para que la GUI
pueda asignarles un botón/menú.
"""

import numpy as np
import cv2


def crop(data, x1, y1, x2, y2):
    """
    Recorta la imagen a la región definida por las coordenadas.

    Parámetros
    ----------
    x1, y1 : int
        Esquina superior izquierda.
    x2, y2 : int
        Esquina inferior derecha.
    """
    h, w = data.shape[:2]
    x1 = max(0, int(x1))
    y1 = max(0, int(y1))
    x2 = min(w, int(x2))
    y2 = min(h, int(y2))

    if x2 <= x1 or y2 <= y1:
        raise ValueError(
            f"Región de crop inválida: ({x1},{y1})-({x2},{y2})"
        )

    return data[y1:y2, x1:x2].copy()


def crop_percent(data, top=0, bottom=0, left=0, right=0):
    """
    Recorta un porcentaje de cada borde.
    Útil para eliminar bordes negros tras alinear/apilar.

    Parámetros
    ----------
    top, bottom, left, right : float (0-50)
        Porcentaje a recortar de cada lado.
    """
    h, w = data.shape[:2]
    y1 = int(h * top / 100)
    y2 = h - int(h * bottom / 100)
    x1 = int(w * left / 100)
    x2 = w - int(w * right / 100)

    return crop(data, x1, y1, x2, y2)


def rotate(data, angle):
    """
    Rota la imagen un ángulo en grados (sentido antihorario).
    Soporta ángulos arbitrarios; la imagen resultante se redimensiona
    para que no se pierda nada.

    Parámetros
    ----------
    angle : float
        Ángulo en grados. Valores comunes: 90, 180, 270.
    """
    h, w = data.shape[:2]

    if angle % 90 == 0:
        k = int(angle / 90) % 4
        if k == 0:
            return data.copy()
        return np.rot90(data, k=k)

    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)

    M[0, 2] += (new_w - w) / 2
    M[1, 2] += (new_h - h) / 2

    if data.ndim == 3:
        result = cv2.warpAffine(
            data, M, (new_w, new_h),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )
    else:
        result = cv2.warpAffine(
            data, M, (new_w, new_h),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )

    return result.astype(np.float32)


def flip_horizontal(data):
    """Voltea la imagen horizontalmente (espejo)."""
    return np.fliplr(data).copy()


def flip_vertical(data):
    """Voltea la imagen verticalmente."""
    return np.flipud(data).copy()


def binning(data, factor=2, method="average"):
    """
    Binning: agrupa píxeles NxN en uno solo.
    Reduce resolución pero mejora la relación señal/ruido.
    Equivale al binning de hardware de las cámaras astro.

    Parámetros
    ----------
    factor : int
        Factor de binning (2 = 2x2, 3 = 3x3).
    method : str
        "average" (media, preserva brillo) o
        "sum" (suma, simula binning de hardware).
    """
    h, w = data.shape[:2]
    new_h = h // factor
    new_w = w // factor

    trimmed_h = new_h * factor
    trimmed_w = new_w * factor

    if data.ndim == 3:
        trimmed = data[:trimmed_h, :trimmed_w, :]
        reshaped = trimmed.reshape(new_h, factor, new_w, factor, -1)
        if method == "sum":
            return reshaped.sum(axis=(1, 3)).astype(np.float32)
        return reshaped.mean(axis=(1, 3)).astype(np.float32)

    trimmed = data[:trimmed_h, :trimmed_w]
    reshaped = trimmed.reshape(new_h, factor, new_w, factor)
    if method == "sum":
        return reshaped.sum(axis=(1, 3)).astype(np.float32)
    return reshaped.mean(axis=(1, 3)).astype(np.float32)


def resize(data, scale=1.0, width=None, height=None):
    """
    Redimensiona la imagen por factor de escala o a un tamaño específico.

    Parámetros
    ----------
    scale : float
        Factor de escala (0.5 = mitad, 2.0 = doble). Se ignora si
        se especifica width/height.
    width, height : int o None
        Tamaño de salida. Si solo se da uno, se mantiene la proporción.
    """
    h, w = data.shape[:2]

    if width is not None or height is not None:
        if width is not None and height is not None:
            new_w, new_h = int(width), int(height)
        elif width is not None:
            new_w = int(width)
            new_h = int(h * new_w / w)
        else:
            new_h = int(height)
            new_w = int(w * new_h / h)
    else:
        new_w = int(w * scale)
        new_h = int(h * scale)

    interpolation = cv2.INTER_LANCZOS4 if new_w > w else cv2.INTER_AREA
    result = cv2.resize(data, (new_w, new_h), interpolation=interpolation)

    return result.astype(np.float32)
