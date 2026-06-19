# Astro BellaDev

Motor de procesamiento de astrofotografía en Python. Alternativa libre
a PixInsight/Siril/SASpro, diseñado para ser **mucho más sencillo de
usar** sin sacrificar potencia.

> Si en algún momento se reutiliza código de Siril/SASpro (ambos
> GPLv3), el proyecto deberá licenciarse como GPLv3.

---

## Filosofía: Modo Auto + Modo Experto

Lo que diferencia a Astro BellaDev de la competencia:

| | PixInsight | Siril | SASpro | **Astro BellaDev** |
|---|---|---|---|---|
| Potencia | ★★★★★ | ★★★★ | ★★★ | ★★★★ |
| Facilidad | ★★ | ★★★ | ★★★★ | ★★★★★ |
| Precio | ~230€ | Gratis | ~150€ | **Gratis** |
| Modo auto real | No | Scripts | Parcial | **Sí, nativo** |

- **Modo Auto**: arrastra tu carpeta → imagen final. Detecta tipo de
  objeto, descarta frames malos, elige el procesamiento óptimo.
  Cero parámetros. Para el que acaba de comprarse su primera cámara.
- **Modo Experto**: cada paso tiene sus controles, deslizadores y
  opciones avanzadas. Para el astrofotógrafo que quiere decidir
  exactamente qué pasa en cada punto del pipeline.

Ambos modos usan el mismo motor — el modo auto simplemente elige los
parámetros por ti basándose en análisis de los datos.

### Funcionalidades exclusivas (no disponibles en la competencia)

- **Asistente inteligente**: analiza tu imagen y te dice que le falta,
  con la accion concreta y los parametros optimos. Un mentor integrado.
- **Planificador de sesion**: que objetos fotografiar esta noche segun
  tu ubicacion, fecha y equipo. Con catalogo astronomico integrado
  (158 objetos: Messier, Caldwell, Sharpless).
- **Perfiles de equipo**: configura tu setup una vez y el programa
  calcula pixel scale, FOV, exposicion sugerida y ajusta todos los
  algoritmos automaticamente.
- **Adaptacion a contaminacion luminica**: introduce tu escala Bortle
  y todos los parametros (ABE, denoise, stretch) se ajustan.
- **Batch processing**: aplica la misma macro a 15 sesiones de M31
  en un clic.
- **Toolbars personalizables**: botones con acciones preconfiguradas
  y macros (secuencias), como los Process Icons de PixInsight.
- **Narrowband completo**: paletas SHO/HOO/custom, continuum
  subtraction, blend narrowband+RGB.

---

## Arquitectura de la aplicación

### Flujo de procesamiento (pipeline)

```
┌─────────────────────────────────────────────────────────┐
│                    ASTRO SUITE                          │
│                                                         │
│  ┌──────────┐   Modo Auto: todo en un clic              │
│  │ ENTRADA  │   Modo Experto: paso a paso con preview   │
│  │ Carpeta/ │                                           │
│  │ Archivos │                                           │
│  └────┬─────┘                                           │
│       │                                                  │
│       ▼                                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 1. CARGA           FITS / RAW / TIFF             │   │
│  ├──────────────────────────────────────────────────┤   │
│  │ 2. CALIBRACIÓN     Bias → Dark → Flat            │   │
│  ├──────────────────────────────────────────────────┤   │
│  │ 3. SCORING         Evaluar calidad cada frame    │   │
│  │                    FWHM, elongación, ruido, etc. │   │
│  ├──────────────────────────────────────────────────┤   │
│  │ 4. DEBAYER         CFA/Bayer → RGB               │   │
│  ├──────────────────────────────────────────────────┤   │
│  │ 5. ALINEACIÓN      Registro por estrellas        │   │
│  ├──────────────────────────────────────────────────┤   │
│  │ 6. APILAMIENTO     Media/Mediana/Sigma-clip      │   │
│  ├──────────────────────────────────────────────────┤   │
│  │ 7. POST-PROCESAMIENTO                            │   │
│  │    ├─ Stretch (MTF / Asinh / Auto por target)    │   │
│  │    ├─ Extracción de fondo (ABE/DBE)              │   │
│  │    ├─ Reducción de ruido (denoise)                │   │
│  │    ├─ Nitidez (sharpen/deconvolution)             │   │
│  │    ├─ Balance de color / calibración cromática    │   │
│  │    ├─ Curvas / niveles                            │   │
│  │    ├─ Saturación selectiva                        │   │
│  │    ├─ Eliminación de estrellas (starless)         │   │
│  │    └─ Combinación estrella + nebulosa             │   │
│  ├──────────────────────────────────────────────────┤   │
│  │ 8. EXPORTACIÓN     FITS / TIFF / PNG / JPEG      │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  En modo experto, cada paso se puede ejecutar           │
│  individualmente, con preview antes/después y           │
│  posibilidad de deshacer (Ctrl+Z por paso).             │
└─────────────────────────────────────────────────────────┘
```

