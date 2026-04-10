"""
Módulo extractor.py - Extrae datos estructurados de facturas
"""

import re
import unicodedata
from typing import Dict, Any


class ExtractorFacturas:
    """Extrae campos de facturas desde texto OCR"""

    def __init__(self):
        self.patrones = {
            'numero_factura': [
                r'numero\s+de\s+factura\s*[:#\-]*\s*([a-z0-9\-\/]+)',
                r'num(?:ero)?\s+de\s+factura\s*[:#\-]*\s*([a-z0-9\-\/]+)',
                r'nro\s+de\s+factura\s*[:#\-]*\s*([a-z0-9\-\/]+)',
                r'factura\s*(?:n[°o]|no|num|numero)?\s*[:#\-]*\s*([a-z0-9\-\/]+)',
            ],
            'fecha_emision': [
                r'fecha\s+de\s+emision\s*[:\-]*\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                r'(?:fecha|date)\s*[:\-]*\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            ],
            'fecha_vencimiento': [
                r'fecha\s+de\s+vencimiento\s*[:\-]*\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                r'vencimiento\s*[:\-]*\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            ],
            'ruc_empresa': [
                r'datos\s+del\s+proveedor.*?ruc\s*[:\-]*\s*([0-9]{8,15})',
                r'proveedor.*?ruc\s*[:\-]*\s*([0-9]{8,15})',
                r'ruc\s*[:\-]*\s*([0-9]{8,15})',
            ],
            'empresa_proveedor': [
                r'datos\s+del\s+proveedor.*?empresa\s*[:\-]*\s*(.+?)(?=\s+(?:ruc|direccion|domicilio|telefono|email)\b|$)',
                r'proveedor.*?empresa\s*[:\-]*\s*(.+?)(?=\s+(?:ruc|direccion|domicilio|telefono|email)\b|$)',
                r'empresa\s*[:\-]*\s*(.+?)(?=\s+(?:ruc|direccion|domicilio|telefono|email)\b|$)',
            ],
            'cliente_nombre': [
                r'datos\s+del\s+cliente.*?empresa\s*[:\-]*\s*(.+?)(?=\s+(?:ruc|direccion|domicilio|telefono|email)\b|$)',
                r'cliente.*?empresa\s*[:\-]*\s*(.+?)(?=\s+(?:ruc|direccion|domicilio|telefono|email)\b|$)',
            ],
            'cliente_ruc': [
                r'datos\s+del\s+cliente.*?ruc\s*[:\-]*\s*([0-9]{8,15})',
                r'cliente.*?ruc\s*[:\-]*\s*([0-9]{8,15})',
            ],
            'direccion_empresa': [
                r'direccion\s*[:\-]*\s*(.+?)(?=\s+(?:telefono|email|ruc|datos\s+del\s+cliente|detalles|$))',
                r'domicilio\s*[:\-]*\s*(.+?)(?=\s+(?:telefono|email|ruc|datos\s+del\s+cliente|detalles|$))',
            ],
            'concepto': [
                r'concepto\s*[:\-]*\s*(.+?)(?=\s+(?:cantidad|precio\s+unitario|subtotal|igv|total)\b|$)',
            ],
            'cantidad': [
                r'cantidad\s*[:\-]*\s*([0-9]+(?:[\.,][0-9]+)?)',
            ],
            'precio_unitario': [
                r'precio\s+unitario\s*[:\-]*\s*(?:s/?|si|\$)?\s*([0-9][0-9\.,]*)',
            ],
            'subtotal': [
                r'subtotal\s*[:\-]*\s*(?:s/?|si|\$)?\s*([0-9][0-9\.,]*)',
            ],
            'igv': [
                r'igv(?:\s*\([^)]+\))?\s*[:\-]*\s*(?:s/?|si|\$)?\s*([0-9][0-9\.,]*)',
            ],
            'monto_total': [
                r'\btotal\s+a\s+pagar\b\s*[:\-]*\s*(?:s/?|si|\$)?\s*([0-9][0-9\.,]*)',
                r'\btotal\b\s*[:\-]*\s*(?:s/?|si|\$)?\s*([0-9][0-9\.,]*)',
            ],
            'fecha': [
                r'(?:fecha|date)\s*[:\-]*\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            ],
        }

    def _normalizar_texto(self, texto: str) -> str:
        """Normaliza texto OCR para búsqueda sin perder el contenido."""
        if not texto:
            return ""

        texto = texto.replace("�", " ")
        texto = unicodedata.normalize("NFKC", texto)
        texto = texto.replace("\r\n", "\n").replace("\r", "\n")
        texto = re.sub(r"[\t\x0b\x0c]+", " ", texto)
        texto = unicodedata.normalize("NFKD", texto)
        texto = ''.join(caracter for caracter in texto if not unicodedata.combining(caracter))
        texto = texto.lower()
        texto = re.sub(r"\s+", " ", texto)
        return texto.strip()

    def _limpiar_valor(self, valor: str) -> str:
        """Limpia un valor capturado por OCR."""
        if valor is None:
            return ""

        valor = valor.replace("�", " ")
        valor = valor.replace("_", " ")
        valor = re.sub(r"\s+", " ", valor).strip()
        valor = valor.strip(" .,:;-")
        return valor

    def _normalizar_numero(self, valor: str) -> str:
        """Convierte importes con separadores mixtos a formato decimal estándar."""
        valor = self._limpiar_valor(valor)
        valor = re.sub(r"[^0-9,.-]", "", valor)

        if "," in valor and "." in valor:
            if valor.rfind(",") > valor.rfind("."):
                valor = valor.replace(".", "").replace(",", ".")
            else:
                valor = valor.replace(",", "")
        else:
            valor = valor.replace(",", ".")

        return valor

    def _buscar_patron(self, texto: str, patrones: list[str]) -> str:
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return ""

    def _extraer_campo(self, texto: str, patrones: list[str], tipo: str = "texto", fallback: str = "") -> str:
        valor = self._buscar_patron(texto, patrones)
        if not valor:
            return fallback

        if tipo == "numero":
            return self._normalizar_numero(valor)

        return self._limpiar_valor(valor)

    def extraer_numero_factura(self, texto: str) -> str:
        """Extrae numero de factura"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['numero_factura'])
        return self._limpiar_valor(valor) if valor else "NO ENCONTRADO"

    def extraer_fecha(self, texto: str) -> str:
        """Extrae fecha de factura"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['fecha_emision'])
        if valor:
            return valor
        return self._buscar_patron(texto_norm, self.patrones['fecha']) or "NO ENCONTRADO"

    def extraer_fecha_vencimiento(self, texto: str) -> str:
        """Extrae fecha de vencimiento"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['fecha_vencimiento'])
        return valor or "NO ENCONTRADO"

    def extraer_ruc(self, texto: str) -> str:
        """Extrae RUC/NIF"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['ruc_empresa'])
        return self._limpiar_valor(valor) if valor else "NO ENCONTRADO"

    def extraer_empresa(self, texto: str) -> str:
        """Extrae nombre de empresa"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['empresa_proveedor'])
        return self._limpiar_valor(valor) if valor else "NO ENCONTRADO"

    def extraer_cliente(self, texto: str) -> str:
        """Extrae nombre del cliente"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['cliente_nombre'])
        return self._limpiar_valor(valor) if valor else ""

    def extraer_ruc_cliente(self, texto: str) -> str:
        """Extrae RUC del cliente"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['cliente_ruc'])
        return self._limpiar_valor(valor) if valor else ""

    def extraer_direccion_empresa(self, texto: str) -> str:
        """Extrae dirección del proveedor"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['direccion_empresa'])
        return self._limpiar_valor(valor) if valor else ""

    def extraer_concepto(self, texto: str) -> str:
        """Extrae el concepto/descripción principal"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['concepto'])
        return self._limpiar_valor(valor) if valor else ""

    def extraer_cantidad(self, texto: str) -> str:
        """Extrae cantidad de la factura"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['cantidad'])
        return self._limpiar_valor(valor) if valor else ""

    def extraer_precio_unitario(self, texto: str) -> str:
        """Extrae precio unitario"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['precio_unitario'])
        return self._normalizar_numero(valor) if valor else ""

    def extraer_monto_total(self, texto: str) -> str:
        """Extrae monto total"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['monto_total'])
        return self._normalizar_numero(valor) if valor else "0.00"

    def extraer_igv(self, texto: str) -> str:
        """Extrae IGV/IVA"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['igv'])
        return self._normalizar_numero(valor) if valor else "0.00"

    def extraer_subtotal(self, texto: str) -> str:
        """Extrae subtotal"""
        texto_norm = self._normalizar_texto(texto)
        valor = self._buscar_patron(texto_norm, self.patrones['subtotal'])
        return self._normalizar_numero(valor) if valor else "0.00"

    def extraer_email(self, texto: str) -> str:
        """Extrae email"""
        patron = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(patron, texto)
        return match.group(0) if match else ""

    def extraer_telefono(self, texto: str) -> str:
        """Extrae telefono"""
        patron = r'(?:tel|phone|telefono)[\s.:]*([0-9\s\-\+\(\)]{7,})'
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def contar_items(self, texto: str) -> int:
        """Cuenta items en la factura"""
        concepto = self.extraer_concepto(texto)
        cantidad = self.extraer_cantidad(texto)
        precio = self.extraer_precio_unitario(texto)

        if concepto and cantidad and precio:
            return 1

        texto_norm = self._normalizar_texto(texto)
        matches = re.findall(r'\b(?:concepto|descripcion|precio unitario|subtotal|igv)\b', texto_norm)
        return 1 if matches else 0

    def extraer_todos(self, texto: str) -> Dict[str, Any]:
        """
        Extrae todos los campos de la factura
        Retorna diccionario con datos estructurados
        """
        from datetime import datetime
        
        fecha_emision = self.extraer_fecha(texto)
        fecha_vencimiento = self.extraer_fecha_vencimiento(texto)
        empresa = self.extraer_empresa(texto)
        ruc = self.extraer_ruc(texto)
        cliente = self.extraer_cliente(texto)
        cliente_ruc = self.extraer_ruc_cliente(texto)
        direccion_empresa = self.extraer_direccion_empresa(texto)
        concepto = self.extraer_concepto(texto)
        cantidad = self.extraer_cantidad(texto)
        precio_unitario = self.extraer_precio_unitario(texto)
        subtotal = self.extraer_subtotal(texto)
        igv = self.extraer_igv(texto)
        total = self.extraer_monto_total(texto)

        return {
            'numero_factura': self.extraer_numero_factura(texto),
            'fecha': fecha_emision,
            'fecha_emision': fecha_emision,
            'fecha_vencimiento': fecha_vencimiento,
            'empresa': empresa,
            'empresa_proveedor': empresa,
            'ruc': ruc,
            'ruc_empresa': ruc,
            'cliente_nombre': cliente,
            'cliente_ruc': cliente_ruc,
            'direccion_empresa': direccion_empresa,
            'concepto': concepto,
            'cantidad': cantidad,
            'precio_unitario': precio_unitario,
            'subtotal': subtotal,
            'igv': igv,
            'total': total,
            'monto_total': total,
            'email': self.extraer_email(texto),
            'telefono': self.extraer_telefono(texto),
            'cantidad_items': self.contar_items(texto),
            'fecha_procesamiento': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }
