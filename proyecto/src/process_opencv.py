"""
Módulo de procesamiento de archivos (Imágenes, PDFs, TXT)
Funciones independientes sin dependencia de UI
Usa EasyOCR como motor OCR principal
"""

import os
# FORZAR CPU - desactivar CUDA completamente ANTES de importar torch/easyocr
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['USE_CUDA'] = '0'
os.environ['TORCH_CUDA_ARCH_LIST'] = ''

import cv2
import pdfplumber
from pdf2image import convert_from_path
from PIL import Image
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from pdfminer.high_level import extract_text
import re

# Helper para inicializar EasyOCR de forma perezosa
_EASY_READER = None
_EASY_FAILED = False
_EASY_ERROR_MSG = None

def get_easyocr_reader():
    """Devuelve un objeto easyocr.Reader o None si no está disponible."""
    global _EASY_READER, _EASY_FAILED, _EASY_ERROR_MSG
    if _EASY_FAILED:
        return None
    if _EASY_READER is not None:
        return _EASY_READER
    try:
        print("  > Inicializando EasyOCR en modo CPU...")
        import easyocr
        _EASY_READER = easyocr.Reader(['es', 'en'], gpu=False, verbose=False)
        print("  OK EasyOCR Reader creado exitosamente (CPU)")
        return _EASY_READER
    except Exception as e:
        import traceback
        _EASY_FAILED = True
        _EASY_ERROR_MSG = str(e)
        print(f"  ERROR al crear EasyOCR Reader: {e}")
        traceback.print_exc()
        return None


def easyocr_read_image(np_image):
    """Lee texto con EasyOCR. Devuelve texto o lanza excepción si falla."""
    reader = get_easyocr_reader()
    if not reader:
        raise RuntimeError(f"EasyOCR no disponible. Error: {_EASY_ERROR_MSG}")
    
    print("  > Ejecutando OCR con EasyOCR...")
    res = reader.readtext(np_image, detail=0, paragraph=True)
    if not res:
        return ""
    texto = '\n'.join(linea.strip() for linea in res if str(linea).strip())
    print(f"  OK EasyOCR extrajo {len(texto)} caracteres")
    return texto

# Importar corrector de palabras
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'diccionario'))
try:
    from correction_deteccio import CorrectorDeteccion
    CORRECTOR_DISPONIBLE = True
except:
    CORRECTOR_DISPONIBLE = False
    print("Advertencia: Corrector de palabras no disponible")