### Estructura de menús prevista (GUI)

```
┌─ Archivo
│   ├─ Abrir imagen (FITS/RAW/TIFF)
│   ├─ Abrir carpeta de sesión
│   ├─ Guardar como... (FITS/TIFF/PNG/JPEG)
│   ├─ Exportar para web (JPEG comprimido)
│   ├─ Exportar para Instagram / Facebook
│   ├─ Watermark (marca de agua)
│   └─ Sesiones recientes
│
├─ Pre-procesamiento
│   ├─ Crear Master Bias
│   ├─ Crear Master Dark
│   ├─ Crear Master Flat
│   ├─ Calibrar Light Frames
│   ├─ ── separador ──
│   ├─ Evaluar calidad de frames (Scoring)
│   │   ├─ Ver tabla de puntuaciones
│   │   ├─ Descartar automáticamente (% configurable)
│   │   └─ Selección manual de frames
│   ├─ ── separador ──
│   ├─ Debayer (patrón auto / manual)
│   ├─ Alinear frames
│   └─ Apilar (Sigma-clip / Media / Mediana)
│
├─ Procesamiento
│   ├─ Stretch
│   │   ├─ Auto (detecta tipo de target)
│   │   ├─ Midtone Transfer (STF)
│   │   ├─ Arcsinh Stretch
│   │   └─ Perfiles: Nebulosa / Galaxia / Estrellas / Planetaria
│   ├─ Extracción de fondo
│   │   ├─ ABE (Automatic Background Extraction)
│   │   └─ DBE (Dynamic Background Extraction - puntos manuales)
│   ├─ Reducción de ruido
│   │   ├─ Denoise (luminancia)
│   │   ├─ Denoise (cromático)
│   │   └─ Intensidad (deslizador)
│   ├─ Nitidez
│   │   ├─ Unsharp Mask
│   │   ├─ Deconvolution (Richardson-Lucy)
│   │   └─ Radio / Intensidad (deslizadores)
│   ├─ Color
│   │   ├─ Balance de blancos (por estrellas / manual)
│   │   ├─ Calibración cromática (photometric color)
│   │   ├─ Saturación global
│   │   └─ Saturación selectiva por color
│   ├─ Curvas y Niveles
│   │   ├─ Curvas RGB / Luminancia
│   │   ├─ Niveles (negro / medio / blanco)
│   │   └─ Histograma interactivo
│   ├─ Estrellas
│   │   ├─ Eliminar estrellas (starless)
│   │   ├─ Solo estrellas (star mask)
│   │   ├─ Reducir halos estelares
│   │   └─ Recombinar estrellas + fondo
│   ├─ Máscaras
│   │   ├─ Máscara de luminancia
│   │   ├─ Máscara de rango
│   │   ├─ Aplicar con máscara
│   │   └─ Máscara manual (pincel)
│   ├─ Narrowband
│   │   ├─ Paleta Hubble (SHO)
│   │   ├─ Paleta Bicolor (HOO)
│   │   ├─ Paleta Natural
│   │   ├─ Combinación personalizada
│   │   ├─ Continuum Subtraction
│   │   └─ Blend Narrowband + RGB
│   ├─ PixelMath
│   │   ├─ Expresión libre (Ha * 0.7 + OIII * 0.3)
│   │   └─ Generar RGB (3 expresiones)
│   ├─ SCNR (eliminar verde)
│   │   ├─ Average Neutral
│   │   └─ Maximum Mask
│   ├─ LRGB Combine (luminancia + color)
│   ├─ Contraste local
│   │   ├─ CLAHE (ecualización adaptativa)
│   │   └─ Contraste local manual
│   └─ Estrellas (ampliado)
│       ├─ Diffraction Spikes (4/6/8 puntas)
│       └─ Star Reduction (reducir tamaño)
│
├─ Herramientas
│   ├─ Plate Solving (identificar campo)
│   ├─ Anotación de objetos (catálogo)
│   ├─ Buscar en catálogo (Messier/Caldwell/NGC/Sharpless)
│   ├─ Crop / Rotación / Flip
│   ├─ Binning / Redimensionar
│   ├─ Mosaico (unir paneles)
│   ├─ HDR (combinar exposiciones)
│   ├─ Análisis de sesión (calidad vs tiempo)
│   ├─ Anotación completa (objetos + brújula + escala)
│   ├─ Drizzle (super-resolución 2x/3x)
│   ├─ Reparación
│   │   ├─ Eliminar píxeles calientes (auto)
│   │   ├─ Reparar columnas muertas
│   │   ├─ Eliminar estela de satélite
│   │   ├─ Detectar satélites automáticamente
│   │   └─ Reparar región (pincel/clone)
│   ├─ Metadatos de sesión / Timeline
│   ├─ Batch Processing (lotes)
│   ├─ Comparar antes/después (side by side / slider / blink)
│   ├─ Timelapse / GIF animado
│   └─ Historial de operaciones
│
├─ Asistente
│   ├─ Analizar imagen (diagnostico automático)
│   ├─ Siguiente acción recomendada
│   ├─ Generar plan de procesamiento
│   └─ Adaptar a contaminación lumínica (Bortle)
│
├─ AI
│   ├─ Denoise
│   │   ├─ Wavelet (multiscale con protección de estrellas)
│   │   ├─ BM3D (Block Matching 3D)
│   │   ├─ Multiscale (control por escala de detalle)
│   │   └─ Neural (ONNX, cuando hay modelo disponible)
│   ├─ Upscale (super-resolución estilo Topaz Gigapixel)
│   ├─ Mejora de detalle (fino/medio/grueso/todo)
│   ├─ Clasificar objeto (nebulosa/galaxia/cúmulo por morfología)
│   └─ Auto-parámetros
│       ├─ Predecir todos los parámetros óptimos
│       ├─ Stretch óptimo según SNR
│       └─ Denoise óptimo según ruido
│
├─ Planificador
│   ├─ Targets visibles esta noche
│   ├─ Perfil de equipo (telescopio + cámara)
│   └─ Recomendación de targets
│
├─ Vista
│   ├─ Modo Auto / Experto (toggle)
│   ├─ Panel de preview (zoom, pan)
│   ├─ Histograma
│   ├─ Estadísticas de imagen
│   └─ Canales R/G/B/L por separado
│
└─ Ayuda
    ├─ Guía rápida
    ├─ Atajos de teclado
    └─ Acerca de
```

