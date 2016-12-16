from decimal import Decimal
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.config import config as config_
from trytond.modules.product import price_digits

__all__ = ['InvoiceLine', 'discount_digits']

STATES = {
    'invisible': Eval('type') != 'line',
    'required': Eval('type') == 'line',
    'readonly': Eval('invoice_state') != 'draft',
    }
DEPENDS = ['type', 'invoice_state']
discount_digits = (16, config_.getint('product', 'discount_decimal',
    default=4))


class InvoiceLine:
    __metaclass__ = PoolMeta
    __name__ = 'account.invoice.line'

    gross_unit_price = fields.Function(fields.Numeric('Gross Price',
            digits=price_digits, states=STATES, depends=DEPENDS),
        'on_change_with_gross_unit_price', setter='set_gross_unit_price')
    discount = fields.Numeric('Discount', digits=discount_digits,
        states=STATES, depends=DEPENDS)

    @classmethod
    def __setup__(cls):
        super(InvoiceLine, cls).__setup__()
        cls.unit_price.digits = (20, price_digits[1] + discount_digits[1])
        if 'discount' not in cls.amount.on_change_with:
            cls.amount.on_change_with.add('discount')
        if 'gross_unit_price' not in cls.amount.on_change_with:
            cls.amount.on_change_with.add('gross_unit_price')

    @staticmethod
    def default_discount():
        return Decimal(0)

    @fields.depends('gross_unit_price', 'unit_price', 'discount')
    def on_change_with_gross_unit_price(self, name=None):
        digits = self.__class__.gross_unit_price.digits[1]
        if self.discount == Decimal(1):
            return Decimal(0)
        if self.unit_price:
            discount = self.discount or Decimal(0)
            gross_unit_price = self.unit_price / (1 - discount)
            gross_unit_price = gross_unit_price.quantize(
                Decimal(str(10.0 ** -digits)))
            return gross_unit_price
        # If no discount nor unit price return current_value or unit_price
        return self.gross_unit_price or self.unit_price

    @classmethod
    def set_gross_unit_price(cls, lines, name, gross_unit_price):
        for line in lines:
            line.set_unit_price_from_gross_unit_price(gross_unit_price)
        cls.save(lines)

    def set_unit_price_from_gross_unit_price(self, gross_unit_price):
        unit_price = self.unit_price
        if gross_unit_price is not None and self.discount is not None:
            unit_price = gross_unit_price * (1 - self.discount)
            digits = self.__class__.unit_price.digits[1]
            unit_price = unit_price.quantize(Decimal(str(10.0 ** -digits)))
        # Ony trigger the change if it has really changed
        if unit_price != self.unit_price:
            self.unit_price = unit_price

    @fields.depends('gross_unit_price', 'discount', 'unit_price')
    def on_change_gross_unit_price(self):
        self.set_unit_price_from_gross_unit_price(self.gross_unit_price)

    @fields.depends('gross_unit_price', 'discount', 'unit_price')
    def on_change_discount(self):
        self.set_unit_price_from_gross_unit_price(self.gross_unit_price)

    def _credit(self):
        line = super(InvoiceLine, self)._credit()
        line.discount = self.discount
        return line