class ProcessadorArchivos:
    """Procesa archivos con EasyOCR"""

    def __init__(self):
        self.tipos_soportados = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp'}
        self.corrector = CorrectorDeteccion() if CORRECTOR_DISPONIBLE else None
        self._verificar_easyocr()

    def _verificar_easyocr(self):
        """Verifica que EasyOCR esté disponible"""
        reader = get_easyocr_reader()
        if reader:
            print("OK EasyOCR disponible y listo")
        else:
            print("WARN EasyOCR no disponible - verifica la instalación")
    
    def _corregir_texto(self, texto: str) -> str:
        """Aplica corrección de palabras mal detectadas"""
        if self.corrector and texto:
            return self.corrector.corregir_texto(texto)
        return texto

    def _preprocesar_imagen(self, img_rgb):
        """Genera variantes de la imagen para mejorar la detección OCR."""
        variantes = []

        if len(img_rgb.shape) == 3:
            gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_rgb.copy()

        altura, ancho = gray.shape[:2]
        escala = 1.5 if max(altura, ancho) < 1400 else 1.0
        if escala != 1.0:
            gray = cv2.resize(gray, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)

        suavizada = cv2.GaussianBlur(gray, (3, 3), 0)
        binaria = cv2.adaptiveThreshold(
            suavizada,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )
        binaria_inversa = cv2.bitwise_not(binaria)

        variantes.append(("original", img_rgb))
        variantes.append(("gris", cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)))
        variantes.append(("binaria", cv2.cvtColor(binaria, cv2.COLOR_GRAY2RGB)))
        variantes.append(("binaria_inversa", cv2.cvtColor(binaria_inversa, cv2.COLOR_GRAY2RGB)))

        return variantes

    def _combinar_textos_ocr(self, textos: List[str]) -> str:
        """Une textos OCR evitando duplicados y conservando saltos de línea."""
        vistos = set()
        lineas = []

        for texto in textos:
            if not texto:
                continue

            for linea in texto.splitlines():
                limpia = re.sub(r'\s+', ' ', linea).strip()
                if not limpia:
                    continue

                clave = re.sub(r'[^a-z0-9]+', '', limpia.lower())
                if not clave or clave in vistos:
                    continue

                vistos.add(clave)
                lineas.append(limpia)

        return '\n'.join(lineas)

    def validar_archivo(self, ruta_archivo: str) -> Tuple[bool, str]:
        """
        Valida si el archivo existe y tiene extensión soportada

        Args:
            ruta_archivo: Ruta del archivo a validar

        Returns:
            Tuple (es_valido, mensaje)
        """
        if not os.path.exists(ruta_archivo):
            return False, f"El archivo no existe: {ruta_archivo}"

        ext = Path(ruta_archivo).suffix.lower()
        if ext not in self.tipos_soportados:
            return False, f"Formato no soportado: {ext}. Soportados: {self.tipos_soportados}"

        return True, "Archivo válido"

    def procesar_imagen(self, ruta_imagen: str) -> Dict:
        """
        Procesa una imagen con EasyOCR (motor principal).

        Args:
            ruta_imagen: Ruta de la imagen

        Returns:
            Dict con datos extraídos
        """
        print(f"\n{'='*50}")
        print(f"  > Procesando imagen: {Path(ruta_imagen).name}")
        
        # Leer imagen
        img = cv2.imread(ruta_imagen)
        if img is None:
            print(f"  ERROR: No se pudo leer la imagen: {ruta_imagen}")
            return {'exito': False, 'error': 'No se pudo leer la imagen'}

        print(f"  OK Imagen cargada: {img.shape[1]}x{img.shape[0]} px")

        # Preprocesamiento
        print("  > Preprocesando imagen...")
        
        # Convertir a RGB para EasyOCR
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # OCR con EasyOCR (motor principal)
        try:
            textos_candidatos = []
            for nombre_variacion, imagen_variacion in self._preprocesar_imagen(img_rgb):
                try:
                    texto_variacion = easyocr_read_image(imagen_variacion)
                    if texto_variacion:
                        textos_candidatos.append(texto_variacion)
                        print(f"  OK OCR variante '{nombre_variacion}' produjo {len(texto_variacion)} chars")
                except Exception as error_variacion:
                    print(f"  WARN OCR variante '{nombre_variacion}' falló: {error_variacion}")

            texto_extraido = self._combinar_textos_ocr(textos_candidatos)
            if not texto_extraido:
                texto_extraido = easyocr_read_image(img_rgb)
            origen = 'EasyOCR'
            print(f"  OK Texto extraído con EasyOCR ({len(texto_extraido)} chars)")
        except Exception as e:
            import traceback
            error_detalle = traceback.format_exc()
            print(f"  ERROR en EasyOCR: {e}")
            return {
                'exito': False, 
                'error': f'Error en EasyOCR: {str(e)}',
                'detalle': error_detalle
            }

        # Corregir palabras mal detectadas
        print("  > Aplicando corrección de texto...")
        texto_corregido = self._corregir_texto(texto_extraido)

        altura, ancho = img.shape[:2]
        
        print(f"  OK Procesamiento completado con {origen}")
        print(f"{'='*50}\n")

        return {
            'exito': True,
            'archivo': Path(ruta_imagen).name,
            'tipo': 'IMAGEN',
            'texto': texto_corregido.strip(),
            'texto_original': texto_extraido.strip() if isinstance(texto_extraido, str) else '',
            'procesado_con': origen,
            'dimensiones': {'ancho': ancho, 'altura': altura},
            'peso_kb': os.path.getsize(ruta_imagen) / 1024
        }

    def procesar_pdf(self, ruta_pdf: str) -> Dict:
        """
        Procesa PDF con pdfminer + EasyOCR

        Args:
            ruta_pdf: Ruta del archivo PDF

        Returns:
            Dict con datos extraídos
        """
        try:
            datos_pdf = {
                'exito': True,
                'archivo': Path(ruta_pdf).name,
                'tipo': 'PDF',
                'paginas': [],
                'total_paginas': 0,
                'peso_kb': os.path.getsize(ruta_pdf) / 1024
            }

            # pdfplumber
            with pdfplumber.open(ruta_pdf) as pdf:
                datos_pdf['total_paginas'] = len(pdf.pages)

                for idx, page in enumerate(pdf.pages, 1):
                    texto = page.extract_text()
                    datos_pdf['paginas'].append({
                        'numero': idx,
                        'texto': texto.strip() if texto else '',
                        'procesado_con': 'pdfplumber'
                    })

            # Si hay páginas vacías, pdfminer
            paginas_vacias = [p for p in datos_pdf['paginas'] if not p['texto']]

            if paginas_vacias:
                print(f"  {len(paginas_vacias)} páginas vacías. Usando pdfminer...")
                try:
                    texto = extract_text(ruta_pdf)
                    if texto:
                        datos_pdf['paginas'][0]['texto'] = texto.strip()
                        datos_pdf['paginas'][0]['procesado_con'] = 'pdfminer'
                except:
                    pass

            # Si hay páginas vacías, usar EasyOCR
            paginas_vacias = [p for p in datos_pdf['paginas'] if not p['texto']]

            if paginas_vacias:
                print(f"  {len(paginas_vacias)} páginas vacías. Usando EasyOCR...")
                imagenes = convert_from_path(ruta_pdf)

                for idx, imagen in enumerate(imagenes, 1):
                    if idx <= len(datos_pdf['paginas']) and not datos_pdf['paginas'][idx - 1]['texto']:
                        # Convertir a numpy array RGB
                        import numpy as np
                        img_array = np.array(imagen)  # Ya está en RGB desde pdf2image

                        # OCR con EasyOCR
                        texto_obtenido = easyocr_read_image(img_array)
                        datos_pdf['paginas'][idx - 1]['procesado_con'] = 'EasyOCR'

                        # Corregir texto
                        texto_corregido = self._corregir_texto(texto_obtenido or '')
                        datos_pdf['paginas'][idx - 1]['texto'] = texto_corregido.strip()

            return datos_pdf

        except Exception as e:
            import traceback
            error_detalle = traceback.format_exc()
            print(f"ERROR en procesar_pdf: {error_detalle}")
            return {'exito': False, 'error': f"Error PDF: {str(e)}", 'detalle': error_detalle}

    def procesar_archivo(self, ruta_archivo: str) -> Dict:
        """
        Procesa cualquier archivo soportado automáticamente

        Args:
            ruta_archivo: Ruta del archivo a procesar

        Returns:
            Dict con datos procesados
        """
        # Validar archivo
        es_valido, mensaje = self.validar_archivo(ruta_archivo)
        if not es_valido:
            return {'exito': False, 'error': mensaje}

        ext = Path(ruta_archivo).suffix.lower()

        print(f"Procesando: {Path(ruta_archivo).name}")

        if ext == '.pdf':
            return self.procesar_pdf(ruta_archivo)
        elif ext in {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp'}:
            return self.procesar_imagen(ruta_archivo)
        else:
            return {'exito': False, 'error': f'Tipo de archivo no reconocido: {ext}'}