### Diseño de la interfaz (previsto)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Archivo  Pre-procesamiento  Procesamiento  Herramientas  Vista     │
├──────┬──────────────────────────────────────────────────┬───────────┤
│      │                                                  │           │
│  P   │                                                  │  PANEL    │
│  A   │                                                  │  DERECHO  │
│  N   │            VISTA PREVIA DE IMAGEN                │           │
│  E   │            (zoom, pan, canales)                  │  Paráme-  │
│  L   │                                                  │  tros del │
│      │                                                  │  paso     │
│  I   │                                                  │  actual   │
│  Z   │                                                  │           │
│  Q   │                                                  │  [Desli-  │
│  U   │                                                  │   zadores]│
│  I   │                                                  │           │
│  E   │                                                  │  [Aplicar]│
│  R   │                                                  │  [Reset]  │
│  D   │                                                  │  [Undo]   │
│  O   │                                                  │           │
│      ├──────────────────────────────────────────────────┤           │
│ Lista│           HISTOGRAMA (R/G/B/L)                   │           │
│  de  │           ████▓▓▒▒░░                             │           │
│pasos │                                                  │           │
├──────┴──────────────────────────────────────────────────┴───────────┤
│ [▶ Auto] [Paso anterior ←] [→ Paso siguiente]    Progreso: ██░ 60% │
└─────────────────────────────────────────────────────────────────────┘

Panel izquierdo: lista de pasos del pipeline con estado
  ✅ 1. Carga (8 frames)
  ✅ 2. Calibración
  ✅ 3. Scoring (7/8 aceptados)
  ✅ 4. Debayer (RGGB)
  ⏳ 5. Alineación...
  ○  6. Apilamiento
  ○  7. Stretch
  ○  8. Exportar
```

---

## Estado actual (implementado)

### Módulos del motor

| Módulo | Archivo | Estado |
|---|---|---|
| Carga FITS | `io_fits.py` | Hecho |
| Carga RAW (DSLR) | `io_raw.py` | Hecho |
| Carga/guardado TIFF | `io_tiff.py` | Hecho |
| Debayer (CFA a RGB) | `debayer.py` | Hecho |
| Calibracion (bias/dark/flat) | `calibration.py` | Hecho |
| Alineacion (registro estelar) | `alignment.py` | Hecho |
| Apilamiento (stacking) | `stacking.py` | Hecho |
| Scoring de frames | `frame_scoring.py` | Hecho |
| Stretch inteligente | `stretch.py` | Hecho |
| Pipeline auto/experto | `pipeline.py` | Hecho |
| Extraccion de fondo (ABE/DBE) | `background.py` | Hecho |
| Reduccion de ruido | `denoise.py` | Hecho |
| Nitidez (USM + deconvolution) | `sharpen.py` | Hecho |
| Color / balance blancos | `color.py` | Hecho |
| Curvas y niveles | `curves.py` | Hecho |
| Crop / Rotacion / Flip / Binning | `transform.py` | Hecho |
| Exportacion PNG / JPEG | `export.py` | Hecho |
| Mascaras (luminancia/rango/estrellas) | `masks.py` | Hecho |
| Eliminacion estrellas + halos | `masks.py` | Hecho |
| Catalogo astronomico (Messier/Caldwell/Sharpless) | `catalog.py` | Hecho |
| Plate Solving + anotacion | `platesolve.py` | Hecho |
| Narrowband (SHO/HOO/paletas/continuum sub) | `narrowband.py` | Hecho |
| Mosaico + HDR multiscale | `mosaic.py` | Hecho |
| PixelMath (calculadora de imagenes) | `pixelmath.py` | Hecho |
| Anotacion visual (objetos/brujula/escala) | `annotate.py` | Hecho |
| AI Denoise (wavelet/BM3D/multiscale/neural) | `ai_denoise.py` | Hecho |
| AI Upscale + mejora de detalle | `ai_enhance.py` | Hecho |
| AI Clasificacion de objetos | `ai_classify.py` | Hecho |
| AI Auto-parametros predictivos | `ai_autoparams.py` | Hecho |
| Drizzle (super-resolucion) | `drizzle.py` | Hecho |
| Metadatos de sesion (timeline) | `metadata.py` | Hecho |
| SCNR (eliminar verde) + LRGB Combine | `scnr.py` | Hecho |
| Star Reduction + Diffraction Spikes | `star_effects.py` | Hecho |
| CLAHE + Contraste local | `local_enhance.py` | Hecho |
| Clone/Heal (satelites, hot pixels, columnas) | `heal.py` | Hecho |
| Watermark + redes sociales + timelapse/GIF | `publish.py` | Hecho |
| Registro de acciones (102 acciones) | `actions.py` | Hecho |
| Sesion paso a paso + undo | `session.py` | Hecho |
| Sistema de progreso | `progress.py` | Hecho |
| Toolbars personalizables + macros | `toolbar.py` | Hecho |
| Asistente inteligente (diagnostico+sugerencias) | `assistant.py` | Hecho |
| Planificador de sesion + perfiles equipo | `planner.py` | Hecho |
| Procesamiento por lotes (batch) | `batch.py` | Hecho |
| GUI (PyQt6) tema oscuro/claro, menus auto | `gui/` | Hecho |

### Componentes GUI (carpeta `gui/`)

| Componente | Archivo | Descripcion |
|---|---|---|
| Ventana principal | `main_window.py` | Layout completo, menus auto-generados desde 102 acciones, 4 toolbars cromaticas (gris/azul/verde/amarillo) con botones que se iluminan al seleccionar (checked con color de grupo), toggle AUTO/EXPERTO con diferencia real, drag & drop de archivos, atajos Ctrl+O/S/Z/F5. Indicador de progreso al ejecutar acciones: cursor de espera, barra indeterminada, status bar con nombre de accion y tiempo transcurrido |
| Wizard (modo guiado) | `wizard_panel.py` | 9 pasos en orden (Cargar, Analizar, Stretch, ABE, Denoise, Color, Sharpen, Saturacion, Guardar). Cards clickables para navegar a cualquier paso libremente. Cada paso muestra los sliders/parametros en el panel derecho automaticamente con preview activado. Botones: Aplicar, Deshacer paso (rojo), Repetir, Anterior, Saltar. Tips contextuales amarillos. Barra de progreso. Reemplaza el panel de pipeline en modo AUTO |
| Visor de imagen | `image_viewer.py` | Zoom con rueda del raton (0.05x-16x), pan con boton central, canales RGB/R/G/B/L con botones coloreados, crosshair con coordenadas pixel, drag & drop de archivos al canvas, boton Fit |
| Panel de parametros | `params_panel.py` | Sliders sincronizados con spinbox para float/int, combos para choices, checkbox para bool. Preview en tiempo real: al soltar slider o editar spinbox, aplica temporalmente sin guardar en historial (con cursor de espera y tiempo). Aplicar confirma, Reset cancela preview y restaura imagen original. En wizard el preview se activa automaticamente |
| Panel de pipeline | `steps_panel.py` | Historial de pasos aplicados con estado OK, tooltip con parametros y tiempo, boton Deshacer. Visible solo en modo EXPERTO |
| Histograma | `histogram_widget.py` | RGB + Luminancia pintado en tiempo real con QPainter, colores por canal (R rojo, G verde, B azul, L blanco) |
| Process Icons | `process_icons.py` | 11 iconos predefinidos (STF, ABE, Denoise, Sharp, WB, Sat+, SCNR, Stars-, Spikes, CLAHE, AI Dn), click derecho para editar/renombrar/eliminar, boton + para anadir cualquiera de las 102 acciones |
| Panel asistente | `assistant_panel.py` | Tab junto a Parametros. Boton Analizar imagen, tarjetas de diagnostico coloreadas por severidad (rojo critico, naranja warning, azul info, verde ok), boton Aplicar en cada tarjeta, boton Aplicar plan completo |
| Planificador | `planner_dialog.py` | Dialogo con inputs lat/lon/Bortle, boton Detectar ubicacion (geolocalizacion por IP automatica), tabla con 30 targets ordenados por score (nombre, altitud max, horas visibles, circumpolar), calculo automatico al abrir |
| Perfil de equipo | `equipment_dialog.py` | Inputs telescopio (focal, apertura) + camara (pixel size, resolucion) + Bortle. Calculos en tiempo real: pixel scale, FOV, focal ratio, evaluacion de muestreo, exposicion sugerida segun Bortle |
| About | `about_dialog.py` | Dialogo con branding ASTRO BELLADEV, version, features, tecnologias usadas, enlace belladev.es |
| Splash screen | `splash.py` | Pantalla de bienvenida con gradiente azul oscuro, titulo ASTRO BELLADEV, features del programa, barra de carga, version. Se muestra 1.8s al arrancar |
| Temas | `theme.py` | 2 temas (BellaDev Dark / BellaDev Light) con paleta completa: 25 variables de color cada uno. 450+ lineas CSS cubriendo todos los widgets (menus, toolbars, botones, inputs, sliders, scrollbars, tabs, tooltips, listas, progress bar, splitter). Colores extraidos del logo BellaDev: azul metalico #4A7FB5, gris acero #8899AA, blanco perla #E8ECF0 |
| Iconos SVG | `icons.py` | 30 iconos vectoriales inline (sin archivos externos): open, save, export, undo, auto, calibrate, score, debayer, align, stack, stretch, background, denoise, sharpen, color, levels, stars, starless, spikes, ai, crop, rotate, heal, mosaic, catalog, histogram, macro, assistant, planner, settings, theme, narrowband. Cache de QIcon para rendimiento |
| Traducciones | `i18n.py` | 2 idiomas (Espanol/Ingles) con 80+ cadenas traducidas. Cambio en vivo desde menu Vista > Idioma: reconstruye menus, toolbars y textos sin reiniciar. Funcion tr() para cualquier string visible |
| Consola/Log | `log_panel.py` | Panel de consola integrado (tab junto a Histograma). Captura todos los prints del motor y los muestra con colores: azul pasos, verde OK, amarillo avisos, rojo errores. Boton Limpiar. Redirige stdout/stderr automaticamente |
| Scripts | `scripts_dialog.py` | Dialogo estilo Siril: tabla con categoria/nombre/descripcion, busqueda, ejecutar, editar con editor de texto, crear nuevo, importar .abs, abrir carpeta. Doble-click para ejecutar |

### Sistema de Scripts (.abs)

Modulo: `scripts.py` — Motor de scripts con formato propio .abs

| Script predefinido | Categoria | Descripcion |
|---|---|---|
| OSC Preprocessing | Pre-procesamiento | Pipeline completo para camaras a color (OSC/DSLR): stretch + ABE + SCNR + denoise + WB + color + sharpen |
| Mono Preprocessing | Pre-procesamiento | Pipeline para camaras monocromaticas: stretch + ABE + denoise + deconvolution |
| Seestar S30 Pro | Telescopios inteligentes | Solo lights sin calibracion: stretch + ABE + SCNR + denoise + WB + color + sharpen + CLAHE |
| Nebulosa Ha | Narrowband | Optimizado para Ha: stretch agresivo + ABE + denoise + sharpen + CLAHE |
| Galaxia con Nucleo | Objetos | Stretch suave para nucleos: preserva detalle + ABE + denoise + WB + color + deconvolution |
| Campo Estelar Colores | Objetos | Potencia colores estelares: asinh stretch + WB + saturacion alta + reducir halos |
| Quick Process | Rapido | 3 pasos: stretch + denoise + WB |

Los scripts se guardan en `~/.astro_belladev/scripts/` y en la carpeta del programa.
Menu Scripts en la barra de menus con todos los scripts disponibles como accesos directos.

### Formatos soportados

- **Entrada**: FITS (.fits/.fit/.fts), RAW (.cr2/.cr3/.nef/.arw/.dng/
  .orf/.rw2/.raf/.pef/.srw), TIFF (.tif/.tiff) 16/32 bits.
- **Salida**: FITS, TIFF, PNG (8/16 bits), JPEG (calidad configurable).

## Instalación

```bash
pip install -r requirements.txt
```

## Cómo probarlo ahora mismo

```bash
python examples/generate_test_data.py   # genera frames FITS sintéticos
python examples/run_stack.py            # pipeline completo auto
python examples/test_debayer.py         # test de debayer + TIFF
python examples/test_scoring_stretch.py # test de scoring + stretch
python examples/test_processing.py     # test de todos los módulos de procesamiento
```

## Uso desde código

```python
from astro_belladev.pipeline import run_pipeline

