"""
Módulo de estructura de factura
Define la estructura estándar de una factura para exportación a Excel y Base de Datos
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class ItemFactura:
    """Estructura de un item/producto en la factura"""
    codigo: str = ""
    descripcion: str = ""
    cantidad: float = 0.0
    unidad: str = "UND"
    precio_unitario: float = 0.0
    subtotal: float = 0.0
    descuento: float = 0.0
    impuesto: float = 0.0
    total: float = 0.0

    def calcular_total(self):
        """Calcula el total del item"""
        self.subtotal = self.cantidad * self.precio_unitario
        self.total = self.subtotal - self.descuento + self.impuesto


@dataclass
class EmpresaInfo:
    """Información de empresa (proveedor o cliente)"""
    nombre: str = ""
    ruc: str = ""
    direccion: str = ""
    telefono: str = ""
    email: str = ""
    ciudad: str = ""
    pais: str = ""


@dataclass
class Factura:
    """Estructura completa de una factura"""
    # Identificación
    numero_factura: str = ""
    fecha_emision: str = ""
    fecha_vencimiento: str = ""
    tipo_factura: str = "FACTURA"  # FACTURA, BOLETA, NOTA_CREDITO, etc.

    # Detalle principal
    concepto: str = ""
    cantidad_detalle: float = 0.0
    precio_unitario: float = 0.0

    # Proveedor
    proveedor: EmpresaInfo = field(default_factory=EmpresaInfo)

    # Cliente
    cliente: EmpresaInfo = field(default_factory=EmpresaInfo)

    # Items de la factura
    items: List[ItemFactura] = field(default_factory=list)

    # Totales
    subtotal: float = 0.0
    descuento_global: float = 0.0
    subtotal_con_descuento: float = 0.0
    igv: float = 0.0
    impuesto_adicional: float = 0.0
    total: float = 0.0

    # Información adicional
    moneda: str = "PEN"  # PEN, USD, EUR
    tipo_cambio: float = 1.0
    forma_pago: str = ""
    observaciones: str = ""
    terminos_condiciones: str = ""

    # Metadatos
    fecha_procesamiento: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    archivo_origen: str = ""
    confianza_ocr: float = 0.0

    def agregar_item(self, item: ItemFactura):
        """Agrega un item a la factura"""
        self.items.append(item)
        self.recalcular_totales()

    def recalcular_totales(self):
        """Recalcula los totales de la factura"""
        self.subtotal = sum(item.subtotal for item in self.items)
        self.subtotal_con_descuento = self.subtotal - self.descuento_global
        self.total = self.subtotal_con_descuento + self.igv + self.impuesto_adicional

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la factura a diccionario"""
        return asdict(self)

    def to_dict_plano(self) -> Dict[str, Any]:
        """
        Convierte la factura a diccionario plano (para Excel simple)
        Sin objetos anidados
        """
        return {
            # Identificación
            'numero_factura': self.numero_factura,
            'fecha': self.fecha_emision,
            'fecha_emision': self.fecha_emision,
            'fecha_vencimiento': self.fecha_vencimiento,
            'tipo_factura': self.tipo_factura,

            # Detalle principal
            'concepto': self.concepto,
            'cantidad_detalle': self.cantidad_detalle,
            'precio_unitario': self.precio_unitario,

            # Proveedor
            'empresa_proveedor': self.proveedor.nombre,
            'ruc_empresa': self.proveedor.ruc,
            'direccion_empresa': self.proveedor.direccion,
            'telefono_empresa': self.proveedor.telefono,
            'email_empresa': self.proveedor.email,

            # Cliente
            'cliente_nombre': self.cliente.nombre,
            'cliente_ruc': self.cliente.ruc,
            'cliente_direccion': self.cliente.direccion,

            # Totales
            'subtotal': self.subtotal,
            'descuento': self.descuento_global,
            'igv': self.igv,
            'monto_total': self.total,

            # Items
            'cantidad_items': len(self.items),
            'items': [asdict(item) for item in self.items],

            # Adicional
            'moneda': self.moneda,
            'forma_pago': self.forma_pago,
            'observaciones': self.observaciones,

            # Metadatos
            'fecha_procesamiento': self.fecha_procesamiento,
            'archivo_origen': self.archivo_origen,
        }

    @staticmethod
    def _a_float(valor: Any) -> float:
        """Convierte strings con separadores de miles a float."""
        if valor in (None, ""):
            return 0.0

        if isinstance(valor, (int, float)):
            return float(valor)

        texto = str(valor).strip()
        texto = texto.replace("S/", "").replace("$", "").replace(" ", "")

        if "," in texto and "." in texto:
            if texto.rfind(",") > texto.rfind("."):
                texto = texto.replace(".", "").replace(",", ".")
            else:
                texto = texto.replace(",", "")
        else:
            texto = texto.replace(",", ".")

        try:
            return float(texto)
        except ValueError:
            return 0.0

    @classmethod
    def desde_dict(cls, data: Dict[str, Any]) -> 'Factura':
        """
        Crea una instancia de Factura desde un diccionario

        Args:
            data: Diccionario con datos de la factura

        Returns:
            Instancia de Factura
        """
        factura = cls()

        # Mapear campos directos
        factura.numero_factura = data.get('numero_factura', '')
        factura.fecha_emision = data.get('fecha', data.get('fecha_emision', ''))
        factura.fecha_vencimiento = data.get('fecha_vencimiento', '')
        factura.tipo_factura = data.get('tipo_factura', 'FACTURA')

        factura.concepto = data.get('concepto', '')
        factura.cantidad_detalle = cls._a_float(data.get('cantidad', data.get('cantidad_detalle', 0)))
        factura.precio_unitario = cls._a_float(data.get('precio_unitario', 0))

        # Proveedor
        factura.proveedor.nombre = data.get('empresa', data.get('empresa_proveedor', ''))
        factura.proveedor.ruc = data.get('ruc', data.get('ruc_empresa', ''))
        factura.proveedor.direccion = data.get('direccion_empresa', data.get('direccion', ''))
        factura.proveedor.telefono = data.get('telefono', data.get('telefono_empresa', ''))
        factura.proveedor.email = data.get('email', data.get('email_empresa', ''))

        # Cliente
        factura.cliente.nombre = data.get('cliente_nombre', data.get('cliente', ''))
        factura.cliente.ruc = data.get('cliente_ruc', '')
        factura.cliente.direccion = data.get('cliente_direccion', '')

        # Totales
        factura.subtotal = cls._a_float(data.get('subtotal', 0))
        factura.igv = cls._a_float(data.get('igv', 0))
        factura.total = cls._a_float(data.get('total', data.get('monto_total', 0)))

        # Items (si existen)
        if 'items' in data and isinstance(data['items'], list):
            for item_data in data['items']:
                item = ItemFactura(**item_data)
                factura.items.append(item)
        elif factura.concepto or factura.cantidad_detalle or factura.precio_unitario:
            item = ItemFactura(
                descripcion=factura.concepto,
                cantidad=factura.cantidad_detalle or 1.0,
                precio_unitario=factura.precio_unitario,
                subtotal=factura.subtotal,
                impuesto=factura.igv,
                total=factura.total,
            )
            if not item.subtotal and item.cantidad and item.precio_unitario:
                item.calcular_total()
            factura.items.append(item)

        # Metadatos
        factura.archivo_origen = data.get('archivo_origen', '')
        factura.fecha_procesamiento = data.get('fecha_procesamiento', 
                                               datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        return factura

    def validar(self) -> tuple[bool, List[str]]:
        """
        Valida que la factura tenga los campos obligatorios

        Returns:
            Tupla (es_valida, lista_errores)
        """
        errores = []

        if not self.numero_factura:
            errores.append("Falta número de factura")

        if not self.fecha_emision:
            errores.append("Falta fecha de emisión")

        if not self.proveedor.nombre:
            errores.append("Falta nombre del proveedor")

        if self.total <= 0:
            errores.append("El total debe ser mayor a 0")

        return (len(errores) == 0, errores)


class FacturaBuilder:
    """Constructor de facturas para facilitar la creación"""

    def __init__(self):
        self.factura = Factura()

    def con_numero(self, numero: str) -> 'FacturaBuilder':
        self.factura.numero_factura = numero
        return self

    def con_fecha(self, fecha: str) -> 'FacturaBuilder':
        self.factura.fecha_emision = fecha
        return self

    def con_proveedor(self, nombre: str, ruc: str = "", **kwargs) -> 'FacturaBuilder':
        self.factura.proveedor.nombre = nombre
        self.factura.proveedor.ruc = ruc
        for key, value in kwargs.items():
            if hasattr(self.factura.proveedor, key):
                setattr(self.factura.proveedor, key, value)
        return self

    def con_totales(self, subtotal: float, igv: float, total: float) -> 'FacturaBuilder':
        self.factura.subtotal = subtotal
        self.factura.igv = igv
        self.factura.total = total
        return self

    def agregar_item(self, codigo: str, descripcion: str, cantidad: float, 
                     precio: float) -> 'FacturaBuilder':
        item = ItemFactura(
            codigo=codigo,
            descripcion=descripcion,
            cantidad=cantidad,
            precio_unitario=precio
        )
        item.calcular_total()
        self.factura.agregar_item(item)
        return self

    def build(self) -> Factura:
        return self.factura
