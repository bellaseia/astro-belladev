"""
preprocess_dialog.py
--------------------
Pipeline de pre-procesamiento estilo Siril:
todo en disco, streaming, sin acumular RAM.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFormLayout, QLineEdit,
    QFileDialog, QComboBox, QCheckBox, QProgressBar,
    QTextEdit, QMessageBox, QSpinBox,
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QFont

from pathlib import Path
import numpy as np
import gc


class PipelineWorker(QThread):
    """Pipeline estilo Siril: streaming en disco."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            self._run_pipeline()
        except Exception as e:
            self.error.emit(str(e))

    def _run_pipeline(self):
        from ..io_fits import load_image, ALL_EXTENSIONS, FITS_EXTENSIONS
        from .. import calibration
        from ..alignment import align_frame
        from ..debayer import detect_pattern
        import tempfile

        cfg = self.config

        # === Encontrar archivos ===
        lights_dir = Path(cfg["lights_dir"])
        light_paths = self._find_images(lights_dir)

        if not light_paths:
            raise RuntimeError(
                f"No se encontraron imagenes en {lights_dir}"
            )

        self.progress.emit(
            f"[1/4] {len(light_paths)} light frames encontrados"
        )

        # === Masters (bias/dark/flat) ===
        master_bias, master_dark, master_flat = (
            self._create_masters(cfg, calibration)
        )

        # === Temp dir ===
        temp_dir = Path(tempfile.mkdtemp(prefix="abd_"))
        self.progress.emit(f"  Temp: {temp_dir}")

        # === Paso principal: calibrar + debayer + alinear ===
        # Frame a frame, directo a disco
        self.progress.emit(
            "[2/4] Calibrando + alineando frame a frame..."
        )

        # Detectar bayer
        bayer_pattern = None
        if cfg.get("do_debayer", True):
            first = light_paths[0]
            if first.suffix.lower() in FITS_EXTENSIONS:
                from ..io_fits import load_fits
                _, hdr = load_fits(str(first))
                bayer_pattern = detect_pattern(hdr)
                if bayer_pattern:
                    self.progress.emit(
                        f"  Bayer: {bayer_pattern}"
                    )

        # Procesar referencia
        ref = self._process_single_frame(
            light_paths[0], calibration,
            master_bias, master_dark, master_flat,
            bayer_pattern,
        )
        ref_path = temp_dir / "frame_0000.npy"
        np.save(str(ref_path), ref)
        aligned_files = [ref_path]
        self.progress.emit(
            f"  #0: referencia "
            f"{ref.shape[1]}x{ref.shape[0]} "
            f"{'RGB' if ref.ndim == 3 else 'Mono'}"
        )

        # Procesar resto uno a uno
        ok_count = 0
        fail_count = 0
        n = len(light_paths)

        for i in range(1, n):
            try:
                frame = self._process_single_frame(
                    light_paths[i], calibration,
                    master_bias, master_dark, master_flat,
                    bayer_pattern,
                )

                # Alinear contra referencia
                aligned = align_frame(frame, ref)
                del frame
                gc.collect()

                if aligned is not None:
                    out = temp_dir / f"frame_{i:04d}.npy"
                    np.save(str(out), aligned)
                    aligned_files.append(out)
                    del aligned
                    ok_count += 1
                else:
                    fail_count += 1

            except Exception:
                fail_count += 1

            gc.collect()

            if i % 10 == 0 or i == n - 1:
                self.progress.emit(
                    f"  {i}/{n-1}: "
                    f"OK={ok_count} fail={fail_count}"
                )

        # Liberar masters y referencia
        del ref, master_bias, master_dark, master_flat
        gc.collect()

        self.progress.emit(
            f"  Total: {len(aligned_files)} frames alineados"
        )

        # === Apilar desde disco por lineas ===
        method = cfg.get("stack_method", "sigma_clip")
        self.progress.emit(
            f"[3/4] Apilando ({method})..."
        )
        result = self._stack_from_disk(aligned_files, method)
        self.progress.emit(
            f"  Resultado: {result.shape[1]}x{result.shape[0]}"
        )

        # === Guardar ===
        output = cfg.get("output_path", "stacked_result.fits")
        if output:
            self.progress.emit(f"[4/4] Guardando: {output}")
            out_path = Path(output)
            if out_path.suffix.lower() in (".tif", ".tiff"):
                from ..io_tiff import save_tiff
                save_tiff(str(out_path), result)
            else:
                from ..io_fits import save_fits
                save_fits(str(out_path), result)

        # Limpiar temporales
        import shutil
        shutil.rmtree(str(temp_dir), ignore_errors=True)

        self.progress.emit("[OK] Pipeline completado!")
        self.finished.emit(result)

    def _find_images(self, folder):
        """Busca imagenes en carpeta o subcarpeta lights."""
        from ..io_fits import ALL_EXTENSIONS

        paths = sorted([
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in ALL_EXTENSIONS
        ])
        if paths:
            return paths

        for name in ["lights", "Lights", "light", "Light"]:
            sub = folder / name
            if sub.exists():
                paths = sorted([
                    p for p in sub.iterdir()
                    if p.is_file()
                    and p.suffix.lower() in ALL_EXTENSIONS
                ])
                if paths:
                    return paths

        for sub in folder.iterdir():
            if sub.is_dir():
                paths = sorted([
                    p for p in sub.iterdir()
                    if p.is_file()
                    and p.suffix.lower() in ALL_EXTENSIONS
                ])
                if paths:
                    return paths

        return []

    def _create_masters(self, cfg, calibration):
        """Crea master bias/dark/flat."""
        from ..io_fits import load_folder

        master_bias = None
        master_dark = None
        master_flat = None

        if cfg.get("bias_dir"):
            self.progress.emit("  Creando master bias...")
            frames, _ = load_folder(cfg["bias_dir"],
                                     auto_debayer=False)
            master_bias = calibration.create_master_bias(frames)
            del frames; gc.collect()
            self.progress.emit(f"    OK")

        if cfg.get("dark_dir"):
            self.progress.emit("  Creando master dark...")
            frames, _ = load_folder(cfg["dark_dir"],
                                     auto_debayer=False)
            master_dark = calibration.create_master_dark(
                frames, master_bias
            )
            del frames; gc.collect()
            self.progress.emit(f"    OK")

        if cfg.get("flat_dir"):
            self.progress.emit("  Creando master flat...")
            frames, _ = load_folder(cfg["flat_dir"],
                                     auto_debayer=False)
            master_flat = calibration.create_master_flat(
                frames, master_bias
            )
            del frames; gc.collect()
            self.progress.emit(f"    OK")

        return master_bias, master_dark, master_flat

    def _process_single_frame(self, path, calibration,
                                master_bias, master_dark,
                                master_flat, bayer_pattern):
        """Carga, calibra y debayerea un solo frame."""
        from ..io_fits import load_image

        data, _ = load_image(str(path), auto_debayer=False)
        cal = calibration.calibrate_light(
            data, master_bias, master_dark, master_flat
        )
        del data

        if bayer_pattern and cal.ndim == 2:
            from ..debayer import debayer
            cal = debayer(cal, bayer_pattern)

        return cal

    def _stack_from_disk(self, file_paths, method):
        """Apila por lineas leyendo desde disco (mmap)."""
        CHUNK = 64  # lineas por chunk

        sample = np.load(str(file_paths[0]), mmap_mode='r')
        h, w = sample.shape[:2]
        has_color = sample.ndim == 3
        n_ch = sample.shape[-1] if has_color else 1
        n_files = len(file_paths)
        del sample

        if has_color:
            result = np.zeros((h, w, n_ch), dtype=np.float32)
        else:
            result = np.zeros((h, w), dtype=np.float32)

        total_chunks = (h + CHUNK - 1) // CHUNK

        for chunk_idx, y0 in enumerate(range(0, h, CHUNK)):
            y1 = min(y0 + CHUNK, h)
            chunk_h = y1 - y0

            if has_color:
                stack = np.zeros(
                    (n_files, chunk_h, w, n_ch),
                    dtype=np.float32,
                )
            else:
                stack = np.zeros(
                    (n_files, chunk_h, w),
                    dtype=np.float32,
                )

            for fi, fp in enumerate(file_paths):
                mmap = np.load(str(fp), mmap_mode='r')
                if has_color:
                    stack[fi] = mmap[y0:y1, :, :]
                else:
                    stack[fi] = mmap[y0:y1, :]
                del mmap

            if method == "average":
                chunk_result = np.mean(stack, axis=0)
            elif method == "median":
                chunk_result = np.median(stack, axis=0)
            else:
                for _ in range(3):
                    med = np.median(stack, axis=0, keepdims=True)
                    std = np.std(stack, axis=0, keepdims=True)
                    std = np.where(std == 0, 1, std)
                    bad = np.abs(stack - med) > 3.0 * std
                    stack = np.where(bad, np.nan, stack)
                with np.errstate(all='ignore'):
                    chunk_result = np.nanmean(stack, axis=0)
                chunk_result = np.nan_to_num(
                    chunk_result, nan=0.0
                )

            if has_color:
                result[y0:y1, :, :] = chunk_result
            else:
                result[y0:y1, :] = chunk_result

            del stack, chunk_result
            gc.collect()

            if (chunk_idx + 1) % 5 == 0:
                pct = int((chunk_idx + 1) / total_chunks * 100)
                self.progress.emit(f"  Apilando: {pct}%")

        return result.astype(np.float32)