# === MODO AUTO — cero configuración ===
run_pipeline(
    bias_dir="mis_datos/bias",
    dark_dir="mis_datos/dark",
    flat_dir="mis_datos/flat",
    lights_dir="mis_datos/lights",
    output_path="resultado.fits",
    mode="auto",
)

# === MODO EXPERTO — control total ===
run_pipeline(
    lights_dir="mis_datos/lights",
    output_path="resultado.tiff",
    mode="expert",
    stack_method="sigma_clip",
    reject_percent=30,
    min_stars=10,
    debayer_pattern="RGGB",
    stretch_method="midtone",
    target_type="nebula",
    stretch_params={"midtone": 0.20, "black_clip": -2.5},
)
```

## Toolbars personalizables (estilo PixInsight)

Como los "Process Icons" de PixInsight, el usuario puede crear
botones personalizados con acciones preconfiguradas:

```
  Toolbar "Principal"
  [Abrir] [Guardar] [Deshacer] [Auto]

  Toolbar "Procesamiento"
  [Stretch] [ABE] [Denoise] [Sharpen] [WB] [Color+] [Niveles] [Starless]

  Toolbar "Macros" (secuencias de acciones)
  [Nebulosa Completo]  -> stretch + ABE + denoise + WB + color + sharpen
  [Galaxia Completo]   -> stretch + ABE + denoise + WB + color + deconv
  [Campo Estelar]      -> stretch + WB + saturacion + reducir halos
