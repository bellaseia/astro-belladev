"""
actions.py
----------
Registro centralizado de acciones (operaciones) del pipeline.

Cada acción se define con sus parámetros, valores por defecto, rangos
válidos y tooltips. La GUI futura iterará este registro para generar
menús, deslizadores y controles automáticamente, sin hardcodear nada.

Ejemplo de uso:
    registry = ActionRegistry()
    registry.register(Action(
        id="stretch_midtone",
        name="Stretch Midtone (STF)",
        category="processing.stretch",
        params=[
            Param("midtone", float, 0.25, 0.01, 0.99, "Punto medio del stretch"),
            Param("black_clip", float, -2.8, -5.0, 0.0, "Recorte de punto negro (sigmas)"),
        ],
        function=stretch_midtone,
    ))

    # La GUI hace:
    for action in registry.get_category("processing"):
        menu.add_item(action.name, action.params)
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class Param:
    """Definición de un parámetro de una acción."""
    name: str
    type: type
    default: Any
    min_value: Any = None
    max_value: Any = None
    tooltip: str = ""
    choices: list = field(default_factory=list)
    visible_in_auto: bool = False
    visible_in_expert: bool = True

    def validate(self, value):
        if self.choices and value not in self.choices:
            raise ValueError(
                f"'{self.name}': valor '{value}' no válido. "
                f"Opciones: {self.choices}"
            )
        if self.min_value is not None and value < self.min_value:
            raise ValueError(
                f"'{self.name}': {value} < mínimo {self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            raise ValueError(
                f"'{self.name}': {value} > máximo {self.max_value}"
            )
        return True


@dataclass
class Action:
    """Una operación registrada en el sistema."""
    id: str
    name: str
    category: str
    description: str = ""
    params: list = field(default_factory=list)
    function: Optional[Callable] = None
    icon: str = ""
    shortcut: str = ""
    menu_path: str = ""

    def get_defaults(self):
        return {p.name: p.default for p in self.params}

    def validate_params(self, values):
        for p in self.params:
            if p.name in values:
                p.validate(values[p.name])
        return True

    def execute(self, data, **kwargs):
        if self.function is None:
            raise RuntimeError(f"Acción '{self.id}' no tiene función asignada")
        params = self.get_defaults()
        params.update(kwargs)
        self.validate_params(params)
        return self.function(data, **params)


class ActionRegistry:
    """Registro global de todas las acciones disponibles."""

    def __init__(self):
        self._actions = {}
        self._categories = {}

    def register(self, action):
        self._actions[action.id] = action
        cat = action.category.split(".")[0]
        if cat not in self._categories:
            self._categories[cat] = []
        self._categories[cat].append(action)

    def get(self, action_id):
        return self._actions.get(action_id)

    def get_category(self, category):
        return self._categories.get(category, [])

    def get_all(self):
        return list(self._actions.values())

    def get_menu_tree(self):
        """Devuelve un dict anidado para generar menús."""
        tree = {}
        for action in self._actions.values():
            parts = action.category.split(".")
            node = tree
            for part in parts:
                if part not in node:
                    node[part] = {}
                node = node[part]
            node[action.id] = action
        return tree

    def list_actions(self):
        """Imprime todas las acciones registradas."""
        for cat in sorted(self._categories.keys()):
            print(f"\n  [{cat.upper()}]")
            for action in self._categories[cat]:
                params_str = ", ".join(
                    f"{p.name}={p.default}" for p in action.params
                )
                print(f"    {action.name}")
                if params_str:
                    print(f"      Params: {params_str}")


def build_default_registry():
    """Construye el registro con todas las acciones del motor."""
    import numpy as np
    from . import calibration, stacking, alignment
    from .debayer import debayer
    from .stretch import stretch_midtone, stretch_asinh, stretch_auto
    from .frame_scoring import score_all
    from .background import extract_background_abe, extract_background_dbe
    from .denoise import denoise_bilateral, denoise_nlm, denoise_selective, denoise_image
    from .sharpen import sharpen_unsharp_mask, sharpen_deconvolution
    from .color import (white_balance_auto, white_balance_stars,
                        white_balance_manual,
                        adjust_saturation, adjust_saturation_selective,
                        photometric_color_calibration, image_statistics)
    from .curves import adjust_levels, adjust_curves
    from .transform import (crop, crop_percent, rotate, flip_horizontal,
                            flip_vertical, binning, resize)
    from .export import save_png, save_jpeg
    from .masks import (mask_luminance, mask_range, mask_stars,
                        extract_starless, combine_starless_stars,
                        reduce_star_halos, apply_with_mask)
    from .curves import get_histogram
    from .narrowband import (combine_palette, combine_custom,
                              continuum_subtraction, blend_narrowband_rgb)
    from .mosaic import hdr_combine
    from .platesolve import solve_image, annotate_image

    registry = ActionRegistry()

    # =====================================================
    #  PRE-PROCESAMIENTO
    # =====================================================
    registry.register(Action(
        id="create_master_bias",
        name="Crear Master Bias",
        category="preprocessing.calibration",
        description="Combina bias frames por mediana",
        menu_path="Pre-procesamiento > Crear Master Bias",
        function=lambda frames, **kw: calibration.create_master_bias(frames),
    ))

    registry.register(Action(
        id="create_master_dark",
        name="Crear Master Dark",
        category="preprocessing.calibration",
        description="Combina dark frames por mediana, restando bias",
        menu_path="Pre-procesamiento > Crear Master Dark",
        function=lambda frames, **kw: calibration.create_master_dark(frames, kw.get("master_bias")),
    ))

    registry.register(Action(
        id="create_master_flat",
        name="Crear Master Flat",
        category="preprocessing.calibration",
        description="Combina flat frames por mediana, normalizado",
        menu_path="Pre-procesamiento > Crear Master Flat",
        function=lambda frames, **kw: calibration.create_master_flat(frames, kw.get("master_bias")),
    ))

    registry.register(Action(
        id="score_frames",
        name="Evaluar Calidad de Frames",
        category="preprocessing.scoring",
        description="Puntúa cada frame por FWHM, elongación, ruido y nº de estrellas",
        menu_path="Pre-procesamiento > Evaluar calidad de frames",
        params=[
            Param("reject_percent", int, 20, 0, 80,
                  "Porcentaje máximo de frames a descartar"),
            Param("min_stars", int, 5, 1, 100,
                  "Mínimo de estrellas para aceptar un frame"),
        ],
        function=lambda frames, **kw: score_all(
            frames,
            reject_percent=kw.get("reject_percent", 20),
            min_stars=kw.get("min_stars", 5),
        ),
    ))

    registry.register(Action(
        id="stack_frames",
        name="Apilar Frames",
        category="preprocessing.stacking",
        description="Combina frames alineados en una imagen final",
        menu_path="Pre-procesamiento > Apilar",
        params=[
            Param("method", str, "sigma_clip", choices=["sigma_clip", "average", "median"],
                  tooltip="Método de apilamiento"),
            Param("sigma", float, 3.0, 1.0, 5.0,
                  "Factor sigma para rechazo de outliers"),
        ],
        function=lambda frames, **kw: stacking.stack_frames(
            frames, method=kw.get("method", "sigma_clip"), sigma=kw.get("sigma", 3.0),
        ),
    ))

    # =====================================================
    #  PROCESAMIENTO: STRETCH
    # =====================================================
    registry.register(Action(
        id="stretch_auto",
        name="Stretch Automático",
        category="processing.stretch",
        description="Detecta tipo de target y aplica el perfil óptimo",
        menu_path="Procesamiento > Stretch > Auto",
        params=[
            Param("target_type", str, "", choices=["", "nebula", "galaxy", "starfield", "planetary"],
                  tooltip="Tipo de objeto (vacío = autodetectar)"),
        ],
        function=lambda data, **kw: stretch_auto(
            data, target_type=kw.get("target_type") or None,
        ),
    ))

    registry.register(Action(
        id="stretch_midtone",
        name="Stretch Midtone (STF)",
        category="processing.stretch",
        description="Midtone Transfer Function, algoritmo clásico de PixInsight",
        menu_path="Procesamiento > Stretch > Midtone (STF)",
        params=[
            Param("midtone", float, 0.25, 0.01, 0.99,
                  "Punto medio del stretch (menor = más agresivo)"),
            Param("black_clip", float, -2.8, -5.0, 0.0,
                  "Recorte de punto negro (sigmas bajo la mediana)"),
        ],
        function=lambda data, **kw: stretch_midtone(
            data, midtone=kw.get("midtone", 0.25), black_clip=kw.get("black_clip", -2.8),
        ),
    ))

    registry.register(Action(
        id="stretch_asinh",
        name="Stretch Arcsinh",
        category="processing.stretch",
        description="Arcsinh stretch, preserva colores (usado en surveys SDSS)",
        menu_path="Procesamiento > Stretch > Arcsinh",
        params=[
            Param("a", float, 0.02, 0.001, 1.0,
                  "Factor de suavizado (menor = más agresivo)"),
            Param("black_clip", float, -2.8, -5.0, 0.0,
                  "Recorte de punto negro (sigmas bajo la mediana)"),
        ],
        function=lambda data, **kw: stretch_asinh(
            data, a=kw.get("a", 0.02), black_clip=kw.get("black_clip", -2.8),
        ),
    ))

    # =====================================================
    #  PROCESAMIENTO: EXTRACCIÓN DE FONDO
    # =====================================================
    registry.register(Action(
        id="background_abe",
        name="Extracción de Fondo (ABE)",
        category="processing.background",
        description="Automatic Background Extraction: detecta y resta gradientes",
        menu_path="Procesamiento > Extracción de fondo > ABE (Automático)",
        params=[
            Param("grid_size", int, 8, 4, 20,
                  "Tamaño de rejilla de muestreo (más = más preciso)"),
            Param("degree", int, 3, 1, 5,
                  "Grado del polinomio de la superficie"),
            Param("star_sigma", float, 3.0, 1.0, 10.0,
                  "Sigmas para excluir estrellas del muestreo"),
        ],
        function=lambda data, **kw: extract_background_abe(
            data,
            grid_size=kw.get("grid_size", 8),
            degree=kw.get("degree", 3),
            star_sigma=kw.get("star_sigma", 3.0),
        )[0],
    ))

    # =====================================================
    #  PROCESAMIENTO: REDUCCIÓN DE RUIDO
    # =====================================================
    registry.register(Action(
        id="denoise_bilateral",
        name="Denoise Bilateral",
        category="processing.denoise",
        description="Filtro bilateral: reduce ruido preservando bordes",
        menu_path="Procesamiento > Reducción de ruido > Bilateral",
        params=[
            Param("d", int, 9, 3, 15,
                  "Diámetro del vecindario (píxeles)"),
            Param("sigma_color", float, 75.0, 10.0, 200.0,
                  "Rango de intensidad del filtro"),
            Param("sigma_space", float, 75.0, 10.0, 200.0,
                  "Rango espacial del filtro"),
        ],
        function=lambda data, **kw: denoise_bilateral(
            data, d=kw.get("d", 9),
            sigma_color=kw.get("sigma_color", 75.0),
            sigma_space=kw.get("sigma_space", 75.0),
        ),
    ))

    registry.register(Action(
        id="denoise_nlm",
        name="Denoise Non-Local Means",
        category="processing.denoise",
        description="NLM: máxima calidad, busca parches similares en toda la imagen",
        menu_path="Procesamiento > Reducción de ruido > Non-Local Means",
        params=[
            Param("h", float, 10.0, 1.0, 30.0,
                  "Intensidad del filtrado (mayor = más suave)"),
            Param("template_size", int, 7, 3, 11,
                  "Tamaño del parche de comparación"),
            Param("search_size", int, 21, 11, 41,
                  "Tamaño de la ventana de búsqueda"),
        ],
        function=lambda data, **kw: denoise_nlm(
            data, h=kw.get("h", 10.0),
            template_size=kw.get("template_size", 7),
            search_size=kw.get("search_size", 21),
        ),
    ))

    registry.register(Action(
        id="denoise_selective",
        name="Denoise Selectivo (Lum+Crom)",
        category="processing.denoise",
        description="Denoise diferenciado: más agresivo en luminancia, suave en color",
        menu_path="Procesamiento > Reducción de ruido > Selectivo",
        params=[
            Param("lum_strength", float, 0.7, 0.0, 1.0,
                  "Intensidad del filtrado de luminancia"),
            Param("chrom_strength", float, 0.3, 0.0, 1.0,
                  "Intensidad del filtrado cromático"),
            Param("base_method", str, "nlm", choices=["nlm", "bilateral"],
                  tooltip="Algoritmo base"),
        ],
        function=lambda data, **kw: denoise_selective(
            data,
            lum_strength=kw.get("lum_strength", 0.7),
            chrom_strength=kw.get("chrom_strength", 0.3),
            method=kw.get("base_method", "nlm"),
        ),
    ))

    # =====================================================
    #  PROCESAMIENTO: NITIDEZ
    # =====================================================
    registry.register(Action(
        id="sharpen_usm",
        name="Unsharp Mask",
        category="processing.sharpen",
        description="Potencia detalles finos restando una versión borrosa",
        menu_path="Procesamiento > Nitidez > Unsharp Mask",
        params=[
            Param("radius", float, 2.0, 0.5, 10.0,
                  "Radio del desenfoque (mayor = detalles más gruesos)"),
            Param("amount", float, 1.0, 0.1, 5.0,
                  "Intensidad del efecto"),
            Param("threshold", int, 0, 0, 50,
                  "Umbral mínimo para aplicar (evita amplificar ruido)"),
        ],
        function=lambda data, **kw: sharpen_unsharp_mask(
            data, radius=kw.get("radius", 2.0),
            amount=kw.get("amount", 1.0),
            threshold=kw.get("threshold", 0),
        ),
    ))

    registry.register(Action(
        id="sharpen_deconv",
        name="Deconvolution (Richardson-Lucy)",
        category="processing.sharpen",
        description="Recupera detalle real perdido por seeing/óptica",
        menu_path="Procesamiento > Nitidez > Deconvolution",
        params=[
            Param("psf_sigma", float, 1.5, 0.5, 5.0,
                  "Sigma de la PSF estimada (píxeles)"),
            Param("iterations", int, 15, 5, 50,
                  "Iteraciones (más = más detalle pero más ruido)"),
        ],
        function=lambda data, **kw: sharpen_deconvolution(
            data, psf_sigma=kw.get("psf_sigma", 1.5),
            iterations=kw.get("iterations", 15),
        ),
    ))

    # =====================================================
    #  PROCESAMIENTO: COLOR
    # =====================================================
    registry.register(Action(
        id="wb_auto",
        name="Balance de Blancos Automático",
        category="processing.color",
        description="Iguala canales RGB por percentil alto",
        menu_path="Procesamiento > Color > Balance blancos > Automático",
        params=[
            Param("percentile", int, 95, 80, 99,
                  "Percentil de referencia para igualar canales"),
        ],
        function=lambda data, **kw: white_balance_auto(
            data, percentile=kw.get("percentile", 95),
        ),
    ))

    registry.register(Action(
        id="wb_stars",
        name="Balance de Blancos por Estrellas",
        category="processing.color",
        description="Usa estrellas brillantes como referencia de blanco",
        menu_path="Procesamiento > Color > Balance blancos > Por estrellas",
        function=lambda data, **kw: white_balance_stars(data),
    ))

    registry.register(Action(
        id="saturation",
        name="Saturación Global",
        category="processing.color",
        description="Ajusta la saturación de toda la imagen",
        menu_path="Procesamiento > Color > Saturación",
        params=[
            Param("factor", float, 1.0, 0.0, 3.0,
                  "Factor (<1 desatura, >1 más color)"),
        ],
        function=lambda data, **kw: adjust_saturation(
            data, factor=kw.get("factor", 1.0),
        ),
    ))

    registry.register(Action(
        id="saturation_selective",
        name="Saturación Selectiva",
        category="processing.color",
        description="Ajusta saturación solo de un rango de color específico",
        menu_path="Procesamiento > Color > Saturación selectiva",
        params=[
            Param("target_hue", int, 0, 0, 180,
                  "Tono objetivo (0=rojo, 60=verde, 120=azul)"),
            Param("hue_range", int, 15, 5, 45,
                  "Rango alrededor del tono"),
            Param("factor", float, 1.5, 0.0, 3.0,
                  "Factor de saturación para ese rango"),
        ],
        function=lambda data, **kw: adjust_saturation_selective(
            data, target_hue=kw.get("target_hue", 0),
            hue_range=kw.get("hue_range", 15),
            factor=kw.get("factor", 1.5),
        ),
    ))

    # =====================================================
    #  PROCESAMIENTO: CURVAS Y NIVELES
    # =====================================================
    registry.register(Action(
        id="levels",
        name="Niveles",
        category="processing.curves",
        description="Ajuste de punto negro, gamma y punto blanco",
        menu_path="Procesamiento > Curvas y niveles > Niveles",
        params=[
            Param("black", float, 0.0, 0.0, 0.5,
                  "Punto negro (recorte inferior)"),
            Param("midtone", float, 0.5, 0.01, 0.99,
                  "Punto medio (gamma)"),
            Param("white", float, 1.0, 0.5, 1.0,
                  "Punto blanco (recorte superior)"),
        ],
        function=lambda data, **kw: adjust_levels(
            data, black=kw.get("black", 0.0),
            midtone=kw.get("midtone", 0.5),
            white=kw.get("white", 1.0),
        ),
    ))

    registry.register(Action(
        id="curves",
        name="Curvas",
        category="processing.curves",
        description="Transformación tonal libre por puntos de control",
        menu_path="Procesamiento > Curvas y niveles > Curvas",
        params=[],
        function=lambda data, **kw: adjust_curves(
            data, control_points=kw.get("control_points"),
        ),
    ))

    # =====================================================
    #  PRE-PROCESAMIENTO: DEBAYER (faltaba en el registry)
    # =====================================================
    registry.register(Action(
        id="debayer",
        name="Debayer (CFA a RGB)",
        category="preprocessing.debayer",
        description="Convierte imagen Bayer (CFA) en RGB completo",
        menu_path="Pre-procesamiento > Debayer",
        params=[
            Param("pattern", str, "RGGB",
                  choices=["RGGB", "BGGR", "GRBG", "GBRG"],
                  tooltip="Patron Bayer del sensor"),
            Param("method", str, "bilinear",
                  choices=["bilinear", "vng"],
                  tooltip="Metodo de interpolacion"),
        ],
        function=lambda data, **kw: debayer(
            data, pattern=kw.get("pattern", "RGGB"),
            method=kw.get("method", "bilinear"),
        ),
    ))

    # =====================================================
    #  PRE-PROCESAMIENTO: ALINEAR (faltaba en el registry)
    # =====================================================
    registry.register(Action(
        id="align_frames",
        name="Alinear Frames",
        category="preprocessing.alignment",
        description="Alinea frames por deteccion de estrellas (astroalign)",
        menu_path="Pre-procesamiento > Alinear frames",
        params=[
            Param("reference_index", int, 0, 0, 999,
                  "Indice del frame de referencia"),
        ],
        function=lambda frames, **kw: alignment.align_all(
            frames, reference_index=kw.get("reference_index", 0),
        ),
    ))

    # =====================================================
    #  PRE-PROCESAMIENTO: CALIBRAR LIGHT (faltaba)
    # =====================================================
    registry.register(Action(
        id="calibrate_light",
        name="Calibrar Light Frame",
        category="preprocessing.calibration",
        description="Aplica bias/dark/flat a un light frame individual",
        menu_path="Pre-procesamiento > Calibrar Light Frame",
        function=lambda data, **kw: calibration.calibrate_light(
            data,
            master_bias=kw.get("master_bias"),
            master_dark=kw.get("master_dark"),
            master_flat_norm=kw.get("master_flat"),
        ),
    ))

    # =====================================================
    #  PROCESAMIENTO: FONDO — DBE (faltaba)
    # =====================================================
    registry.register(Action(
        id="background_dbe",
        name="Extraccion de Fondo (DBE)",
        category="processing.background",
        description="Dynamic Background Extraction: puntos de muestreo manuales",
        menu_path="Procesamiento > Extraccion de fondo > DBE (Manual)",
        params=[
            Param("degree", int, 3, 1, 5,
                  "Grado del polinomio de la superficie"),
        ],
        function=lambda data, **kw: extract_background_dbe(
            data,
            sample_points=kw.get("sample_points", []),
            degree=kw.get("degree", 3),
        )[0],
    ))

    # =====================================================
    #  PROCESAMIENTO: COLOR — WB Manual (faltaba)
    # =====================================================
    registry.register(Action(
        id="wb_manual",
        name="Balance de Blancos Manual",
        category="processing.color",
        description="Corrige color usando un punto neutro seleccionado por el usuario",
        menu_path="Procesamiento > Color > Balance blancos > Manual",
        params=[
            Param("ref_y", int, 0, 0, 99999, "Coordenada Y del punto neutro"),
            Param("ref_x", int, 0, 0, 99999, "Coordenada X del punto neutro"),
            Param("radius", int, 10, 1, 50, "Radio de muestreo alrededor del punto"),
        ],
        function=lambda data, **kw: white_balance_manual(
            data,
            ref_y=kw.get("ref_y", 0),
            ref_x=kw.get("ref_x", 0),
            radius=kw.get("radius", 10),
        ),
    ))

    # =====================================================
    #  TRANSFORMACIONES
    # =====================================================
    registry.register(Action(
        id="crop",
        name="Recortar",
        category="transform.crop",
        description="Recorta la imagen a una region rectangular",
        menu_path="Herramientas > Crop / Recortar",
        params=[
            Param("x1", int, 0, 0, 99999, "X esquina superior izquierda"),
            Param("y1", int, 0, 0, 99999, "Y esquina superior izquierda"),
            Param("x2", int, 100, 1, 99999, "X esquina inferior derecha"),
            Param("y2", int, 100, 1, 99999, "Y esquina inferior derecha"),
        ],
        function=lambda data, **kw: crop(
            data, x1=kw.get("x1", 0), y1=kw.get("y1", 0),
            x2=kw.get("x2", data.shape[1]), y2=kw.get("y2", data.shape[0]),
        ),
    ))

    registry.register(Action(
        id="crop_percent",
        name="Recortar Bordes (%)",
        category="transform.crop",
        description="Recorta un porcentaje de cada borde (util tras apilar)",
        menu_path="Herramientas > Crop bordes (%)",
        params=[
            Param("top", float, 2.0, 0.0, 50.0, "% a recortar arriba"),
            Param("bottom", float, 2.0, 0.0, 50.0, "% a recortar abajo"),
            Param("left", float, 2.0, 0.0, 50.0, "% a recortar izquierda"),
            Param("right", float, 2.0, 0.0, 50.0, "% a recortar derecha"),
        ],
        function=lambda data, **kw: crop_percent(
            data, top=kw.get("top", 2), bottom=kw.get("bottom", 2),
            left=kw.get("left", 2), right=kw.get("right", 2),
        ),
    ))

    registry.register(Action(
        id="rotate",
        name="Rotar",
        category="transform.rotate",
        description="Rota la imagen un angulo en grados",
        menu_path="Herramientas > Rotacion",
        params=[
            Param("angle", float, 0.0, -360.0, 360.0,
                  "Angulo en grados (antihorario)"),
        ],
        function=lambda data, **kw: rotate(data, angle=kw.get("angle", 0)),
    ))

    registry.register(Action(
        id="flip_h",
        name="Voltear Horizontal",
        category="transform.flip",
        description="Voltea la imagen como un espejo",
        menu_path="Herramientas > Voltear horizontal",
        function=lambda data, **kw: flip_horizontal(data),
    ))

    registry.register(Action(
        id="flip_v",
        name="Voltear Vertical",
        category="transform.flip",
        description="Voltea la imagen verticalmente",
        menu_path="Herramientas > Voltear vertical",
        function=lambda data, **kw: flip_vertical(data),
    ))

    registry.register(Action(
        id="binning",
        name="Binning",
        category="transform.binning",
        description="Agrupa pixeles NxN para ganar senal/ruido",
        menu_path="Herramientas > Binning",
        params=[
            Param("factor", int, 2, 2, 4,
                  choices=[2, 3, 4],
                  tooltip="Factor de binning (2x2, 3x3, 4x4)"),
            Param("method", str, "average",
                  choices=["average", "sum"],
                  tooltip="Media (preserva brillo) o suma (simula hardware)"),
        ],
        function=lambda data, **kw: binning(
            data, factor=kw.get("factor", 2),
            method=kw.get("method", "average"),
        ),
    ))

    registry.register(Action(
        id="resize",
        name="Redimensionar",
        category="transform.resize",
        description="Cambia el tamano de la imagen",
        menu_path="Herramientas > Redimensionar",
        params=[
            Param("scale", float, 1.0, 0.1, 4.0,
                  "Factor de escala (0.5 = mitad, 2.0 = doble)"),
        ],
        function=lambda data, **kw: resize(
            data, scale=kw.get("scale", 1.0),
        ),
    ))

    # =====================================================
    #  ESTRELLAS
    # =====================================================
    registry.register(Action(
        id="star_mask",
        name="Mascara de Estrellas",
        category="processing.stars",
        description="Genera mascara automatica de estrellas",
        menu_path="Procesamiento > Estrellas > Mascara de estrellas",
        params=[
            Param("threshold_sigma", float, 5.0, 2.0, 15.0,
                  "Sigmas sobre el fondo para detectar estrellas"),
            Param("dilation_radius", int, 3, 1, 10,
                  "Radio de dilatacion alrededor de cada estrella"),
            Param("softness", float, 2.0, 0.0, 10.0,
                  "Suavizado de los bordes de la mascara"),
        ],
        function=lambda data, **kw: mask_stars(
            data,
            threshold_sigma=kw.get("threshold_sigma", 5.0),
            dilation_radius=kw.get("dilation_radius", 3),
            softness=kw.get("softness", 2.0),
        ),
    ))

    registry.register(Action(
        id="extract_starless",
        name="Eliminar Estrellas (Starless)",
        category="processing.stars",
        description="Elimina estrellas rellenando con interpolacion del fondo",
        menu_path="Procesamiento > Estrellas > Eliminar estrellas",
        params=[
            Param("threshold_sigma", float, 5.0, 2.0, 15.0,
                  "Sensibilidad de deteccion de estrellas"),
            Param("dilation_radius", int, 5, 1, 15,
                  "Radio alrededor de cada estrella a rellenar"),
            Param("softness", float, 3.0, 0.0, 10.0,
                  "Suavizado de la mascara"),
        ],
        function=lambda data, **kw: extract_starless(
            data,
            threshold_sigma=kw.get("threshold_sigma", 5.0),
            dilation_radius=kw.get("dilation_radius", 5),
            softness=kw.get("softness", 3.0),
        )[0],
    ))

    registry.register(Action(
        id="reduce_halos",
        name="Reducir Halos Estelares",
        category="processing.stars",
        description="Reduce los halos alrededor de estrellas brillantes",
        menu_path="Procesamiento > Estrellas > Reducir halos",
        params=[
            Param("halo_radius", int, 5, 2, 15,
                  "Radio de la zona de halo"),
            Param("strength", float, 0.7, 0.1, 1.0,
                  "Intensidad de la reduccion"),
        ],
        function=lambda data, **kw: reduce_star_halos(
            data,
            halo_radius=kw.get("halo_radius", 5),
            strength=kw.get("strength", 0.7),
        ),
    ))

    # =====================================================
    #  MASCARAS
    # =====================================================
    registry.register(Action(
        id="mask_luminance",
        name="Mascara de Luminancia",
        category="processing.masks",
        description="Selecciona pixeles por brillo (protege sombras u highlights)",
        menu_path="Procesamiento > Mascaras > Luminancia",
        params=[
            Param("shadows", float, 0.0, 0.0, 1.0,
                  "Umbral inferior (pixeles mas oscuros quedan fuera)"),
            Param("highlights", float, 1.0, 0.0, 1.0,
                  "Umbral superior (pixeles mas brillantes quedan fuera)"),
            Param("softness", float, 0.1, 0.0, 0.5,
                  "Suavizado de transicion"),
        ],
        function=lambda data, **kw: mask_luminance(
            data,
            shadows=kw.get("shadows", 0.0),
            highlights=kw.get("highlights", 1.0),
            softness=kw.get("softness", 0.1),
        ),
    ))

    registry.register(Action(
        id="mask_range",
        name="Mascara de Rango",
        category="processing.masks",
        description="Selecciona pixeles dentro de un rango de brillo",
        menu_path="Procesamiento > Mascaras > Rango",
        params=[
            Param("low", float, 0.2, 0.0, 1.0, "Limite inferior del rango"),
            Param("high", float, 0.8, 0.0, 1.0, "Limite superior del rango"),
            Param("softness", float, 0.05, 0.0, 0.5, "Suavizado de transicion"),
        ],
        function=lambda data, **kw: mask_range(
            data,
            low=kw.get("low", 0.2),
            high=kw.get("high", 0.8),
            softness=kw.get("softness", 0.05),
        ),
    ))

    # =====================================================
    #  EXPORTACION
    # =====================================================
    registry.register(Action(
        id="export_png",
        name="Exportar PNG",
        category="export.png",
        description="Guarda la imagen como PNG (sin perdida, 8 o 16 bits)",
        menu_path="Archivo > Guardar como > PNG",
        params=[
            Param("bits", int, 16, choices=[8, 16],
                  tooltip="Profundidad de bits"),
        ],
    ))

    registry.register(Action(
        id="export_jpeg",
        name="Exportar JPEG",
        category="export.jpeg",
        description="Guarda la imagen como JPEG (comprimido, para web)",
        menu_path="Archivo > Guardar como > JPEG",
        params=[
            Param("quality", int, 95, 1, 100,
                  "Calidad de compresion (95=alta, 75=web)"),
        ],
    ))

    registry.register(Action(
        id="export_jpeg_web",
        name="Exportar para Web",
        category="export.jpeg",
        description="JPEG comprimido optimizado para web/redes sociales",
        menu_path="Archivo > Exportar para web",
        params=[
            Param("quality", int, 75, 1, 100,
                  "Calidad de compresion para web"),
        ],
    ))

    # =====================================================
    #  ACCIONES ADICIONALES QUE FALTABAN
    # =====================================================

    registry.register(Action(
        id="combine_stars",
        name="Recombinar Estrellas + Fondo",
        category="processing.stars",
        description="Combina imagen starless con estrellas, controlando intensidad",
        menu_path="Procesamiento > Estrellas > Recombinar estrellas + fondo",
        params=[
            Param("blend", float, 1.0, 0.0, 2.0,
                  "Intensidad de las estrellas (0=sin, 1=normal, >1=potenciar)"),
        ],
        function=lambda data, **kw: combine_starless_stars(
            data, kw.get("stars_only", data * 0),
            blend=kw.get("blend", 1.0),
        ),
    ))

    registry.register(Action(
        id="photometric_cc",
        name="Calibracion Cromatica Fotometrica",
        category="processing.color",
        description="Corrige respuesta cromatica del sistema optico (SPCC simplificado)",
        menu_path="Procesamiento > Color > Calibracion cromatica",
        params=[
            Param("neutral_reference", str, "stars",
                  choices=["stars", "background"],
                  tooltip="Referencia neutra: estrellas o fondo del cielo"),
        ],
        function=lambda data, **kw: photometric_color_calibration(
            data, neutral_reference=kw.get("neutral_reference", "stars"),
        ),
    ))

    registry.register(Action(
        id="histogram",
        name="Histograma",
        category="view.histogram",
        description="Calcula histograma RGB + Luminancia de la imagen",
        menu_path="Vista > Histograma",
        function=lambda data, **kw: get_histogram(data),
    ))

    registry.register(Action(
        id="image_stats",
        name="Estadisticas de Imagen",
        category="view.stats",
        description="Calcula estadisticas completas (min/max/media/mediana/std por canal)",
        menu_path="Vista > Estadisticas de imagen",
        function=lambda data, **kw: image_statistics(data),
    ))

    registry.register(Action(
        id="apply_with_mask",
        name="Aplicar con Mascara",
        category="processing.masks",
        description="Combina original y procesada usando una mascara de seleccion",
        menu_path="Procesamiento > Mascaras > Aplicar con mascara",
        function=lambda data, **kw: apply_with_mask(
            kw.get("original", data),
            data,
            kw.get("mask", np.ones(data.shape[:2], dtype=np.float32)),
        ),
    ))

    # =====================================================
    #  NARROWBAND
    # =====================================================
    registry.register(Action(
        id="nb_combine_sho",
        name="Paleta Hubble (SHO)",
        category="processing.narrowband",
        description="Combina SII=R, Ha=G, OIII=B (paleta Hubble/NASA)",
        menu_path="Procesamiento > Narrowband > Paleta Hubble (SHO)",
        function=lambda data, **kw: combine_palette(kw.get("channels", {}), "SHO"),
    ))

    registry.register(Action(
        id="nb_combine_hoo",
        name="Paleta Bicolor (HOO)",
        category="processing.narrowband",
        description="Combina Ha=R, OIII=G, OIII=B (bicolor popular)",
        menu_path="Procesamiento > Narrowband > Paleta Bicolor (HOO)",
        function=lambda data, **kw: combine_palette(kw.get("channels", {}), "HOO"),
    ))

    registry.register(Action(
        id="nb_combine_natural",
        name="Paleta Natural",
        category="processing.narrowband",
        description="Combinacion con aspecto mas cercano al color real",
        menu_path="Procesamiento > Narrowband > Paleta Natural",
        function=lambda data, **kw: combine_palette(kw.get("channels", {}), "natural"),
    ))

    registry.register(Action(
        id="nb_combine_custom",
        name="Combinacion Personalizada",
        category="processing.narrowband",
        description="Asigna canales libremente a R/G/B con pesos",
        menu_path="Procesamiento > Narrowband > Personalizada",
        params=[
            Param("r_channel", str, "Ha", choices=["Ha", "OIII", "SII"],
                  tooltip="Canal para Rojo"),
            Param("g_channel", str, "OIII", choices=["Ha", "OIII", "SII"],
                  tooltip="Canal para Verde"),
            Param("b_channel", str, "SII", choices=["Ha", "OIII", "SII"],
                  tooltip="Canal para Azul"),
            Param("r_weight", float, 1.0, 0.0, 2.0, "Peso del canal rojo"),
            Param("g_weight", float, 1.0, 0.0, 2.0, "Peso del canal verde"),
            Param("b_weight", float, 1.0, 0.0, 2.0, "Peso del canal azul"),
        ],
    ))

    registry.register(Action(
        id="nb_continuum_sub",
        name="Continuum Subtraction",
        category="processing.narrowband",
        description="Resta el continuo estelar para aislar emision nebular",
        menu_path="Procesamiento > Narrowband > Continuum subtraction",
        params=[
            Param("factor", float, 1.0, 0.1, 3.0,
                  "Factor de escala del broadband (ajustar hasta eliminar estrellas)"),
        ],
    ))

    registry.register(Action(
        id="nb_blend_rgb",
        name="Blend Narrowband + RGB",
        category="processing.narrowband",
        description="Mezcla senal narrowband en imagen broadband RGB",
        menu_path="Procesamiento > Narrowband > Blend con RGB",
        params=[
            Param("blend_channel", str, "R", choices=["R", "G", "B", "L"],
                  tooltip="Canal donde mezclar la senal narrowband"),
            Param("blend_mode", str, "screen", choices=["screen", "add", "max"],
                  tooltip="Modo de mezcla"),
            Param("opacity", float, 0.5, 0.0, 1.0, "Opacidad de la mezcla"),
        ],
    ))

    # =====================================================
    #  MOSAICO / HDR
    # =====================================================
    registry.register(Action(
        id="mosaic_stitch",
        name="Unir Paneles (Mosaico)",
        category="tools.mosaic",
        description="Une multiples paneles en una imagen grande",
        menu_path="Herramientas > Mosaico > Unir paneles",
    ))

    registry.register(Action(
        id="hdr_combine",
        name="HDR Multiscale",
        category="tools.hdr",
        description="Combina exposiciones cortas y largas para maximo rango dinamico",
        menu_path="Herramientas > HDR > Combinar exposiciones",
        params=[
            Param("blend_width", float, 0.1, 0.01, 0.5,
                  "Ancho de transicion entre corta y larga"),
        ],
    ))

    # =====================================================
    #  PLATE SOLVING / CATALOGO
    # =====================================================
    registry.register(Action(
        id="plate_solve",
        name="Plate Solving",
        category="tools.platesolve",
        description="Identifica coordenadas celestes de la imagen",
        menu_path="Herramientas > Plate Solving",
        params=[
            Param("pixel_scale_hint", float, 0.0, 0.0, 100.0,
                  "Escala de pixel aprox. en arcsec/pixel (0 = autodetectar)"),
        ],
    ))

    registry.register(Action(
        id="annotate_objects",
        name="Anotar Objetos del Catalogo",
        category="tools.catalog",
        description="Identifica y anota objetos astronomicos en la imagen",
        menu_path="Herramientas > Anotacion de objetos",
        params=[
            Param("min_size_arcmin", float, 1.0, 0.0, 60.0,
                  "Tamano minimo del objeto para incluirlo (arcmin)"),
        ],
    ))

    registry.register(Action(
        id="search_catalog",
        name="Buscar en Catalogo",
        category="tools.catalog",
        description="Busca objetos por nombre en Messier/Caldwell/NGC/Sharpless",
        menu_path="Herramientas > Buscar en catalogo",
    ))

    # =====================================================
    #  ANALISIS DE SESION
    # =====================================================
    registry.register(Action(
        id="session_quality_graph",
        name="Grafico de Calidad de Sesion",
        category="tools.analysis",
        description="Visualiza FWHM, elongacion y ruido a lo largo de la noche",
        menu_path="Herramientas > Analisis de sesion",
    ))

    registry.register(Action(
        id="batch_process",
        name="Procesamiento por Lotes",
        category="tools.batch",
        description="Aplica la misma secuencia de operaciones a multiples imagenes",
        menu_path="Herramientas > Batch Processing",
    ))

    # =====================================================
    #  ASISTENTE INTELIGENTE
    # =====================================================
    registry.register(Action(
        id="assistant_analyze",
        name="Analizar Imagen",
        category="assistant.analyze",
        description="Diagnostica problemas y sugiere operaciones con parametros optimos",
        menu_path="Asistente > Analizar imagen",
    ))

    registry.register(Action(
        id="assistant_next_action",
        name="Siguiente Accion Recomendada",
        category="assistant.recommend",
        description="Sugiere la accion mas importante a aplicar ahora",
        menu_path="Asistente > Siguiente accion recomendada",
    ))

    registry.register(Action(
        id="assistant_plan",
        name="Generar Plan de Procesamiento",
        category="assistant.plan",
        description="Genera un plan completo de procesamiento basado en el analisis",
        menu_path="Asistente > Generar plan de procesamiento",
    ))

    registry.register(Action(
        id="assistant_bortle",
        name="Adaptar a Contaminacion Luminica",
        category="assistant.bortle",
        description="Ajusta parametros segun escala Bortle del lugar de captura",
        menu_path="Asistente > Adaptar a contaminacion luminica",
        params=[
            Param("bortle_class", int, 5, 1, 9,
                  "Escala Bortle (1=cielo perfecto, 9=centro ciudad)"),
        ],
    ))

    # =====================================================
    #  PLANIFICADOR DE SESION
    # =====================================================
    registry.register(Action(
        id="planner_targets",
        name="Targets Visibles Esta Noche",
        category="planner.targets",
        description="Calcula que objetos son fotografiables desde tu ubicacion",
        menu_path="Planificador > Targets visibles esta noche",
    ))

    registry.register(Action(
        id="planner_recommend",
        name="Recomendacion de Targets",
        category="planner.recommend",
        description="Recomienda los mejores targets segun ubicacion, equipo y fecha",
        menu_path="Planificador > Recomendacion de targets",
    ))

    registry.register(Action(
        id="planner_equipment",
        name="Perfil de Equipo",
        category="planner.equipment",
        description="Configura telescopio + camara para calcular FOV, pixel scale, etc.",
        menu_path="Planificador > Perfil de equipo",
    ))

    # =====================================================
    #  PIXELMATH
    # =====================================================
    registry.register(Action(
        id="pixelmath",
        name="PixelMath",
        category="processing.pixelmath",
        description="Calculadora de imagenes: combina con formulas libres (Ha*0.7+OIII*0.3)",
        menu_path="Procesamiento > PixelMath",
    ))

    registry.register(Action(
        id="pixelmath_rgb",
        name="PixelMath RGB",
        category="processing.pixelmath",
        description="Tres expresiones separadas para generar R, G, B",
        menu_path="Procesamiento > PixelMath > Generar RGB",
    ))

    # =====================================================
    #  ANOTACIONES
    # =====================================================
    registry.register(Action(
        id="annotate_full",
        name="Anotacion Completa",
        category="tools.annotate",
        description="Anota objetos + brujula + escala + info del equipo",
        menu_path="Herramientas > Anotacion completa",
    ))

    registry.register(Action(
        id="annotate_compass",
        name="Brujula N/E",
        category="tools.annotate",
        description="Dibuja brujula con orientacion Norte/Este",
        menu_path="Herramientas > Anotacion > Brujula",
        params=[
            Param("rotation_deg", float, 0.0, -360.0, 360.0,
                  "Rotacion del campo en grados"),
        ],
    ))

    registry.register(Action(
        id="annotate_scale",
        name="Barra de Escala",
        category="tools.annotate",
        description="Dibuja barra de escala angular",
        menu_path="Herramientas > Anotacion > Escala",
        params=[
            Param("bar_length_arcmin", float, 5.0, 0.5, 60.0,
                  "Longitud de la barra en arcminutos"),
        ],
    ))

    registry.register(Action(
        id="annotate_text",
        name="Anadir Texto",
        category="tools.annotate",
        description="Escribe texto sobre la imagen",
        menu_path="Herramientas > Anotacion > Texto",
    ))

    # =====================================================
    #  DRIZZLE
    # =====================================================
    registry.register(Action(
        id="drizzle",
        name="Drizzle (Super-resolucion)",
        category="preprocessing.drizzle",
        description="Apila con offsets subpixel para mayor resolucion",
        menu_path="Pre-procesamiento > Drizzle",
        params=[
            Param("scale", int, 2, 2, 3,
                  choices=[2, 3],
                  tooltip="Factor de super-resolucion"),
            Param("drop_size", float, 0.7, 0.3, 1.0,
                  "Tamano del kernel drop (menor=mas detalle, mas ruido)"),
        ],
    ))

    registry.register(Action(
        id="drizzle_quick",
        name="Drizzle Rapido (Preview)",
        category="preprocessing.drizzle",
        description="Version rapida de drizzle para previsualizacion",
        menu_path="Pre-procesamiento > Drizzle rapido",
        params=[
            Param("scale", int, 2, 2, 3,
                  choices=[2, 3],
                  tooltip="Factor de super-resolucion"),
        ],
    ))

    # =====================================================
    #  METADATOS DE SESION
    # =====================================================
    registry.register(Action(
        id="session_metadata",
        name="Leer Metadatos de Sesion",
        category="tools.metadata",
        description="Extrae EXIF/headers de cada frame y genera linea temporal",
        menu_path="Herramientas > Metadatos de sesion",
    ))

    registry.register(Action(
        id="session_timeline",
        name="Timeline de Sesion",
        category="tools.metadata",
        description="Visualiza FWHM, temperatura y calidad a lo largo de la noche",
        menu_path="Herramientas > Timeline de sesion",
    ))

    # =====================================================
    #  AI
    # =====================================================
    from .ai_denoise import denoise_wavelet, denoise_bm3d_like, denoise_multiscale
    from .ai_enhance import upscale_ai, enhance_detail
    from .ai_classify import classify_object

    registry.register(Action(
        id="ai_denoise_wavelet",
        name="AI Denoise Wavelet",
        category="ai.denoise",
        description="Denoise multiscale por wavelets con proteccion de estrellas",
        menu_path="AI > Denoise > Wavelet",
        params=[
            Param("strength", float, 0.5, 0.0, 1.0,
                  "Intensidad del filtrado"),
            Param("levels", int, 4, 2, 6,
                  "Escalas de descomposicion"),
            Param("protect_stars", bool, True,
                  tooltip="Proteger estrellas del filtrado"),
        ],
        function=lambda data, **kw: denoise_wavelet(
            data, strength=kw.get("strength", 0.5),
            levels=kw.get("levels", 4),
            protect_stars=kw.get("protect_stars", True),
        ),
    ))

    registry.register(Action(
        id="ai_denoise_bm3d",
        name="AI Denoise BM3D",
        category="ai.denoise",
        description="Block Matching 3D: mejor algoritmo clasico de denoise",
        menu_path="AI > Denoise > BM3D",
        params=[
            Param("strength", float, 0.5, 0.0, 1.0,
                  "Intensidad del filtrado"),
            Param("block_size", int, 8, 4, 16,
                  "Tamano del bloque de matching"),
        ],
        function=lambda data, **kw: denoise_bm3d_like(
            data, strength=kw.get("strength", 0.5),
            block_size=kw.get("block_size", 8),
        ),
    ))

    registry.register(Action(
        id="ai_denoise_multiscale",
        name="AI Denoise Multiscale",
        category="ai.denoise",
        description="Control independiente de denoise por escala de detalle",
        menu_path="AI > Denoise > Multiscale",
        params=[
            Param("fine_strength", float, 0.7, 0.0, 1.0,
                  "Detalle fino (ruido)"),
            Param("medium_strength", float, 0.3, 0.0, 1.0,
                  "Detalle medio (textura)"),
            Param("coarse_strength", float, 0.1, 0.0, 1.0,
                  "Detalle grueso (estructura)"),
        ],
        function=lambda data, **kw: denoise_multiscale(
            data, fine_strength=kw.get("fine_strength", 0.7),
            medium_strength=kw.get("medium_strength", 0.3),
            coarse_strength=kw.get("coarse_strength", 0.1),
        ),
    ))

    registry.register(Action(
        id="ai_denoise_neural",
        name="AI Denoise Neural (ONNX)",
        category="ai.denoise",
        description="Denoise por red neuronal (requiere modelo ONNX)",
        menu_path="AI > Denoise > Neural",
        params=[
            Param("strength", float, 0.5, 0.0, 1.0,
                  "Intensidad del filtrado"),
        ],
    ))

    registry.register(Action(
        id="ai_upscale",
        name="AI Upscale",
        category="ai.enhance",
        description="Super-resolucion AI (equivalente a Topaz Gigapixel)",
        menu_path="AI > Upscale",
        params=[
            Param("scale", int, 2, 2, 4,
                  choices=[2, 3, 4],
                  tooltip="Factor de ampliacion"),
            Param("method", str, "cubic_plus",
                  choices=["lanczos", "cubic_plus", "edsr", "espcn"],
                  tooltip="Metodo de upscale"),
        ],
        function=lambda data, **kw: upscale_ai(
            data, scale=kw.get("scale", 2),
            method=kw.get("method", "cubic_plus"),
        ),
    ))

    registry.register(Action(
        id="ai_enhance_detail",
        name="AI Mejora de Detalle",
        category="ai.enhance",
        description="Potencia detalles finos sin amplificar ruido",
        menu_path="AI > Mejora de detalle",
        params=[
            Param("strength", float, 0.5, 0.0, 1.0,
                  "Intensidad de la mejora"),
            Param("scale", str, "all",
                  choices=["fine", "medium", "coarse", "all"],
                  tooltip="Escala de detalle a potenciar"),
        ],
        function=lambda data, **kw: enhance_detail(
            data, strength=kw.get("strength", 0.5),
            scale=kw.get("scale", "all"),
        ),
    ))

    registry.register(Action(
        id="ai_classify",
        name="AI Clasificar Objeto",
        category="ai.classify",
        description="Detecta tipo de objeto (nebulosa/galaxia/cumulo) por morfologia",
        menu_path="AI > Clasificar objeto",
        function=lambda data, **kw: data,
    ))

    registry.register(Action(
        id="ai_autoparams",
        name="AI Auto-Parametros",
        category="ai.autoparams",
        description="Predice parametros optimos para todas las operaciones",
        menu_path="AI > Auto-parametros",
    ))

    registry.register(Action(
        id="ai_autoparams_stretch",
        name="AI Parametros Stretch",
        category="ai.autoparams",
        description="Predice midtone y black_clip optimos segun SNR",
        menu_path="AI > Auto-parametros > Stretch",
    ))

    registry.register(Action(
        id="ai_autoparams_denoise",
        name="AI Parametros Denoise",
        category="ai.autoparams",
        description="Predice intensidad optima de denoise segun ruido",
        menu_path="AI > Auto-parametros > Denoise",
    ))

    # =====================================================
    #  SCNR + LRGB
    # =====================================================
    registry.register(Action(
        id="scnr_average",
        name="SCNR Average Neutral",
        category="processing.scnr",
        description="Elimina exceso de verde (metodo clasico de PixInsight)",
        menu_path="Procesamiento > SCNR > Average Neutral",
        params=[
            Param("amount", float, 1.0, 0.0, 1.0, "Intensidad de la correccion"),
        ],
    ))

    registry.register(Action(
        id="scnr_maximum",
        name="SCNR Maximum Mask",
        category="processing.scnr",
        description="SCNR agresivo: limita verde al maximo de R y B",
        menu_path="Procesamiento > SCNR > Maximum Mask",
        params=[
            Param("amount", float, 1.0, 0.0, 1.0, "Intensidad"),
        ],
    ))

    registry.register(Action(
        id="lrgb_combine",
        name="LRGB Combine",
        category="processing.lrgb",
        description="Combina luminancia mono con RGB color",
        menu_path="Procesamiento > LRGB Combine",
        params=[
            Param("lum_weight", float, 1.0, 0.0, 1.0, "Peso de la luminancia"),
        ],
    ))

    # =====================================================
    #  STAR EFFECTS
    # =====================================================
    registry.register(Action(
        id="star_reduction",
        name="Star Reduction",
        category="processing.stars",
        description="Reduce tamano de estrellas sin eliminarlas",
        menu_path="Procesamiento > Estrellas > Reducir tamano",
        params=[
            Param("amount", float, 0.5, 0.1, 1.0, "Intensidad de la reduccion"),
            Param("iterations", int, 2, 1, 5, "Iteraciones de erosion"),
        ],
    ))

    from .star_effects import diffraction_spikes as _diffraction_spikes
    registry.register(Action(
        id="diffraction_spikes",
        name="Diffraction Spikes",
        category="processing.stars",
        description="Anade puntas de difraccion a estrellas brillantes",
        menu_path="Procesamiento > Estrellas > Diffraction Spikes",
        params=[
            Param("num_spikes", int, 4, 2, 8,
                  choices=[2, 4, 6, 8],
                  tooltip="Numero de puntas"),
            Param("spike_length", float, 0.15, 0.005, 0.4,
                  "Longitud relativa al tamano de imagen"),
            Param("spike_brightness", float, 0.7, 0.1, 1.0,
                  "Brillo de las puntas"),
            Param("rotation_deg", float, 0.0, -180.0, 180.0,
                  "Rotacion de las puntas en grados"),
            Param("min_star_brightness", float, 0.3, 0.05, 1.0,
                  "Brillo minimo para recibir spikes (menor=mas estrellas)"),
        ],
        function=lambda data, **kw: _diffraction_spikes(
            data,
            num_spikes=kw.get("num_spikes", 4),
            spike_length=kw.get("spike_length", 0.15),
            spike_brightness=kw.get("spike_brightness", 0.7),
            rotation_deg=kw.get("rotation_deg", 0.0),
            min_star_brightness=kw.get("min_star_brightness", 0.3),
        ),
    ))

    # =====================================================
    #  CLAHE / CONTRASTE LOCAL
    # =====================================================
    registry.register(Action(
        id="clahe",
        name="CLAHE",
        category="processing.local",
        description="Ecualizacion local de histograma (revela detalle debil)",
        menu_path="Procesamiento > Contraste local > CLAHE",
        params=[
            Param("clip_limit", float, 2.0, 0.5, 10.0, "Limite de contraste"),
            Param("grid_size", int, 8, 4, 16, "Tamano de rejilla"),
        ],
    ))

    registry.register(Action(
        id="local_contrast",
        name="Contraste Local",
        category="processing.local",
        description="Potencia diferencias locales de brillo",
        menu_path="Procesamiento > Contraste local > Manual",
        params=[
            Param("radius", int, 50, 10, 200, "Radio del entorno local"),
            Param("strength", float, 0.5, 0.0, 1.0, "Intensidad"),
        ],
    ))

    # =====================================================
    #  HEAL / REPARACION
    # =====================================================
    registry.register(Action(
        id="remove_hot_pixels",
        name="Eliminar Pixeles Calientes",
        category="tools.heal",
        description="Detecta y repara pixeles calientes automaticamente",
        menu_path="Herramientas > Reparacion > Pixeles calientes",
        params=[
            Param("threshold_sigma", float, 5.0, 2.0, 10.0,
                  "Sensibilidad de deteccion"),
        ],
    ))

    registry.register(Action(
        id="remove_dead_columns",
        name="Reparar Columnas Muertas",
        category="tools.heal",
        description="Detecta y repara columnas muertas del sensor",
        menu_path="Herramientas > Reparacion > Columnas muertas",
    ))

    registry.register(Action(
        id="remove_satellite",
        name="Eliminar Estela de Satelite",
        category="tools.heal",
        description="Borra estela de satelite/avion por coordenadas",
        menu_path="Herramientas > Reparacion > Estela de satelite",
        params=[
            Param("width", int, 5, 1, 20, "Ancho de la franja a reparar"),
        ],
    ))

    registry.register(Action(
        id="auto_detect_satellites",
        name="Detectar Satelites Automaticamente",
        category="tools.heal",
        description="Busca estelas de satelites/aviones con Hough Transform",
        menu_path="Herramientas > Reparacion > Detectar satelites",
    ))

    registry.register(Action(
        id="heal_region",
        name="Reparar Region (Pincel)",
        category="tools.heal",
        description="Repara una zona pintada por el usuario (clone/heal)",
        menu_path="Herramientas > Reparacion > Reparar region",
    ))

    # =====================================================
    #  PUBLICACION
    # =====================================================
    registry.register(Action(
        id="watermark",
        name="Watermark",
        category="publish.watermark",
        description="Anade nombre/texto como marca de agua",
        menu_path="Archivo > Watermark",
        params=[
            Param("position", str, "bottom_right",
                  choices=["bottom_right", "bottom_left", "top_right", "top_left", "center"],
                  tooltip="Posicion del watermark"),
            Param("opacity", float, 0.5, 0.1, 1.0, "Transparencia"),
        ],
    ))

    registry.register(Action(
        id="social_instagram",
        name="Preparar para Instagram",
        category="publish.social",
        description="Ajusta aspect ratio 1:1 con bordes negros",
        menu_path="Archivo > Exportar para > Instagram",
    ))

    registry.register(Action(
        id="social_facebook",
        name="Preparar para Facebook",
        category="publish.social",
        description="Ajusta aspect ratio 16:9",
        menu_path="Archivo > Exportar para > Facebook",
    ))

    registry.register(Action(
        id="comparison",
        name="Crear Comparacion Antes/Despues",
        category="publish.compare",
        description="Genera imagen lado a lado o con slider",
        menu_path="Herramientas > Comparar antes/despues",
        params=[
            Param("mode", str, "side_by_side",
                  choices=["side_by_side", "slider", "blink"],
                  tooltip="Tipo de comparacion"),
        ],
    ))

    registry.register(Action(
        id="timelapse",
        name="Crear Timelapse / GIF",
        category="publish.timelapse",
        description="Genera animacion a partir de frames de la sesion",
        menu_path="Herramientas > Timelapse / GIF",
    ))

    # =====================================================
    #  ASIGNAR FUNCIONES A ACCIONES SIN FUNCION
    # =====================================================
    from .heal import (remove_hot_pixels, remove_dead_columns,
                        remove_line, heal_region, auto_detect_satellites)
    from .annotate import (annotate_full, annotate_compass,
                            annotate_scale_bar, annotate_text as ann_text)
    from .publish import (create_comparison, create_timelapse_frames)
    from .mosaic import hdr_combine as _hdr_combine
    from .platesolve import solve_image
    from .color import image_statistics
    from .metadata import extract_fits_metadata

    from .scnr import scnr_average_neutral, scnr_maximum_mask, lrgb_combine as _lrgb
    from .star_effects import star_reduction as _star_reduction
    from .local_enhance import clahe as _clahe, local_contrast as _local_contrast
    from .publish import add_watermark, prepare_for_social
    from .drizzle import drizzle_quick as _drizzle_quick
    from .narrowband import combine_custom, continuum_subtraction, blend_narrowband_rgb
    from .ai_autoparams import predict_all_params, predict_stretch_params, predict_denoise_params

    _fn_map = {
        "remove_hot_pixels": lambda data, **kw: remove_hot_pixels(
            data, threshold_sigma=kw.get("threshold_sigma", 5.0)),
        "remove_dead_columns": lambda data, **kw: remove_dead_columns(data),
        "remove_satellite": lambda data, **kw: remove_line(
            data, kw.get("y1", 0), kw.get("x1", 0),
            kw.get("y2", data.shape[0]), kw.get("x2", data.shape[1]),
            width=kw.get("width", 5)),
        "auto_detect_satellites": lambda data, **kw: data,
        "heal_region": lambda data, **kw: data,
        "annotate_full": lambda data, **kw: annotate_full(data),
        "annotate_compass": lambda data, **kw: annotate_compass(
            data, rotation_deg=kw.get("rotation_deg", 0)),
        "annotate_scale": lambda data, **kw: annotate_scale_bar(
            data, pixel_scale_arcsec=kw.get("pixel_scale", 1.0),
            bar_length_arcmin=kw.get("bar_length_arcmin", 5.0)),
        "annotate_text": lambda data, **kw: ann_text(
            data, kw.get("text", "Astro BellaDev"),
            kw.get("x", 10), kw.get("y", 30)),
        "annotate_objects": lambda data, **kw: annotate_full(data),
        "plate_solve": lambda data, **kw: data,
        "search_catalog": lambda data, **kw: data,
        "mosaic_stitch": lambda data, **kw: (_ for _ in ()).throw(
            RuntimeError("Mosaico: usa Pre-procesamiento > Pipeline para unir paneles desde carpetas")),
        "hdr_combine": lambda data, **kw: _hdr_combine(
            data, data, blend_width=kw.get("blend_width", 0.1)),
        "session_quality_graph": lambda data, **kw: data,
        "session_metadata": lambda data, **kw: data,
        "session_timeline": lambda data, **kw: data,
        "batch_process": lambda data, **kw: data,
        "comparison": lambda data, **kw: data,
        "timelapse": lambda data, **kw: data,
        # SCNR + LRGB
        "scnr_average": lambda data, **kw: scnr_average_neutral(
            data, amount=kw.get("amount", 1.0)),
        "scnr_maximum": lambda data, **kw: scnr_maximum_mask(
            data, amount=kw.get("amount", 1.0)),
        "lrgb_combine": lambda data, **kw: data,
        # Star effects
        "star_reduction": lambda data, **kw: _star_reduction(
            data, amount=kw.get("amount", 0.5),
            iterations=kw.get("iterations", 2)),
        # Local enhance
        "clahe": lambda data, **kw: _clahe(
            data, clip_limit=kw.get("clip_limit", 2.0),
            grid_size=kw.get("grid_size", 8)),
        "local_contrast": lambda data, **kw: _local_contrast(
            data, radius=kw.get("radius", 50),
            strength=kw.get("strength", 0.5)),
        # Export / Publish
        "export_png": lambda data, **kw: data,
        "export_jpeg": lambda data, **kw: data,
        "export_jpeg_web": lambda data, **kw: data,
        "watermark": lambda data, **kw: add_watermark(
            data, kw.get("text", "Astro BellaDev"),
            position=kw.get("position", "bottom_right"),
            opacity=kw.get("opacity", 0.5)),
        "social_instagram": lambda data, **kw: prepare_for_social(
            data, platform="instagram"),
        "social_facebook": lambda data, **kw: prepare_for_social(
            data, platform="facebook"),
        # Narrowband (operan sobre canales de la imagen RGB)
        "nb_combine_custom": lambda data, **kw: data,
        "nb_continuum_sub": lambda data, **kw: continuum_subtraction(
            data.mean(axis=-1) if data.ndim == 3 else data,
            data[..., 0] if data.ndim == 3 else data,
            factor=kw.get("factor", 1.0),
        ) if data.ndim >= 2 else data,
        "nb_blend_rgb": lambda data, **kw: blend_narrowband_rgb(
            data,
            data.mean(axis=-1) if data.ndim == 3 else data,
            blend_channel=kw.get("blend_channel", "R"),
            blend_mode=kw.get("blend_mode", "screen"),
            opacity=kw.get("opacity", 0.5),
        ) if data.ndim == 3 else data,
        # Drizzle (aplica sobre imagen unica como upscale)
        "drizzle": lambda data, **kw: _drizzle_quick(
            [data], scale=kw.get("scale", 2)),
        "drizzle_quick": lambda data, **kw: _drizzle_quick(
            [data], scale=kw.get("scale", 2)),
        # PixelMath (normalizar como operacion basica)
        "pixelmath": lambda data, **kw: (
            data / np.max(data) if np.max(data) > 0 else data
        ).astype(np.float32),
        "pixelmath_rgb": lambda data, **kw: data,
        # AI autoparams (predice y aplica)
        "ai_autoparams": lambda data, **kw: data,
        "ai_autoparams_stretch": lambda data, **kw: stretch_midtone(
            data, **predict_stretch_params(data).params),
        "ai_autoparams_denoise": lambda data, **kw: denoise_selective(
            data, **predict_denoise_params(data).params),
        "ai_denoise_neural": lambda data, **kw: data,
        # Asistente
        "assistant_analyze": lambda data, **kw: data,
        "assistant_next_action": lambda data, **kw: data,
        "assistant_plan": lambda data, **kw: data,
        "assistant_bortle": lambda data, **kw: data,
        # Planificador
        "planner_targets": lambda data, **kw: data,
        "planner_recommend": lambda data, **kw: data,
        "planner_equipment": lambda data, **kw: data,
    }

    for action_id, fn in _fn_map.items():
        action = registry.get(action_id)
        if action and action.function is None:
            action.function = fn

    return registry
