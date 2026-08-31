# 🎨 PixelPainter Lab

Autor: **KALEVI LATVA AIJO ALEGRIA** · Windows · 100 % local (nada sale de tu equipo)

Convierte cualquier imagen en una **guía para pintar por números**: elige cuántos colores
quieres usar y obtén una **cuadrícula numerada** más la **receta de mezcla** de cada pintura.
Ideal para pixel art, cuadros por números, punto de cruz, perler beads / hama, etc.

## ✨ Qué mejoré respecto al original

- 🧮 **Cuantización real con K-means:** en vez de redondear cada canal RGB (que dejaba muchos
  casi-duplicados), agrupa los colores con K-means y **tú eliges cuántas pinturas** usar.
- 🗂️ **Leyenda de la paleta completa:** lista de todas las pinturas con su número, HEX, cuántas
  celdas ocupa y su receta. Clic en una pintura resalta sus celdas.
- #️⃣ **Números dentro de cada celda:** guía de "pinta por números" de verdad (toggle).
- 🧪 **Receta normalizada:** blanco/cian/magenta/amarillo/negro en **pasos de 5 % que suman 100 %**,
  coherente y reproducible (antes era ad-hoc y no sumaba).
- 🖨️ **Guía imprimible:** exporta la cuadrícula numerada **con la leyenda de colores** debajo.

## 📦 Versiones

| Versión | Archivo | Cómo se usa |
|---------|---------|-------------|
| 🖥️ **Escritorio (.exe)** | `PixelPainter.exe` (Release) | Doble clic, sin instalar nada |
| 🐍 **Python** | `pixelpainter_lab.py` | `PixelPainter.bat` |
| 🌐 **Web (HTML)** | `web/index.html` | Doble clic → navegador. Ideal para **GitHub Pages** |

> Las versiones comparten el mismo motor (K-means + receta) y las mismas funciones.

## ⬇️ Descargar (sin instalar Python)

En **[Releases](../../releases)**: `PixelPainter_carpeta.zip` → descomprime y ejecuta
**`PixelPainter.exe`**.
*(Es un `.exe` sin firmar: Windows SmartScreen puede pedir "Más info → Ejecutar de todos modos".)*

## ▶️ Cómo usar

1. **Sube una imagen** (o arrástrala, en la web).
2. Ajusta la **Resolución** (celdas de ancho) y el **Nº de colores** (pinturas).
3. Activa **Números** y **Cuadrícula** para la guía; **Resaltar iguales** para ver un color.
4. **Clic en un color** (en el lienzo o en la paleta) → ves su **receta de mezcla** y cuántas
   celdas hay que pintar de ese tono.
5. **Descargar guía (PNG)** o **Guía imprimible (con leyenda)**.

## ⚙️ Tecnología

- **Python 3.12** · **PySide6** (Qt 6) · **NumPy** (K-means) · **Pillow** (leer/redimensionar imagen).
- Lienzo dibujado con `QPainter`. Web: HTML + Canvas, un solo archivo, sin librerías externas.
- Reutiliza el entorno `..\.venv_face`; si no, `instalar.bat` crea `.venv`.

## 🔨 Generar el `.exe`

`pip install pyinstaller` y doble clic en **`crear_exe.bat`** → queda en `dist\PixelPainter\`.

---

Desarrollado y documentado por **KALEVI LATVA AIJO ALEGRIA**.
