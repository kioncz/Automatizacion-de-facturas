"""
Módulo de corrección de detección OCR
Corrige palabras mal detectadas por EasyOCR
"""

from typing import Dict, List
import re


class CorrectorDeteccion:
    """Corrige palabras mal detectadas por OCR"""

    def __init__(self):
        # Diccionario de correcciones comunes
        self.correcciones = {
            # Palabras comunes en facturas
            'factura': ['factur4', 'f4ctura', 'factur@', 'faetura', 'factur'],
            'numero': ['num3ro', 'numer0', 'nurnero', 'num', 'n°'],
            'fecha': ['f3cha', 'fech@', 'feche', 'fech'],
            'total': ['tot4l', 't0tal', 'totai', 'totaI', 'tota1'],
            'subtotal': ['subt0tal', 'sub-total', 'sub total', 'subtotai'],
            'igv': ['1gv', 'lgv', 'igv:', 'i.g.v', 'i.g.v.'],
            'iva': ['1va', 'lva', 'iva:', 'i.v.a', 'i.v.a.'],
            'ruc': ['ruc:', 'r.u.c', 'r.u.c.', 'rue'],
            'empresa': ['empres4', 'ernpresa', 'empr3sa'],
            'proveedor': ['prove3dor', 'proveed0r', 'provedor'],
            'cliente': ['cli3nte', 'client3', 'cllente'],
            'direccion': ['direcci0n', 'direcci6n', 'direccion:'],
            'telefono': ['tel3fono', 'telefon0', 'telf', 'tel.'],
            'email': ['em4il', 'e-mail', 'correo'],
            'cantidad': ['c4ntidad', 'cantid4d', 'cant', 'cant.'],
            'precio': ['preci0', 'pr3cio', 'precio.'],
            'descuento': ['descuent0', 'd3scuento', 'desc', 'desc.'],
            'producto': ['product0', 'pr0ducto', 'prod', 'prod.'],
            'servicio': ['servici0', 's3rvicio', 'serv', 'serv.'],
            'descripcion': ['descripci0n', 'descripc16n', 'desc'],
            'codigo': ['c0digo', 'c6digo', 'cod', 'cod.'],
            'unidad': ['unid4d', 'unid', 'und', 'ud'],
            'importe': ['import3', 'imp0rte', 'imp', 'imp.'],
            'moneda': ['mon3da', 'moned4', 'mon'],
            'metodo': ['met0do', 'm3todo'],
            'pago': ['p4go', 'pag0'],
            'banco': ['b4nco', 'banc0'],
            'cuenta': ['cuent4', 'cu3nta', 'cta', 'cta.'],
            'observaciones': ['observaci0nes', 'observac1ones', 'obs', 'obs.'],
        }

        # Crear diccionario inverso para búsqueda rápida
        self.mapa_correcciones = {}
        for correcta, errores in self.correcciones.items():
            for error in errores:
                self.mapa_correcciones[error.lower()] = correcta

    def corregir_palabra(self, palabra: str) -> str:
        """
        Corrige una palabra individual

        Args:
            palabra: Palabra a corregir

        Returns:
            Palabra corregida o la original si no hay corrección
        """
        palabra_limpia = palabra.lower().strip()

        # Buscar corrección exacta
        if palabra_limpia in self.mapa_correcciones:
            return self.mapa_correcciones[palabra_limpia]

        return palabra

    def corregir_texto(self, texto: str) -> str:
        """
        Corrige un texto completo palabra por palabra

        Args:
            texto: Texto completo a corregir

        Returns:
            Texto corregido
        """
        def reemplazar_palabra(match):
            palabra = match.group(0)
            if palabra.isalnum():
                return self.corregir_palabra(palabra)
            return palabra

        return re.sub(r'\b\w+\b', reemplazar_palabra, texto)

    def corregir_linea(self, linea: str) -> str:
        """
        Corrige una línea de texto

        Args:
            linea: Línea a corregir

        Returns:
            Línea corregida
        """
        return self.corregir_texto(linea)

    def agregar_correccion(self, correcta: str, errores: List[str]):
        """
        Agrega una nueva corrección al diccionario

        Args:
            correcta: Palabra correcta
            errores: Lista de variantes incorrectas
        """
        if correcta not in self.correcciones:
            self.correcciones[correcta] = []

        self.correcciones[correcta].extend(errores)

        # Actualizar mapa
        for error in errores:
            self.mapa_correcciones[error.lower()] = correcta

    def obtener_estadisticas(self, texto_original: str, texto_corregido: str) -> Dict:
        """
        Obtiene estadísticas de corrección

        Args:
            texto_original: Texto antes de corregir
            texto_corregido: Texto después de corregir

        Returns:
            Diccionario con estadísticas
        """
        palabras_original = texto_original.split()
        palabras_corregido = texto_corregido.split()

        correcciones_realizadas = 0
        for orig, corr in zip(palabras_original, palabras_corregido):
            if orig.lower() != corr.lower():
                correcciones_realizadas += 1

        return {
            'total_palabras': len(palabras_original),
            'palabras_corregidas': correcciones_realizadas,
            'porcentaje_correccion': (correcciones_realizadas / len(palabras_original) * 100) if palabras_original else 0
        }


# Función de conveniencia para uso rápido
def corregir_texto_ocr(texto: str) -> str:
    """
    Función rápida para corregir texto OCR

    Args:
        texto: Texto a corregir

    Returns:
        Texto corregido
    """
    corrector = CorrectorDeteccion()
    return corrector.corregir_texto(texto)
