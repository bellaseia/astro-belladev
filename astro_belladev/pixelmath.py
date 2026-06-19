"""
pixelmath.py
------------
PixelMath: calculadora de imagenes con expresiones matematicas.

Permite combinar imagenes, canales y mascaras con formulas libres,
como la funcion homologa de PixInsight que es la razon por la que
muchos astrofotografos pagan 230 euros por ese programa.

Ejemplos de expresiones:
  "Ha * 0.7 + OIII * 0.3"
  "(R + G + B) / 3"
  "max(Ha, OIII) * mask"
  "img1 - median(img1)"
  "clip(img * 2.0, 0, 1)"
  "where(mask > 0.5, starless, original)"
  "log(img + 1) / log(max(img) + 1)"

Las imagenes se referencian por nombre (registradas previamente)
y las operaciones son pixel a pixel sobre arrays numpy.

Funciones disponibles:
  Aritmeticas: +, -, *, /, **, %
  Comparacion: >, <, >=, <=, ==, !=
  Funciones: min, max, clip, abs, sqrt, log, log10, exp,
             sin, cos, mean, median, std, where, normalize
"""

import numpy as np
import re


SAFE_FUNCTIONS = {
    "min": np.minimum,
    "max": np.maximum,
    "clip": np.clip,
    "abs": np.abs,
    "sqrt": np.sqrt,
    "log": np.log,
    "log10": np.log10,
    "exp": np.exp,
    "sin": np.sin,
    "cos": np.cos,
    "power": np.power,
    "where": np.where,
    "mean": lambda x: np.full_like(x, np.mean(x)) if isinstance(x, np.ndarray) else np.mean(x),
    "median": lambda x: np.full_like(x, np.median(x)) if isinstance(x, np.ndarray) else np.median(x),
    "std": lambda x: np.full_like(x, np.std(x)) if isinstance(x, np.ndarray) else np.std(x),
    "normalize": lambda x: (x - np.min(x)) / (np.max(x) - np.min(x)) if np.max(x) > np.min(x) else x * 0,
    "invert": lambda x: 1.0 - x,
    "percentile": np.percentile,
}

SAFE_CONSTANTS = {
    "pi": np.pi,
    "e": np.e,
}


class PixelMathEngine:
    """
    Motor de PixelMath: evalua expresiones matematicas sobre imagenes.

    Uso:
        engine = PixelMathEngine()
        engine.set_image("Ha", ha_data)
        engine.set_image("OIII", oiii_data)
        engine.set_image("mask", mask_data)
        result = engine.evaluate("Ha * 0.7 + OIII * 0.3 * mask")
    """

    def __init__(self):
        self._images = {}
        self._history = []

    def set_image(self, name, data):
        """Registra una imagen con un nombre para usar en expresiones."""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            raise ValueError(
                f"Nombre invalido: '{name}'. Usa solo letras, numeros y _"
            )
        if name in SAFE_FUNCTIONS or name in SAFE_CONSTANTS:
            raise ValueError(
                f"'{name}' es una funcion/constante reservada"
            )
        self._images[name] = data.astype(np.float32)

    def remove_image(self, name):
        self._images.pop(name, None)

    def list_images(self):
        """Lista todas las imagenes registradas con su info."""
        result = {}
        for name, data in self._images.items():
            result[name] = {
                "shape": data.shape,
                "dtype": str(data.dtype),
                "min": float(np.min(data)),
                "max": float(np.max(data)),
                "mean": float(np.mean(data)),
            }
        return result

    def evaluate(self, expression):
        """
        Evalua una expresion PixelMath y devuelve el resultado.

        La expresion puede usar:
        - Nombres de imagenes registradas
        - Operadores aritmeticos (+, -, *, /, **, %)
        - Funciones (min, max, clip, sqrt, log, where, etc.)
        - Constantes (pi, e)
        - Numeros literales
        """
        expression = expression.strip()
        if not expression:
            raise ValueError("Expresion vacia")

        self._validate_expression(expression)

        namespace = {}
        namespace.update(SAFE_FUNCTIONS)
        namespace.update(SAFE_CONSTANTS)
        namespace.update(self._images)

        namespace["__builtins__"] = {}

        try:
            result = eval(expression, namespace)
        except NameError as e:
            name = str(e).split("'")[1] if "'" in str(e) else str(e)
            available = list(self._images.keys())
            raise ValueError(
                f"Variable '{name}' no encontrada. "
                f"Imagenes disponibles: {available}"
            ) from None
        except Exception as e:
            raise ValueError(f"Error evaluando expresion: {e}") from None

        if isinstance(result, (int, float)):
            ref_shape = next(iter(self._images.values())).shape if self._images else (1,)
            result = np.full(ref_shape, result, dtype=np.float32)

        if isinstance(result, np.ndarray):
            result = result.astype(np.float32)

        self._history.append({
            "expression": expression,
            "output_shape": result.shape if isinstance(result, np.ndarray) else None,
        })

        return result

    def _validate_expression(self, expression):
        """Validacion de seguridad: solo permite operaciones seguras."""
        forbidden = [
            "import", "exec", "eval", "compile", "__",
            "open", "file", "os.", "sys.", "subprocess",
            "getattr", "setattr", "delattr", "globals", "locals",
        ]
        expr_lower = expression.lower()
        for word in forbidden:
            if word in expr_lower:
                raise ValueError(
                    f"Expresion no permitida: contiene '{word}'"
                )

    def evaluate_to_rgb(self, r_expr, g_expr, b_expr):
        """
        Evalua tres expresiones (una por canal) y combina en RGB.

        Ejemplo:
            result = engine.evaluate_to_rgb(
                "Ha * 0.8",
                "OIII * 0.6",
                "OIII * 0.4 + SII * 0.2"
            )
        """
        r = self.evaluate(r_expr)
        g = self.evaluate(g_expr)
        b = self.evaluate(b_expr)

        if r.ndim == 3:
            r = r.mean(axis=-1)
        if g.ndim == 3:
            g = g.mean(axis=-1)
        if b.ndim == 3:
            b = b.mean(axis=-1)

        return np.stack([r, g, b], axis=-1)

    def get_history(self):
        return list(self._history)

    def clear_history(self):
        self._history = []


# Expresiones predefinidas utiles
PRESET_EXPRESSIONS = {
    "Luminancia": "(R + G + B) / 3",
    "Ha + OIII bicolor": "evaluate_to_rgb('Ha', 'OIII * 0.5 + Ha * 0.5', 'OIII')",
    "Starless blend": "where(mask > 0.5, starless, original)",
    "Normalizar": "normalize(img)",
    "Invertir": "invert(img)",
    "Aumentar contraste": "clip((img - median(img)) * 2 + 0.5, 0, 1)",
    "Reducir estrellas": "where(star_mask > 0.3, img * 0.5, img)",
    "Mezcla 50/50": "img1 * 0.5 + img2 * 0.5",
    "Sustraccion continuo": "clip(narrowband - broadband * factor, 0, 1)",
    "HDR simple": "where(luminance > 0.8, short_exp, long_exp)",
}