class PreprocessDialog(QDialog):
    """Dialogo de pre-procesamiento."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pre-procesamiento")
        self.setMinimumSize(700, 600)
        self.result_data = None

        input_style = """
            QLineEdit {
                background-color: #1A1E30;
                color: #E0E4EC;
                border: 1px solid #2A2F45;
                border-radius: 4px;
                padding: 6px; font-size: 13px;
            }
        """

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Carpetas
        fg = QGroupBox("Carpetas de datos")
        fl = QFormLayout(fg)

        self.lights_edit = QLineEdit()
        self.lights_edit.setStyleSheet(input_style)
        self.lights_edit.setPlaceholderText("Obligatorio")
        b = QPushButton("..."); b.setFixedWidth(40)
        b.clicked.connect(lambda: self._browse("lights_edit"))
        r = QHBoxLayout(); r.addWidget(self.lights_edit); r.addWidget(b)
        fl.addRow("Lights:", r)

        self.darks_edit = QLineEdit()
        self.darks_edit.setStyleSheet(input_style)
        self.darks_edit.setPlaceholderText("Opcional")
        b = QPushButton("..."); b.setFixedWidth(40)
        b.clicked.connect(lambda: self._browse("darks_edit"))
        r = QHBoxLayout(); r.addWidget(self.darks_edit); r.addWidget(b)
        fl.addRow("Darks:", r)

        self.flats_edit = QLineEdit()
        self.flats_edit.setStyleSheet(input_style)
        self.flats_edit.setPlaceholderText("Opcional")
        b = QPushButton("..."); b.setFixedWidth(40)
        b.clicked.connect(lambda: self._browse("flats_edit"))
        r = QHBoxLayout(); r.addWidget(self.flats_edit); r.addWidget(b)
        fl.addRow("Flats:", r)

        self.bias_edit = QLineEdit()
        self.bias_edit.setStyleSheet(input_style)
        self.bias_edit.setPlaceholderText("Opcional")
        b = QPushButton("..."); b.setFixedWidth(40)
        b.clicked.connect(lambda: self._browse("bias_edit"))
        r = QHBoxLayout(); r.addWidget(self.bias_edit); r.addWidget(b)
        fl.addRow("Bias:", r)

        layout.addWidget(fg)

        # Opciones
        og = QGroupBox("Opciones")
        ol = QFormLayout(og)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["sigma_clip", "average", "median"])
        ol.addRow("Apilamiento:", self.method_combo)

        self.debayer_check = QCheckBox("Debayer automatico")
        self.debayer_check.setChecked(True)
        ol.addRow("Debayer:", self.debayer_check)

        self.output_edit = QLineEdit()
        self.output_edit.setStyleSheet(input_style)
        self.output_edit.setText("stacked_result.fits")
        b = QPushButton("..."); b.setFixedWidth(40)
        b.clicked.connect(self._browse_output)
        r = QHBoxLayout(); r.addWidget(self.output_edit); r.addWidget(b)
        ol.addRow("Guardar:", r)

        layout.addWidget(og)

        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 11))
        self.log.setStyleSheet("""
            QTextEdit {
                background-color: #0A0C14;
                color: #A0B0C0;
                border: 1px solid #2A2F45;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.log, stretch=1)

        # Progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        # Botones
        bl = QHBoxLayout()
        bl.addStretch()
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        bl.addWidget(self.cancel_btn)
        self.run_btn = QPushButton("Ejecutar Pipeline")
        self.run_btn.setObjectName("primary")
        self.run_btn.setMinimumWidth(160)
        self.run_btn.clicked.connect(self._run)
        bl.addWidget(self.run_btn)
        layout.addLayout(bl)

    def _browse(self, field):
        d = QFileDialog.getExistingDirectory(self, "Carpeta")
        if d:
            getattr(self, field).setText(d)

    def _browse_output(self):
        p, _ = QFileDialog.getSaveFileName(
            self, "Guardar", "stacked_result.fits",
            "FITS (*.fits);;TIFF (*.tiff)",
        )
        if p:
            self.output_edit.setText(p)

    def _log(self, text):
        self.log.append(text)
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        print(text)

    def _run(self):
        if not self.lights_edit.text().strip():
            QMessageBox.warning(self, "Falta",
                                "Selecciona carpeta de lights")
            return

        config = {
            "lights_dir": self.lights_edit.text().strip(),
            "dark_dir": self.darks_edit.text().strip() or None,
            "flat_dir": self.flats_edit.text().strip() or None,
            "bias_dir": self.bias_edit.text().strip() or None,
            "stack_method": self.method_combo.currentText(),
            "do_debayer": self.debayer_check.isChecked(),
            "output_path": self.output_edit.text().strip(),
        }

        self.run_btn.setEnabled(False)
        self.progress_bar.setMaximum(0)
        self.log.clear()
        self._log("=== PIPELINE ===")

        self.worker = PipelineWorker(config)
        self.worker.progress.connect(self._log)
        self.worker.finished.connect(self._done)
        self.worker.error.connect(self._fail)
        self.worker.start()

    def _done(self, result):
        self.result_data = result
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
        self.run_btn.setEnabled(True)
        self._log("=== COMPLETADO ===")

        reply = QMessageBox.question(
            self, "Completado",
            "Cargar resultado en el visor?",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.accept()

    def _fail(self, msg):
        self.progress_bar.setMaximum(100)
        self.run_btn.setEnabled(True)
        self._log(f"[ERROR] {msg}")
        QMessageBox.critical(self, "Error", msg)

    def get_result(self):
        return self.result_data
