"""
Interfaz gráfica para Conversor de Facturas a Excel
Versión con Tkinter (sin conflictos con PyTorch)
"""

import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['USE_CUDA'] = '0'

import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

sys.path.insert(0, str(Path(__file__).parent))

from process_opencv import ProcessadorArchivos
from extractor import ExtractorFacturas
from excel_exporter import ExcelExporter
from factura_estructura import Factura


class ConversorFacturasApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Conversor de Facturas a Excel")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        self.archivo_actual = None
        self.datos_extraccion = None
        
        self.crear_ui()
        
    def crear_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        titulo = ttk.Label(main_frame, text="📋 Sistema de Conversión de Facturas", 
                          font=('Arial', 16, 'bold'))
        titulo.pack(pady=10)
        
        # Frame de selección de archivo
        frame_archivo = ttk.LabelFrame(main_frame, text="1. SELECCIONAR DOCUMENTO", padding="10")
        frame_archivo.pack(fill=tk.X, pady=5)
        
        self.entrada_archivo = ttk.Entry(frame_archivo, width=60)
        self.entrada_archivo.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        btn_examinar = ttk.Button(frame_archivo, text="Examinar", command=self.seleccionar_archivo)
        btn_examinar.pack(side=tk.RIGHT, padx=5)
        
        # Frame de salida
        frame_salida = ttk.LabelFrame(main_frame, text="2. CARPETA DE SALIDA", padding="10")
        frame_salida.pack(fill=tk.X, pady=5)
        
        carpeta_default = str(Path(__file__).parent.parent / 'salida')
        self.entrada_carpeta = ttk.Entry(frame_salida, width=60)
        self.entrada_carpeta.insert(0, carpeta_default)
        self.entrada_carpeta.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        btn_carpeta = ttk.Button(frame_salida, text="Examinar", command=self.seleccionar_carpeta)
        btn_carpeta.pack(side=tk.RIGHT, padx=5)
        
        # Barra de progreso
        self.progreso = ttk.Progressbar(main_frame, mode='determinate', length=400)
        self.progreso.pack(pady=10)
        
        # Estado
        self.label_estado = ttk.Label(main_frame, text="Estado: Listo", font=('Arial', 10))
        self.label_estado.pack(pady=5)
        
        # Botones
        frame_botones = ttk.Frame(main_frame)
        frame_botones.pack(pady=10)
        
        self.btn_procesar = ttk.Button(frame_botones, text="PROCESAR FACTURA", 
                                       command=self.procesar_factura)
        self.btn_procesar.pack(side=tk.LEFT, padx=10)
        
        btn_limpiar = ttk.Button(frame_botones, text="Limpiar", command=self.limpiar)
        btn_limpiar.pack(side=tk.LEFT, padx=10)
        
        # Área de resultados
        frame_resultado = ttk.LabelFrame(main_frame, text="RESULTADO", padding="10")
        frame_resultado.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.texto_resultado = tk.Text(frame_resultado, height=15, width=80)
        self.texto_resultado.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(frame_resultado, orient=tk.VERTICAL, 
                                  command=self.texto_resultado.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.texto_resultado.configure(yscrollcommand=scrollbar.set)
        
    def seleccionar_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar Factura",
            filetypes=[
                ("Documentos", "*.pdf *.jpg *.jpeg *.png *.tiff *.bmp"),
                ("PDF", "*.pdf"),
                ("Imágenes", "*.jpg *.jpeg *.png *.tiff *.bmp"),
                ("Todos", "*.*")
            ]
        )
        if ruta:
            self.archivo_actual = ruta
            self.entrada_archivo.delete(0, tk.END)
            self.entrada_archivo.insert(0, ruta)
            self.actualizar_estado("Archivo seleccionado")
            
    def seleccionar_carpeta(self):
        carpeta = filedialog.askdirectory(title="Seleccionar Carpeta de Salida")
        if carpeta:
            self.entrada_carpeta.delete(0, tk.END)
            self.entrada_carpeta.insert(0, carpeta)
            
    def actualizar_estado(self, mensaje):
        self.label_estado.config(text=f"Estado: {mensaje}")
        self.root.update_idletasks()
        
    def log(self, mensaje):
        self.texto_resultado.insert(tk.END, mensaje + "\n")
        self.texto_resultado.see(tk.END)
        self.root.update_idletasks()
        
    def procesar_factura(self):
        if not self.archivo_actual:
            messagebox.showwarning("Error", "Por favor selecciona un archivo primero")
            return
            
        self.btn_procesar.config(state='disabled')
        self.texto_resultado.delete(1.0, tk.END)
        self.progreso['value'] = 0
        
        # Ejecutar en hilo separado
        thread = threading.Thread(target=self._procesar_en_hilo)
        thread.start()
        
    def _procesar_en_hilo(self):
        try:
            self.root.after(0, lambda: self.actualizar_estado("Inicializando OCR..."))
            self.root.after(0, lambda: self.log("→ Iniciando procesamiento..."))
            self.root.after(0, lambda: self.progreso.configure(value=10))
            
            # Paso 1: OCR
            self.root.after(0, lambda: self.actualizar_estado("Escaneando documento con EasyOCR..."))
            self.root.after(0, lambda: self.log("→ Ejecutando OCR (puede tardar la primera vez)..."))
            
            procesador = ProcessadorArchivos()
            resultado_proceso = procesador.procesar_archivo(self.archivo_actual)
            
            if not resultado_proceso['exito']:
                error = resultado_proceso.get('error', 'Error desconocido')
                self.root.after(0, lambda: messagebox.showerror("Error OCR", error))
                self.root.after(0, lambda: self.btn_procesar.config(state='normal'))
                return
                
            self.root.after(0, lambda: self.progreso.configure(value=40))
            motor = resultado_proceso.get('procesado_con', 'OCR')
            self.root.after(0, lambda: self.log(f"✓ OCR completado con {motor}"))
            
            # Paso 2: Extracción
            self.root.after(0, lambda: self.actualizar_estado("Extrayendo datos..."))
            self.root.after(0, lambda: self.log("→ Extrayendo datos de factura..."))
            
            texto_extraido = resultado_proceso.get('texto', '')
            self.root.after(0, lambda: self.log(f"  Texto extraído: {len(texto_extraido)} caracteres"))
            
            extractor = ExtractorFacturas()
            datos_raw = extractor.extraer_todos(texto_extraido)
            
            self.root.after(0, lambda: self.progreso.configure(value=60))
            
            # Paso 3: Estructura
            self.root.after(0, lambda: self.actualizar_estado("Estructurando datos..."))
            factura = Factura.desde_dict(datos_raw)
            factura.archivo_origen = self.archivo_actual
            datos_factura = factura.to_dict_plano()
            
            self.root.after(0, lambda: self.progreso.configure(value=70))
            
            # Paso 4: Excel
            self.root.after(0, lambda: self.actualizar_estado("Generando Excel..."))
            self.root.after(0, lambda: self.log("→ Generando archivo Excel..."))
            
            carpeta_salida = Path(self.entrada_carpeta.get())
            carpeta_salida.mkdir(parents=True, exist_ok=True)
            
            exporter = ExcelExporter()
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"factura_{datos_factura['numero_factura']}_{timestamp}.xlsx"
            ruta_excel = str(carpeta_salida / nombre_archivo)
            
            if exporter.crear_hoja_unica(datos_factura, ruta_excel):
                self.root.after(0, lambda: self.progreso.configure(value=100))
                self.root.after(0, lambda: self.actualizar_estado("¡Completado!"))
                self.root.after(0, lambda: self.log(f"\n✓✓✓ ÉXITO ✓✓✓"))
                self.root.after(0, lambda: self.log(f"\nArchivo guardado en:\n{ruta_excel}"))
                self.root.after(0, lambda: self.log(f"\n--- DATOS EXTRAÍDOS ---"))
                for k, v in datos_factura.items():
                    if k != 'items':
                        self.root.after(0, lambda k=k, v=v: self.log(f"  {k}: {v}"))
                        
                self.root.after(0, lambda: messagebox.showinfo("Éxito", 
                    f"Factura procesada con {motor}!\n\nArchivo guardado en:\n{ruta_excel}"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Error al generar Excel"))
                
        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}\n\n{traceback.format_exc()}"
            self.root.after(0, lambda: self.log(f"\n✗ ERROR: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            
        finally:
            self.root.after(0, lambda: self.btn_procesar.config(state='normal'))
            
    def limpiar(self):
        self.entrada_archivo.delete(0, tk.END)
        self.archivo_actual = None
        self.progreso['value'] = 0
        self.texto_resultado.delete(1.0, tk.END)
        self.actualizar_estado("Listo")


def main():
    root = tk.Tk()
    app = ConversorFacturasApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
