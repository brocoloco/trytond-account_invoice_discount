from decimal import Decimal

from trytond.model import fields
from trytond.pool import PoolMeta


class Line(metaclass=PoolMeta):
    __name__ = 'sale.line'

    def get_invoice_line(self):
        'Return a list of invoice lines for sale line'
        # Populate invoice discount fields if sale_discount is installed
        # Note there is no checking done here as this class is enabled at the config level
        # when the module sale_discount is enabled
        lines = super().get_invoice_line()
        if lines:
            line = lines[0]
            line.gross_unit_price = self.base_price
            if self.discount_rate:
                line.discount = self.discount_rate
            else:
                line.discount = Decimal(0)
        return lines

    @fields.depends(methods=['compute_unit_price'])
    def compute_base_price(self):
        value = self.compute_unit_price()
        return value
