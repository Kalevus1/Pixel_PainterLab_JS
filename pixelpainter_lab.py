import sys
import numpy as np
from PIL import Image

from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QFont
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QSlider, QFileDialog, QScrollArea,
    QHBoxLayout, QVBoxLayout, QFrame, QCheckBox, QSizePolicy, QMessageBox,
)

# ------------------------------------------------------------------ motor
def kmeans(X, k, max_iter=30, seed=None):
    rng = np.random.default_rng(seed)
    n = len(X)
    if n == 0 or k <= 0:
        return np.zeros(0, dtype=int), np.zeros((0, 3))
    k = min(k, n)
    centers = [X[rng.integers(n)]]
    for _ in range(1, k):
        d2 = np.min(np.stack([np.sum((X - c) ** 2, axis=1) for c in centers]), axis=0)
        s = d2.sum()
        probs = d2 / s if s > 0 else np.full(n, 1.0 / n)
        centers.append(X[rng.choice(n, p=probs)])
    C = np.array(centers, dtype=float)
    labels = np.full(n, -1, dtype=int)
    for _ in range(max_iter):
        dists = ((X[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
        new = np.argmin(dists, axis=1)
        for c in range(k):
            m = new == c
            if m.any():
                C[c] = X[m].mean(axis=0)
        if np.array_equal(new, labels):
            labels = new
            break
        labels = new
    return labels, C


def recipe(r, g, b):
    """Mezcla aproximada {w,c,m,y,k} en % (pasos de 5, suma 100)."""
    R, G, B = r / 255, g / 255, b / 255
    k = 1 - max(R, G, B)
    denom = (1 - k) or 1
    c = (1 - R - k) / denom
    m = (1 - G - k) / denom
    y = (1 - B - k) / denom
    w = min(R, G, B)
    raw = {"w": w, "c": c * (1 - w), "m": m * (1 - w), "y": y * (1 - w), "k": k}
    s = sum(raw.values()) or 1
    arr = [[key, round(raw[key] / s * 100 / 5) * 5] for key in raw]
    total = sum(v for _, v in arr)
    arr.sort(key=lambda p: -p[1])
    i = guard = 0
    while total != 100 and guard < 60:
        p = arr[i % len(arr)]
        if total < 100:
            p[1] += 5; total += 5
        elif p[1] >= 5:
            p[1] -= 5; total -= 5
        i += 1; guard += 1
    return {key: v for key, v in arr}


MIX_INFO = {"w": ("Blanco", "#f1f5f9"), "c": ("Cian", "#06b6d4"),
            "m": ("Magenta", "#d946ef"), "y": ("Amarillo", "#facc15"), "k": ("Negro", "#0f172a")}


def hexc(r, g, b):
    return f"#{int(r):02X}{int(g):02X}{int(b):02X}"


# ------------------------------------------------------------------ lienzo
class Canvas(QWidget):
    seleccion = Signal(int)

    def __init__(self):
        super().__init__()
        self.cols = 0
        self.rows = 0
        self.cell_labels = None       # np array (rows*cols,)
        self.palette = []             # [{r,g,b,hex,count,recipe}]
        self.show_grid = True
        self.show_num = True
        self.highlight = True
        self.selected = None
        self.disp_w = 540
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_data(self, cols, rows, labels, palette):
        self.cols, self.rows = cols, rows
        self.cell_labels = labels
        self.palette = palette
        self._resize()
        self.update()

    def _resize(self):
        if not self.cols:
            return
        cw = self.disp_w / self.cols
        self.setFixedSize(int(self.disp_w), int(cw * self.rows))

    def _cw(self):
        return self.disp_w / self.cols if self.cols else 1

    def paintEvent(self, _):
        if not self.cols or self.cell_labels is None:
            return
        cw = self._cw()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        # celdas via QImage a resolución de rejilla, escalado nearest
        img = QImage(self.cols, self.rows, QImage.Format.Format_RGB32)
        for y in range(self.rows):
            for x in range(self.cols):
                col = self.palette[self.cell_labels[y * self.cols + x]]
                img.setPixelColor(x, y, QColor(col["r"], col["g"], col["b"]))
        p.drawImage(QRect(0, 0, int(cw * self.cols), int(cw * self.rows)), img)

        W, H = cw * self.cols, cw * self.rows
        # resaltar
        if self.highlight and self.selected is not None:
            col = self.palette[self.selected]
            dark = (col["r"] + col["g"] + col["b"]) / 3 < 128
            p.setPen(QPen(QColor("#22ff88") if dark else QColor("#ff2fd6"), 2))
            fill = QColor(255, 255, 255, 64) if dark else QColor(0, 0, 0, 56)
            for y in range(self.rows):
                for x in range(self.cols):
                    if self.cell_labels[y * self.cols + x] == self.selected:
                        p.fillRect(int(x * cw), int(y * cw), int(cw) + 1, int(cw) + 1, fill)
                        p.drawRect(int(x * cw) + 1, int(y * cw) + 1, int(cw) - 2, int(cw) - 2)
        # cuadrícula
        if self.show_grid:
            p.setPen(QPen(QColor(120, 130, 150, 90), 1))
            for i in range(self.cols + 1):
                p.drawLine(int(i * cw), 0, int(i * cw), int(H))
            for i in range(self.rows + 1):
                p.drawLine(0, int(i * cw), int(W), int(i * cw))
        # números
        if self.show_num and cw >= 9:
            f = QFont("Segoe UI"); f.setPixelSize(max(6, int(cw * 0.5)))
            p.setFont(f)
            for y in range(self.rows):
                for x in range(self.cols):
                    col = self.palette[self.cell_labels[y * self.cols + x]]
                    dark = (col["r"] + col["g"] + col["b"]) / 3 < 128
                    p.setPen(QColor(255, 255, 255, 200) if dark else QColor(0, 0, 0, 175))
                    p.drawText(QRect(int(x * cw), int(y * cw), int(cw), int(cw)),
                               Qt.AlignmentFlag.AlignCenter, str(self.cell_labels[y * self.cols + x] + 1))

    def mousePressEvent(self, e):
        if not self.cols or self.cell_labels is None:
            return
        cw = self._cw()
        x, y = int(e.position().x() / cw), int(e.position().y() / cw)
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self.selected = int(self.cell_labels[y * self.cols + x])
            self.update()
            self.seleccion.emit(self.selected)


# ------------------------------------------------------------------ barra de mezcla
class MixBar(QWidget):
    def __init__(self, nombre, color, pct):
        super().__init__()
        self.nombre, self.color, self.pct = nombre, QColor(color), pct
        self.setFixedHeight(34)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        p.setPen(QColor("#94a3b8")); f = QFont("Segoe UI"); f.setPixelSize(11); p.setFont(f)
        p.drawText(QRect(0, 0, w, 14), Qt.AlignmentFlag.AlignLeft, self.nombre)
        p.drawText(QRect(0, 0, w, 14), Qt.AlignmentFlag.AlignRight, f"{self.pct}%")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#0f172a")); p.drawRoundedRect(0, 18, w, 14, 7, 7)
        p.setBrush(self.color); p.drawRoundedRect(0, 18, int(w * self.pct / 100), 14, 7, 7)


# ------------------------------------------------------------------ ventana
class PixelPainter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PixelPainter Lab")
        self.resize(1120, 780)
        self.setStyleSheet(ESTILO)

        self.img_arr = None       # np array HxWx3 de la imagen original
        self.cols = 40
        self.selected = None

        root = QVBoxLayout(self); root.setContentsMargins(18, 16, 18, 14)
        t = QLabel("PixelPainter <span style='color:#8b5cf6'>Lab</span>"); t.setObjectName("h1")
        root.addWidget(t)
        sub = QLabel("Convierte una imagen en una guía para pintar por números: elige cuántos "
                     "colores y obtén la cuadrícula numerada y la receta de cada pintura.")
        sub.setObjectName("muted"); sub.setWordWrap(True); root.addWidget(sub)

        cols = QHBoxLayout(); cols.setSpacing(16); root.addLayout(cols, 1)

        # ---- panel izquierdo: controles ----
        left = QVBoxLayout(); left.setSpacing(12)
        self.btn_open = QPushButton("⬆  Subir imagen"); self.btn_open.setObjectName("accent")
        self.btn_open.clicked.connect(self._abrir); left.addWidget(self.btn_open)

        self.res_lbl = QLabel("Resolución: 40 px"); self.res_lbl.setObjectName("ctl")
        left.addWidget(self.res_lbl)
        self.res = QSlider(Qt.Orientation.Horizontal); self.res.setMinimum(10); self.res.setMaximum(100)
        self.res.setValue(40); self.res.valueChanged.connect(self._res_changed); left.addWidget(self.res)

        self.col_lbl = QLabel("Nº de colores: 12"); self.col_lbl.setObjectName("ctl")
        left.addWidget(self.col_lbl)
        self.ncolors = QSlider(Qt.Orientation.Horizontal); self.ncolors.setMinimum(2); self.ncolors.setMaximum(24)
        self.ncolors.setValue(12); self.ncolors.valueChanged.connect(self._col_changed); left.addWidget(self.ncolors)

        self.cb_grid = QCheckBox("Cuadrícula"); self.cb_grid.setChecked(True); self.cb_grid.toggled.connect(self._opts)
        self.cb_num = QCheckBox("Números"); self.cb_num.setChecked(True); self.cb_num.toggled.connect(self._opts)
        self.cb_high = QCheckBox("Resaltar iguales"); self.cb_high.setChecked(True); self.cb_high.toggled.connect(self._opts)
        for cb in (self.cb_grid, self.cb_num, self.cb_high):
            left.addWidget(cb)

        self.btn_png = QPushButton("⬇  Descargar guía (PNG)"); self.btn_png.setObjectName("accent")
        self.btn_png.clicked.connect(self._descargar); self.btn_png.setEnabled(False)
        self.btn_print = QPushButton("🖨  Guía imprimible (con leyenda)"); self.btn_print.setObjectName("ghost")
        self.btn_print.clicked.connect(self._imprimible); self.btn_print.setEnabled(False)
        left.addWidget(self.btn_png); left.addWidget(self.btn_print)
        left.addStretch()
        lw = QWidget(); lw.setLayout(left); lw.setFixedWidth(230)
        cols.addWidget(lw)

        # ---- centro: lienzo ----
        self.canvas = Canvas(); self.canvas.seleccion.connect(self._on_select)
        scroll = QScrollArea(); scroll.setWidgetResizable(False); scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(self.canvas); scroll.setObjectName("cscroll")
        self.placeholder = QLabel("🖌️\nSube una imagen para comenzar"); self.placeholder.setObjectName("ph")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas.setVisible(False)
        center = QVBoxLayout(); center.addWidget(self.placeholder, 1); center.addWidget(scroll, 3)
        cw = QWidget(); cw.setLayout(center); cols.addWidget(cw, 1)

        # ---- derecha: paleta + receta ----
        right = QVBoxLayout(); right.setSpacing(12)
        self.pal_title = QLabel("🎨  Paleta"); self.pal_title.setObjectName("h3")
        right.addWidget(self.pal_title)
        self.pal_area = QScrollArea(); self.pal_area.setWidgetResizable(True); self.pal_area.setObjectName("palscroll")
        self.pal_host = QWidget(); self.pal_lay = QVBoxLayout(self.pal_host); self.pal_lay.setSpacing(4); self.pal_lay.addStretch()
        self.pal_area.setWidget(self.pal_host); self.pal_area.setFixedHeight(280)
        right.addWidget(self.pal_area)

        self.rec_host = QFrame(); self.rec_host.setObjectName("card")
        self.rec_lay = QVBoxLayout(self.rec_host)
        self.rec_title = QLabel("🖌️  Receta de mezcla"); self.rec_title.setObjectName("h3")
        self.rec_lay.addWidget(self.rec_title)
        self.rec_swatch = QFrame(); self.rec_swatch.setFixedHeight(48); self.rec_swatch.setStyleSheet("border-radius:8px; border:1px solid #334155;")
        self.rec_lay.addWidget(self.rec_swatch)
        self.rec_info = QLabel("Selecciona un color."); self.rec_info.setObjectName("muted"); self.rec_info.setWordWrap(True)
        self.rec_lay.addWidget(self.rec_info)
        self.rec_bars = QVBoxLayout(); self.rec_lay.addLayout(self.rec_bars)
        self.rec_note = QLabel("Mezcla aproximada (pasos de 5%, suma 100%)."); self.rec_note.setObjectName("muted"); self.rec_note.setWordWrap(True)
        self.rec_lay.addWidget(self.rec_note)
        self.rec_host.setVisible(False)
        right.addWidget(self.rec_host); right.addStretch()
        rw = QWidget(); rw.setLayout(right); rw.setFixedWidth(300)
        cols.addWidget(rw)

        self.status = QLabel("Sube una imagen para empezar.  ·  por KALEVI LATVA AIJO ALEGRIA")
        self.status.setObjectName("status"); root.addWidget(self.status)

        self.palette = []
        self.cell_labels = None
        self.rows = 0

    # ---------------- carga y proceso ----------------
    def _abrir(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Subir imagen", "",
                                              "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
        if not ruta:
            return
        try:
            img = Image.open(ruta).convert("RGB")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir la imagen:\n{e}")
            return
        self.img_arr = np.asarray(img, dtype=float)
        self.selected = None
        self.canvas.setVisible(True); self.placeholder.setVisible(False)
        self.btn_png.setEnabled(True); self.btn_print.setEnabled(True)
        self._procesar()

    def _procesar(self):
        if self.img_arr is None:
            return
        h, w, _ = self.img_arr.shape
        aspect = w / h
        cols = self.res.value()
        rows = max(1, round(cols / aspect))
        # muestrear a la rejilla con PIL (rápido y suave)
        small = Image.fromarray(self.img_arr.astype(np.uint8)).resize((cols, rows), Image.BILINEAR)
        cells = np.asarray(small, dtype=float).reshape(-1, 3)
        k = min(self.ncolors.value(), len(cells))
        labels, C = kmeans(cells, k)
        counts = np.bincount(labels, minlength=len(C))
        orden = [i for i in np.argsort(-counts) if counts[i] > 0]
        remap = {old: nuevo for nuevo, old in enumerate(orden)}
        self.cell_labels = np.array([remap[l] for l in labels])
        self.cols, self.rows = cols, rows
        self.palette = []
        for old in orden:
            r, g, b = [int(round(v)) for v in C[old]]
            self.palette.append({"r": r, "g": g, "b": b, "hex": hexc(r, g, b),
                                 "count": int(counts[old]), "recipe": recipe(r, g, b)})
        if self.selected is not None and self.selected >= len(self.palette):
            self.selected = None
        self.canvas.selected = self.selected
        self.canvas.set_data(cols, rows, self.cell_labels, self.palette)
        self._render_palette()
        self._render_recipe()
        self.status.setText(f"{cols}×{rows} celdas · {len(self.palette)} pinturas")

    # ---------------- paneles ----------------
    def _render_palette(self):
        self.pal_title.setText(f"🎨  Paleta ({len(self.palette)} pinturas)")
        while self.pal_lay.count() > 1:
            it = self.pal_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for i, p in enumerate(self.palette):
            row = QFrame(); row.setObjectName("paint")
            row.setProperty("sel", i == self.selected)
            row.setStyleSheet("")  # forzar re-eval de estilo
            h = QHBoxLayout(row); h.setContentsMargins(6, 4, 6, 4); h.setSpacing(8)
            num = QLabel(str(i + 1)); num.setObjectName("pnum"); num.setFixedSize(22, 22)
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sw = QFrame(); sw.setFixedSize(28, 28); sw.setStyleSheet(f"background:{p['hex']}; border-radius:6px; border:1px solid #334155;")
            meta = QLabel(f"<b style='font-family:Consolas'>{p['hex']}</b><br><span style='color:#94a3b8;font-size:11px'>{p['count']} celdas</span>")
            h.addWidget(num); h.addWidget(sw); h.addWidget(meta); h.addStretch()
            row.mousePressEvent = (lambda e, idx=i: self._on_select(idx))
            if i == self.selected:
                row.setStyleSheet("QFrame#paint { border:1px solid #8b5cf6; background:#0f172a; border-radius:8px; }")
            self.pal_lay.insertWidget(self.pal_lay.count() - 1, row)

    def _render_recipe(self):
        while self.rec_bars.count():
            it = self.rec_bars.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if self.selected is None:
            self.rec_host.setVisible(False)
            return
        self.rec_host.setVisible(True)
        p = self.palette[self.selected]
        self.rec_swatch.setStyleSheet(f"background:{p['hex']}; border-radius:8px; border:1px solid #334155;")
        self.rec_info.setText(f"Pintura <b>#{self.selected + 1}</b> · <span style='font-family:Consolas'>{p['hex']}</span> · "
                              f"<b style='color:#34d399'>{p['count']}</b> celdas")
        for key in ("w", "c", "m", "y", "k"):
            if p["recipe"][key] > 0:
                nombre, color = MIX_INFO[key]
                self.rec_bars.addWidget(MixBar(nombre, color, p["recipe"][key]))

    def _on_select(self, idx):
        self.selected = idx
        self.canvas.selected = idx
        self.canvas.update()
        self._render_palette()
        self._render_recipe()

    # ---------------- controles ----------------
    def _res_changed(self, v):
        self.res_lbl.setText(f"Resolución: {v} px")
        self._procesar()

    def _col_changed(self, v):
        self.col_lbl.setText(f"Nº de colores: {v}")
        self._procesar()

    def _opts(self):
        self.canvas.show_grid = self.cb_grid.isChecked()
        self.canvas.show_num = self.cb_num.isChecked()
        self.canvas.highlight = self.cb_high.isChecked()
        self.canvas.update()

    # ---------------- exportar ----------------
    def _descargar(self):
        if self.cell_labels is None:
            return
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar guía", "guia-pixelart.png", "PNG (*.png)")
        if not ruta:
            return
        self.canvas.grab().save(ruta, "PNG")
        self.status.setText(f"Guía guardada: {ruta}")

    def _imprimible(self):
        if self.cell_labels is None:
            return
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar guía imprimible", "guia-imprimible.png", "PNG (*.png)")
        if not ruta:
            return
        canvas_pix = self.canvas.grab()
        cw, ch = canvas_pix.width(), canvas_pix.height()
        legend_rows = (len(self.palette) + 1) // 2
        W = max(cw, 540)
        H = ch + 60 + legend_rows * 34 + 20
        out = QPixmap(W, H); out.fill(QColor("#ffffff"))
        p = QPainter(out)
        p.drawPixmap((W - cw) // 2, 10, canvas_pix)
        p.setPen(QColor("#0f172a")); f = QFont("Segoe UI"); f.setPixelSize(16); f.setBold(True); p.setFont(f)
        p.drawText(16, ch + 40, "Paleta de pinturas")
        f2 = QFont("Segoe UI"); f2.setPixelSize(11); p.setFont(f2)
        for i, col in enumerate(self.palette):
            c, r = i % 2, i // 2
            x = 16 + c * (W // 2 - 8); yy = ch + 54 + r * 34
            p.setBrush(QColor(col["hex"])); p.setPen(QPen(QColor("#334155"), 1))
            p.drawRect(x, yy, 26, 26)
            rec = " ".join(f"{MIX_INFO[k][0][0]}{col['recipe'][k]}" for k in ("w", "c", "m", "y", "k") if col["recipe"][k] > 0)
            p.setPen(QColor("#0f172a")); p.drawText(x + 34, yy + 12, f"#{i+1}  {col['hex']}  ({col['count']})")
            p.setPen(QColor("#475569")); p.drawText(x + 34, yy + 25, rec)
        p.end()
        out.save(ruta, "PNG")
        self.status.setText(f"Guía imprimible guardada: {ruta}")


ESTILO = """
* { font-family: 'Segoe UI'; }
QWidget { background: #0f172a; color: #e2e8f0; font-size: 13px; }
QLabel#h1 { font-size: 22px; font-weight: 800; color: #f8fafc; }
QLabel#h3 { font-size: 14px; font-weight: 700; color: #f8fafc; }
QLabel#muted { color: #94a3b8; font-size: 12px; }
QLabel#ctl { color: #e2e8f0; font-weight: 600; font-size: 12px; }
QLabel#status { color: #94a3b8; padding-top: 6px; border-top: 1px solid #1e293b; }
QLabel#ph { color: #475569; font-size: 18px; }
QLabel#pnum { background: #0f172a; border: 1px solid #334155; border-radius: 6px; font-weight: 700; font-size: 11px; }
QFrame#card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; }
QFrame#paint { border-radius: 8px; }
QFrame#paint:hover { background: #0f172a; }
QScrollArea#cscroll, QScrollArea#palscroll { background: #1e293b; border: 1px solid #334155; border-radius: 12px; }
QScrollArea#cscroll > QWidget > QWidget { background: #1e293b; }
QPushButton#accent { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ec4899, stop:1 #8b5cf6);
  color: #fff; border: none; border-radius: 10px; padding: 10px; font-weight: 700; }
QPushButton#ghost { background: #334155; color: #fff; border: none; border-radius: 10px; padding: 10px; font-weight: 700; }
QPushButton#ghost:hover { background: #475569; }
QPushButton:disabled { background: #1e293b; color: #475569; }
QCheckBox { color: #e2e8f0; font-weight: 600; padding: 4px 0; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid #334155; background: #0f172a; }
QCheckBox::indicator:checked { background: #8b5cf6; border-color: #8b5cf6; }
QSlider::groove:horizontal { height: 5px; background: #334155; border-radius: 3px; }
QSlider::handle:horizontal { background: #8b5cf6; width: 15px; height: 15px; margin: -6px 0; border-radius: 8px; }
"""


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(ESTILO)
    v = PixelPainter()
    v.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
