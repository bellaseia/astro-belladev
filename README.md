# Astro BellaDev

**Astrophotography Processing Suite** — Free, open-source alternative to PixInsight, Siril and SASpro.

Built by [BellaDev](https://belladev.es) | MIT License | Python + PyQt6

---

## What is Astro BellaDev?

A complete astrophotography processing application designed to be **powerful yet simple**. Two modes for two kinds of users:

- **Auto Mode**: guided wizard, 9 steps from raw to final image. Zero configuration.
- **Expert Mode**: full control over 102 processing actions with real-time preview.

## Key Features

- **Full Pipeline**: calibration (bias/dark/flat), debayer, alignment, stacking (memory-optimized for 200+ frames)
- **Intelligent Stretch**: Midtone (STF), Arcsinh, Auto-detect by target type (nebula/galaxy/starfield/planetary)
- **AI Processing**: wavelet denoise, BM3D, multiscale, auto-parameters prediction, object classification
- **Color Tools**: SCNR green removal, white balance (auto/stars/manual), saturation (global/selective), photometric calibration
- **Star Tools**: diffraction spikes, star removal (starless), halo reduction, star masks
- **Background**: ABE/DBE automatic background extraction
- **Narrowband**: SHO/HOO/HOS palettes, continuum subtraction, RGB blend
- **PixelMath**: free-form image calculator (like PixInsight)
- **158 Object Catalog**: Messier, Caldwell, Sharpless with Aladin Sky Atlas previews
- **Session Planner**: visible targets tonight based on your location, equipment profiles
- **10 Built-in Scripts**: OSC, Mono, Seestar S30 Pro, SCNR, and more
- **Smart Assistant**: diagnoses your image and suggests the exact action with optimal parameters
- **Export**: FITS, TIFF, PNG, JPEG, Instagram/Facebook templates, watermark, timelapse GIF

## Installation

### From source (recommended for development)

```bash
git clone https://github.com/bellaseia/astro-belladev.git
cd astro-belladev
pip install -r requirements.txt
python app.py
```

### Windows executable

Download `AstroBellaDev.exe` from [Releases](https://github.com/bellaseia/astro-belladev/releases) — no Python needed.

## Quick Start

1. Launch the app (`python app.py` or `AstroBellaDev.exe`)
2. The **Guided Wizard** walks you through 9 steps
3. Open your stacked FITS/TIFF image
4. Follow the wizard: Stretch → ABE → Denoise → Color → Sharpen → Save
5. Switch to **Expert Mode** for full control

## Screenshots

*Coming soon — the app features a professional dark/light theme with BellaDev branding.*

## Requirements

- Python 3.10+
- PyQt6
- NumPy, SciPy, OpenCV, AstroPy
- astroalign, rawpy, tifffile

## Project Stats

| | |
|---|---|
| Python modules | 62 |
| Processing actions | 102 |
| GUI components | 19 |
| Built-in scripts | 10 |
| Catalog objects | 158 |
| SVG icons | 30 |
| Languages | ES / EN |
| Lines of code | 20,000+ |

## Architecture

See [DEVELOPMENT.md](DEVELOPMENT.md) for full technical documentation including module descriptions, menu structure, pipeline diagrams, and roadmap.

## Contributing

1. Fork the repo
2. Create a branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push and create a Pull Request

Scripts are welcome! Write a `.py` or `.abs` script and share it with the community.

## License

MIT License — Copyright (c) 2026 [BellaDev](https://belladev.es)

See [LICENSE](LICENSE) for details.
