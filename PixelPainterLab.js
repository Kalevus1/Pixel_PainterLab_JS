import React, { useState, useRef, useEffect } from 'react';
import { Upload, Paintbrush, Grid, Droplet, Maximize, Minimize, Download, Info, Layers, Palette } from 'lucide-react';

const PixelArtPainter = () => {
  const [image, setImage] = useState(null);
  const [pixelSize, setPixelSize] = useState(32); // Cantidad de píxeles de ancho
  const [colorTolerance, setColorTolerance] = useState(15); // Nuevo: Tolerancia de color (0-50)
  const [selectedColor, setSelectedColor] = useState(null);
  const [showGrid, setShowGrid] = useState(true);
  const [highlightSimilar, setHighlightSimilar] = useState(true);
  const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 });
  const [matchingPixelsCount, setMatchingPixelsCount] = useState(0);
  
  const canvasRef = useRef(null);
  const originalImageRef = useRef(null);
  const lowResDataRef = useRef(null);

  // Paleta de mezcla
  const [mixingRecipe, setMixingRecipe] = useState({ c: 0, m: 0, y: 0, k: 0, w: 0 });

  // Cargar imagen
  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const img = new Image();
        img.onload = () => {
          originalImageRef.current = img;
          setImage(img);
          setSelectedColor(null);
          setMatchingPixelsCount(0);
        };
        img.src = event.target.result;
      };
      reader.readAsDataURL(file);
    }
  };

  // Función maestra de renderizado
  const renderCanvas = () => {
    const img = originalImageRef.current;
    if (!img) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    const aspectRatio = img.width / img.height;
    const canvasWidth = 500; 
    const canvasHeight = canvasWidth / aspectRatio;

    if (canvas.width !== canvasWidth || canvas.height !== canvasHeight) {
      setCanvasSize({ width: canvasWidth, height: canvasHeight });
      canvas.width = canvasWidth;
      canvas.height = canvasHeight;
    }

    // --- Paso 1: Generar datos de píxeles (Low Res) ---
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = pixelSize;
    tempCanvas.height = Math.round(pixelSize / aspectRatio);
    const tempCtx = tempCanvas.getContext('2d');
    
    // Dibujar imagen reducida
    tempCtx.drawImage(img, 0, 0, tempCanvas.width, tempCanvas.height);
    
    // Obtener datos crudos
    const pixelData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
    const data = pixelData.data;

    // --- NUEVO: Estandarizar Colores (Quantization) ---
    // Redondeamos los valores RGB para agrupar colores similares
    // El 'step' determina cuán agresiva es la agrupación (ej. step 25 significa que colores entre 0-25 son iguales)
    const step = Math.max(1, colorTolerance * 2.55); // Mapear 0-100 a 0-255 aprox

    for (let i = 0; i < data.length; i += 4) {
        // Redondear cada canal al múltiplo más cercano del 'step'
        data[i] = Math.round(data[i] / step) * step;     // R
        data[i+1] = Math.round(data[i+1] / step) * step; // G
        data[i+2] = Math.round(data[i+2] / step) * step; // B
        // Alpha se queda igual (data[i+3])
    }
    
    // Volvemos a poner los datos "simplificados" en el canvas temporal
    tempCtx.putImageData(pixelData, 0, 0);
    
    // Guardamos los datos estandarizados para análisis
    lowResDataRef.current = pixelData;

    // --- Paso 2: Dibujar imagen escalada al canvas visible ---
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(tempCanvas, 0, 0, tempCanvas.width, tempCanvas.height, 0, 0, canvasWidth, canvasHeight);

    // --- Paso 3: Resaltar píxeles idénticos ---
    if (selectedColor && highlightSimilar) {
        highlightMatchingPixels(ctx, pixelData, tempCanvas.width, tempCanvas.height, canvasWidth, canvasHeight);
    }

    // --- Paso 4: Dibujar cuadrícula ---
    if (showGrid) {
      drawGrid(ctx, canvasWidth, canvasHeight, tempCanvas.width, tempCanvas.height);
    }
  };

  const highlightMatchingPixels = (ctx, pixelData, cols, rows, width, height) => {
    const data = pixelData.data;
    const cellWidth = width / cols;
    const cellHeight = height / rows;
    let count = 0;

    const targetR = selectedColor.r;
    const targetG = selectedColor.g;
    const targetB = selectedColor.b;

    // Usamos un color de resalte dinámico según si el pixel es oscuro o claro para contraste
    const isDark = (targetR + targetG + targetB) / 3 < 128;
    ctx.strokeStyle = isDark ? '#00ff00' : '#ff00ff'; // Verde para oscuros, Magenta para claros
    ctx.lineWidth = 2;
    ctx.fillStyle = isDark ? 'rgba(255, 255, 255, 0.25)' : 'rgba(0, 0, 0, 0.25)';

    for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
            const i = (y * cols + x) * 4;
            if (data[i] === targetR && data[i+1] === targetG && data[i+2] === targetB) {
                count++;
                ctx.fillRect(x * cellWidth, y * cellHeight, cellWidth, cellHeight);
                ctx.strokeRect(x * cellWidth, y * cellHeight, cellWidth, cellHeight);
            }
        }
    }
    
    if (count !== matchingPixelsCount) setMatchingPixelsCount(count);
  };

  const drawGrid = (ctx, width, height, cols, rows) => {
    ctx.strokeStyle = 'rgba(128, 128, 128, 0.3)';
    ctx.lineWidth = 1;
    const cellWidth = width / cols;
    const cellHeight = height / rows;
    
    ctx.beginPath();
    for (let i = 0; i <= cols; i++) {
      ctx.moveTo(i * cellWidth, 0); ctx.lineTo(i * cellWidth, height);
    }
    for (let i = 0; i <= rows; i++) {
      ctx.moveTo(0, i * cellHeight); ctx.lineTo(width, i * cellHeight);
    }
    ctx.stroke();
  };

  useEffect(() => {
    renderCanvas();
  }, [image, pixelSize, colorTolerance, showGrid, selectedColor, highlightSimilar]);

  // --- NUEVO: Cálculo de Receta Redondeada ---
  const calculateMixingRecipe = (r, g, b) => {
    let rNorm = r / 255;
    let gNorm = g / 255;
    let bNorm = b / 255;
    let k = 1 - Math.max(rNorm, gNorm, bNorm);
    let c = (1 - rNorm - k) / (1 - k) || 0;
    let m = (1 - gNorm - k) / (1 - k) || 0;
    let y = (1 - bNorm - k) / (1 - k) || 0;
    
    const lightness = (Math.max(r, g, b) + Math.min(r, g, b)) / 2;
    let w = 0;
    if (lightness > 127) w = (lightness - 127) / 128;
    if (w > 0.5) k = k * 0.5;

    // Función auxiliar para redondear al 5% más cercano
    const roundTo5 = (num) => Math.round(num / 5) * 5;

    setMixingRecipe({
      c: roundTo5(c * 100),
      m: roundTo5(m * 100),
      y: roundTo5(y * 100),
      k: roundTo5(k * 100),
      w: roundTo5(w * 100)
    });
  };

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas || !lowResDataRef.current) return;

    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const imgAspect = originalImageRef.current.width / originalImageRef.current.height;
    const cols = pixelSize;
    const rows = Math.round(pixelSize / imgAspect);
    
    const cellWidth = canvas.width / cols;
    const cellHeight = canvas.height / rows;
    
    const gridX = Math.floor(clickX / cellWidth);
    const gridY = Math.floor(clickY / cellHeight);

    if (gridX < 0 || gridX >= cols || gridY < 0 || gridY >= rows) return;

    const data = lowResDataRef.current.data;
    const index = (gridY * cols + gridX) * 4;
    
    const color = {
      r: data[index],
      g: data[index + 1],
      b: data[index + 2],
      hex: rgbToHex(data[index], data[index + 1], data[index + 2]),
      x: gridX + 1,
      y: gridY + 1
    };

    // Permitir re-seleccionar para asegurar actualización si el usuario cambia parámetros
    setMatchingPixelsCount(0); 
    setSelectedColor(color);
    calculateMixingRecipe(color.r, color.g, color.b);
  };

  const rgbToHex = (r, g, b) => {
    return "#" + [r, g, b].map(x => {
      const hex = x.toString(16);
      return hex.length === 1 ? "0" + hex : hex;
    }).join("");
  };

  const downloadCanvas = () => {
    const canvas = canvasRef.current;
    const link = document.createElement('a');
    link.download = 'guia-pixelart-pintura.png';
    link.href = canvas.toDataURL();
    link.click();
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        
        <header className="mb-8 text-center">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-pink-500 to-violet-500 bg-clip-text text-transparent mb-2">
            PixelPainter Lab
          </h1>
          <p className="text-slate-400">
            Estandariza tus colores y obtén recetas de mezcla simplificadas.
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Controles */}
          <div className="lg:col-span-3 space-y-6">
            <div className="bg-slate-800 p-6 rounded-xl shadow-lg border border-slate-700">
              <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-slate-600 border-dashed rounded-lg cursor-pointer hover:bg-slate-700/50 transition-colors">
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <Upload className="w-8 h-8 mb-3 text-slate-400" />
                  <p className="text-sm text-slate-400"><span className="font-semibold">Sube tu imagen</span></p>
                  <p className="text-xs text-slate-500">JPG, PNG</p>
                </div>
                <input type="file" className="hidden" onChange={handleImageUpload} accept="image/*" />
              </label>
            </div>

            {image && (
              <div className="bg-slate-800 p-6 rounded-xl shadow-lg border border-slate-700 space-y-6">
                
                {/* Slider Resolución */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                      <Maximize size={16} /> Resolución
                    </label>
                    <span className="text-xs bg-violet-600 px-2 py-1 rounded text-white font-bold">{pixelSize} px</span>
                  </div>
                  <input 
                    type="range" min="10" max="100" value={pixelSize} 
                    onChange={(e) => setPixelSize(parseInt(e.target.value))}
                    className="w-full h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer accent-violet-500"
                  />
                </div>

                {/* Slider Estandarización (Nuevo) */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm font-medium text-slate-300 flex items-center gap-2 text-yellow-400">
                      <Palette size={16} /> Agrupar Colores
                    </label>
                    <span className="text-xs bg-yellow-600 px-2 py-1 rounded text-white font-bold">{colorTolerance}%</span>
                  </div>
                  <input 
                    type="range" min="0" max="40" value={colorTolerance} 
                    onChange={(e) => setColorTolerance(parseInt(e.target.value))}
                    className="w-full h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer accent-yellow-500"
                  />
                  <p className="text-[10px] text-slate-400 mt-1">
                    Sube este valor para eliminar pequeñas variaciones de color.
                  </p>
                </div>

                {/* Botones Toggle */}
                <div className="space-y-3 pt-2 border-t border-slate-700">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                      <Grid size={16} /> Mostrar Guía
                    </label>
                    <button 
                      onClick={() => setShowGrid(!showGrid)}
                      className={`w-12 h-6 rounded-full transition-colors relative ${showGrid ? 'bg-violet-500' : 'bg-slate-600'}`}
                    >
                      <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${showGrid ? 'left-7' : 'left-1'}`}></div>
                    </button>
                  </div>

                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                      <Layers size={16} /> Resaltar Iguales
                    </label>
                    <button 
                      onClick={() => setHighlightSimilar(!highlightSimilar)}
                      className={`w-12 h-6 rounded-full transition-colors relative ${highlightSimilar ? 'bg-pink-500' : 'bg-slate-600'}`}
                    >
                      <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${highlightSimilar ? 'left-7' : 'left-1'}`}></div>
                    </button>
                  </div>
                </div>

                <button onClick={downloadCanvas} className="w-full py-2 flex items-center justify-center gap-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors text-sm font-medium">
                  <Download size={16} /> Descargar Guía
                </button>
              </div>
            )}
          </div>

          {/* Canvas Central */}
          <div className="lg:col-span-6 flex flex-col items-center justify-start min-h-[500px]">
            {image ? (
              <div className="relative shadow-2xl rounded-lg overflow-hidden border-4 border-slate-800 bg-slate-800">
                <canvas 
                  ref={canvasRef} 
                  onClick={handleCanvasClick}
                  className="cursor-crosshair max-w-full h-auto block"
                />
                {!selectedColor && (
                  <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black/70 px-4 py-2 rounded-full text-sm backdrop-blur-sm pointer-events-none flex items-center gap-2 w-max border border-slate-600">
                    <Droplet size={14} className="text-yellow-400" /> Toca un color para ver su receta
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 opacity-50">
                <Paintbrush size={64} className="mb-4" />
                <p>Sube una imagen para comenzar</p>
              </div>
            )}
          </div>

          {/* Panel Derecho */}
          <div className="lg:col-span-3">
            <div className="bg-slate-800 rounded-xl shadow-lg border border-slate-700 overflow-hidden h-full">
              <div className="bg-slate-750 p-4 border-b border-slate-700 flex items-center gap-2">
                <Paintbrush className="text-violet-400" size={20} />
                <h3 className="font-bold text-lg">Datos de Pintura</h3>
              </div>
              
              <div className="p-6">
                {selectedColor ? (
                  <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    
                    {/* Estadísticas */}
                    <div className="flex items-start gap-4">
                      <div 
                        className="w-20 h-20 rounded-lg shadow-inner border border-slate-600 flex-shrink-0"
                        style={{ backgroundColor: selectedColor.hex }}
                      ></div>
                      <div>
                        <p className="text-xs text-slate-400 uppercase tracking-wider">Píxeles Iguales</p>
                        <div className="mt-1">
                           <p className="text-4xl font-bold text-green-400">{matchingPixelsCount}</p>
                        </div>
                        <p className="text-xs text-slate-500 font-mono mt-2">{selectedColor.hex}</p>
                      </div>
                    </div>

                    <div className="bg-slate-900/50 p-3 rounded border border-slate-700/50">
                        <p className="text-xs text-slate-400">
                            Los colores están <span className="text-yellow-400">simplificados</span>. Pinta estos {matchingPixelsCount} cuadros exactamente con la misma mezcla.
                        </p>
                    </div>

                    <div className="h-px bg-slate-700"></div>

                    {/* Receta */}
                    <div>
                      <h4 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                        <Info size={14} /> Receta (Pasos de 5%)
                      </h4>
                      
                      <div className="space-y-3">
                        <MixBar label="Blanco" color="bg-white" value={mixingRecipe.w} textColor="text-slate-900" />
                        <MixBar label="Cian" color="bg-cyan-500" value={mixingRecipe.c} />
                        <MixBar label="Magenta" color="bg-fuchsia-500" value={mixingRecipe.m} />
                        <MixBar label="Amarillo" color="bg-yellow-400" value={mixingRecipe.y} textColor="text-slate-900" />
                        <MixBar label="Negro" color="bg-black" value={mixingRecipe.k} />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-slate-500 py-10">
                    <Droplet size={48} className="mx-auto mb-4 opacity-20" />
                    <p>Selecciona un píxel para ver la mezcla estandarizada.</p>
                  </div>
                )}
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

const MixBar = ({ label, color, value, textColor = "text-white" }) => {
  if (value <= 0) return null;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-300">{label}</span>
        <span className="font-mono text-slate-400">{value}%</span>
      </div>
      <div className="h-4 w-full bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} ${textColor} text-[10px] font-bold flex items-center justify-center transition-all duration-500`} style={{ width: `${value}%` }}></div>
      </div>
    </div>
  );
};

export default PixelArtPainter;