```

Cada boton puede ser:
- **Simple**: una accion con parametros fijos (ej: "Stretch midtone=0.18")
- **Macro**: secuencia de acciones que se ejecutan en orden
- **Preset**: configuracion guardada que se puede reutilizar

Los botones son arrastrables, reordenables, y la configuracion
se guarda en JSON para persistir entre sesiones.

```python
from astro_belladev.toolbar import ToolbarManager

manager = ToolbarManager()
manager.create_default_toolbars()  # 4 toolbars, 20 botones, 6 presets

# Crear boton personalizado
from astro_belladev.toolbar import ToolButton, MacroStep
manager.get_toolbar("processing").add_button(ToolButton(
    id="mi_boton", label="Mi Proceso",
    action_id="stretch_midtone",
    params={"midtone": 0.18},
    color="#FF6B6B",
))

# Guardar un preset para reutilizar
manager.save_preset("Mi Stretch M42", "stretch_midtone",
                     {"midtone": 0.15, "black_clip": -3.0})

# Guardar/cargar configuracion
manager.save_config("mis_toolbars.json")
manager.load_config("mis_toolbars.json")
```

## Uso avanzado: sesion paso a paso

```python
from astro_belladev.actions import build_default_registry
from astro_belladev.session import Session

registry = build_default_registry()
session = Session()

