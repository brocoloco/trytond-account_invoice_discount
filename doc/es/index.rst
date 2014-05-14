=====================================================
Facturación. Descuentos en las líneas de las facturas
=====================================================

En las líneas de la factura podemos añadir un valor fijo para aplicar un descuento.

El descuento se aplica en el campo "Precio unidad" a partir del descuento y el
campo "Precio bruto".

Precio = Precio bruto - descuento

Por defecto el número de dígitos del descuento son 4 dígitos. Si desea usar más
número de dígitos en el descuento, en el fichero de configuración de trytond,
puede definir la variable "unit_price_digits" y el número de dígitos. Por ejemplo:

unit_price_digits = 8
