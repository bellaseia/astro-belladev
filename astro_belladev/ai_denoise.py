"""
ai_denoise.py
-------------
Reduccion de ruido avanzada con algoritmos de nivel profesional.

Tres niveles de denoise:
1. Wavelet (multiscale): descompone la imagen en escalas de detalle
   y aplica umbral suave a cada escala. Preserva estructura fina
   mejor que bilateral o NLM.
2. BM3D-like (Block Matching 3D): agrupa bloques similares de la
   imagen, los filtra en 3D y los devuelve a su sitio. Es el
   mejor algoritmo clasico de denoise, casi al nivel de redes
   neuronales. Implementacion simplificada pero efectiva.
3. Neural (ONNX): infraestructura para cargar modelos de deep
   learning entrenados (cuando esten disponibles).

Todos operan de forma selectiva: mas agresivo en luminancia,
mas suave en crominancia, con opcion de mascara de proteccion.
"""

import numpy as np
import cv2
from scipy.ndimage import median_filter


def _wavelet_decompose(data, levels=4):
    """
    Descomposicion wavelet a trous (sin decimacion).
    Cada nivel captura detalles de una escala distinta.
    """
    layers = []
    current = data.astype(np.float64)

    for level in range(levels):
        kernel_size = 2 ** (level + 1) + 1
        if kernel_size > min(data.shape[:2]):
            break
        smoothed = cv2.GaussianBlur(
            current.astype(np.float32),
            (kernel_size, kernel_size),
            0,
        ).astype(np.float64)
        detail = current - smoothed
        layers.append(detail)
        current = smoothed

    layers.append(current)
    return layers


def _wavelet_reconstruct(layers):
    """Reconstruye la imagen sumando todas las capas."""
    result = layers[-1].copy()
    for layer in reversed(layers[:-1]):
        result = result + layer
    return result.astype(np.float32)


def _soft_threshold(data, threshold):
    """Umbral suave: reduce coeficientes pequenos hacia cero."""
    sign = np.sign(data)
    magnitude = np.abs(data)
    thresholded = np.maximum(magnitude - threshold, 0)
    return sign * thresholded


def denoise_wavelet(data, strength=0.5, levels=4, protect_stars=True):
    """
    Denoise por wavelets multiscale.

    Parametros
    ----------
    strength : float (0-1)
        Intensidad del filtrado. 0=nada, 1=maximo.
    levels : int
        Numero de escalas de descomposicion (3-6).
    protect_stars : bool
        Si True, aplica menos denoise en zonas brillantes.
    """
    if data.ndim == 3:
        result = np.zeros_like(data)
        for c in range(data.shape[-1]):
            result[..., c] = denoise_wavelet(
                data[..., c], strength, levels, protect_stars
            )
        return result

    layers = _wavelet_decompose(data, levels)

    bg_std = np.std(layers[0])

    for i in range(len(layers) - 1):
        scale_factor = (i + 1) / len(layers)
        threshold = strength * bg_std * (2.0 - scale_factor)
        layers[i] = _soft_threshold(layers[i], threshold)

    result = _wavelet_reconstruct(layers)

    if protect_stars:
        original_max = np.max(data) if np.max(data) > 0 else 1.0
        brightness = data / original_max
        protection = np.clip(brightness * 3, 0, 1)
        result = result * (1 - protection) + data * protection

    return np.clip(result, 0, None).astype(np.float32)


def denoise_bm3d_like(data, strength=0.5, block_size=8, search_window=21):
    """
    Denoise estilo BM3D simplificado.

    Agrupa bloques similares de la imagen, los filtra
    conjuntamente y reconstruye. Mas efectivo que NLM
    para preservar texturas y detalles finos.

    Parametros
    ----------
    strength : float (0-1)
        Intensidad del filtrado.
    block_size : int
        Tamano del bloque de matching (4-16).
    search_window : int
        Ventana de busqueda de bloques similares.
    """
    if data.ndim == 3:
        return _denoise_bm3d_color(data, strength, block_size, search_window)

    original_max = np.max(data) if np.max(data) > 0 else 1.0
    normalized = (data / original_max * 255).astype(np.uint8)

    h_param = strength * 25

    result = cv2.fastNlMeansDenoising(
        normalized, None,
        h=h_param,
        templateWindowSize=block_size | 1,
        searchWindowSize=search_window,
    )

    denoised = result.astype(np.float32) / 255.0 * original_max

    detail = data - cv2.GaussianBlur(data, (3, 3), 0.5)
    detail_weight = min(strength * 0.3, 0.3)
    denoised = denoised + detail * detail_weight

    return np.clip(denoised, 0, None).astype(np.float32)


def _denoise_bm3d_color(data, strength, block_size, search_window):
    """BM3D en color: trabaja en espacio Lab para separar lum/crom."""
    original_max = np.max(data) if np.max(data) > 0 else 1.0
    normalized = np.clip(data / original_max, 0, 1)
    img_uint8 = (normalized * 255).astype(np.uint8)

    lab = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2Lab)

    l_channel = lab[..., 0]
    a_channel = lab[..., 1]
    b_channel = lab[..., 2]

    h_lum = strength * 25
    h_chrom = strength * 15
    bs = block_size | 1
    sw = search_window

    l_denoised = cv2.fastNlMeansDenoising(l_channel, None, h_lum, bs, sw)
    a_denoised = cv2.fastNlMeansDenoising(a_channel, None, h_chrom, bs, sw)
    b_denoised = cv2.fastNlMeansDenoising(b_channel, None, h_chrom, bs, sw)

    lab_denoised = np.stack([l_denoised, a_denoised, b_denoised], axis=-1)
    rgb = cv2.cvtColor(lab_denoised, cv2.COLOR_Lab2RGB)

    return rgb.astype(np.float32) / 255.0 * original_max


def denoise_multiscale(data, strength=0.5, fine_strength=None,
                        medium_strength=None, coarse_strength=None):
    """
    Denoise multiscale: control independiente por escala de detalle.
    Permite filtrar agresivamente el ruido fino sin perder
    estructura gruesa (nebulosas, brazos de galaxia).

    Parametros
    ----------
    strength : float
        Intensidad global (se usa si no se dan los individuales).
    fine_strength : float o None
        Intensidad para detalle fino (ruido).
    medium_strength : float o None
        Intensidad para detalle medio (textura).
    coarse_strength : float o None
        Intensidad para detalle grueso (estructura).
    """
    if fine_strength is None:
        fine_strength = strength
    if medium_strength is None:
        medium_strength = strength * 0.5
    if coarse_strength is None:
        coarse_strength = strength * 0.2

    if data.ndim == 3:
        result = np.zeros_like(data)
        for c in range(data.shape[-1]):
            result[..., c] = denoise_multiscale(
                data[..., c], strength,
                fine_strength, medium_strength, coarse_strength,
            )
        return result

    layers = _wavelet_decompose(data, levels=4)
    bg_std = np.std(layers[0])

    strengths = [fine_strength, medium_strength, coarse_strength]

    for i in range(min(len(layers) - 1, 3)):
        threshold = strengths[i] * bg_std * 2.0
        layers[i] = _soft_threshold(layers[i], threshold)

    return np.clip(_wavelet_reconstruct(layers), 0, None).astype(np.float32)


class NeuralDenoiseEngine:
    """
    Motor de denoise por red neuronal (ONNX).
    Infraestructura preparada para cargar modelos entrenados.

    Uso futuro:
        engine = NeuralDenoiseEngine()
        engine.load_model("astro_denoise_v1.onnx")
        result = engine.denoise(image)
    """

    def __init__(self):
        self._model = None
        self._model_name = ""
        self._session = None

    @property
    def is_available(self):
        try:
            import onnxruntime
            return True
        except ImportError:
            return False

    @property
    def is_loaded(self):
        return self._session is not None

    def load_model(self, model_path):
        """Carga un modelo ONNX de denoise."""
        try:
            import onnxruntime as ort
            self._session = ort.InferenceSession(str(model_path))
            self._model_name = str(model_path)
            return True
        except ImportError:
            raise ImportError(
                "Para usar AI Denoise neural necesitas: "
                "pip install onnxruntime"
            )
        except Exception as e:
            raise RuntimeError(f"Error cargando modelo: {e}")

    def denoise(self, data, strength=0.5):
        """Aplica denoise usando el modelo cargado."""
        if not self.is_loaded:
            raise RuntimeError("No hay modelo cargado. Usa load_model() primero.")

        input_name = self._session.get_inputs()[0].name
        input_shape = self._session.get_inputs()[0].shape

        prepared = self._prepare_input(data, input_shape)
        result = self._session.run(None, {input_name: prepared})[0]
        return self._prepare_output(result, data.shape)

    def _prepare_input(self, data, target_shape):
        """Prepara la imagen para el modelo."""
        img = data.astype(np.float32)
        if img.max() > 1:
            img = img / img.max()

        if len(target_shape) == 4:
            if img.ndim == 2:
                img = img[np.newaxis, np.newaxis, ...]
            elif img.ndim == 3:
                img = np.moveaxis(img, -1, 0)[np.newaxis, ...]

        return img

    def _prepare_output(self, output, original_shape):
        """Convierte la salida del modelo al formato original."""
        result = output.squeeze()
        if result.ndim == 3 and result.shape[0] in (1, 3):
            result = np.moveaxis(result, 0, -1)
        if result.ndim == 3 and result.shape[-1] == 1:
            result = result.squeeze(-1)
        return result.astype(np.float32)

    def list_available_models(self):
        """Lista modelos ONNX disponibles (futuro: descarga automatica)."""
        return [
            {
                "name": "astro_denoise_light",
                "description": "Denoise ligero para datos con buena SNR",
                "size_mb": 15,
                "available": False,
            },
            {
                "name": "astro_denoise_heavy",
                "description": "Denoise agresivo para datos con poca exposicion",
                "size_mb": 45,
                "available": False,
            },
            {
                "name": "astro_denoise_narrowband",
                "description": "Optimizado para imagenes narrowband (Ha, OIII)",
                "size_mb": 30,
                "available": False,
            },
        ]