# Cargar imagen
import numpy as np
from astro_belladev.io_fits import load_fits
data, header = load_fits("mi_imagen_apilada.fits")
session.load_image(data)

# Aplicar operaciones una a una (como en la GUI)
session.apply(registry.get("stretch_midtone"), midtone=0.20)
session.apply(registry.get("background_abe"), grid_size=10)
session.apply(registry.get("denoise_selective"), lum_strength=0.6)
session.apply(registry.get("saturation"), factor=1.3)

# Deshacer el ultimo paso
session.undo()

# Ver historial
session.print_history()

# Ver todas las acciones disponibles
registry.list_actions()
```

## Roadmap

1. ~~**Debayer + soporte RAW/TIFF**~~ — Hecho.
2. ~~**Scoring de frames + Stretch inteligente**~~ — Hecho.
3. ~~**Infraestructura GUI + Procesamiento + Acciones**~~ — Hecho:
   - **39 acciones** registradas con parametros, rangos, defaults y
     rutas de menu (genera menus automaticamente).
   - Sistema de callbacks/eventos para progreso (barras, logs).
   - Sesion paso a paso con undo (hasta 10 pasos), historial JSON.
   - Extraccion de fondo ABE/DBE, denoise (bilateral/NLM/selectivo),
     nitidez (USM/deconvolution), color (WB auto/estrellas/manual),
     saturacion (global/selectiva), curvas, niveles, histograma.
   - Crop, rotacion, flip, binning, redimensionar.
   - Mascaras (luminancia, rango, estrellas), eliminacion de
     estrellas (inpainting), reduccion de halos.
   - Exportacion PNG (8/16 bits) y JPEG (calidad configurable).
4. ~~**Funciones avanzadas**~~ — Hecho:
   - Catalogo astronomico integrado: 158 objetos (Messier completo,
     Caldwell, Sharpless), busqueda, filtrado, persistencia JSON.
   - Plate solving con WCS (pixel <-> RA/Dec), anotacion automatica.
   - Narrowband: paletas SHO/HOO/HOS/natural/custom, continuum
     subtraction, blend narrowband+RGB.
   - Mosaico: deteccion de solapamiento (ORB), stitching con
     homografia, union multipanel.
   - HDR multiscale: combinar exposiciones cortas y largas.
   - Analisis de sesion: metricas de calidad a lo largo de la noche.
5. **Interfaz grafica** (PyQt6) — proximo:
   - Layout con panel de pasos, preview central, histograma,
     panel de parametros (ver mockup arriba).
   - Toggle auto/experto.
   - Drag & drop de carpetas.
   - Generacion automatica de controles desde las 102 acciones.
