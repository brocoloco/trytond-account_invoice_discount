from decimal import Decimal
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.config import config as config_
from trytond.modules.product import price_digits

__all__ = ['InvoiceLine']
__metaclass__ = PoolMeta

STATES = {
    'invisible': Eval('type') != 'line',
    'required': Eval('type') == 'line',
    }
DEPENDS = ['type']
DISCOUNT_DIGITS = config_.getint('product', 'discount_decimal', default=4)


class InvoiceLine:
    __name__ = 'account.invoice.line'

    gross_unit_price = fields.Numeric('Gross Price', digits=price_digits,
        states=STATES, depends=DEPENDS)
    gross_unit_price_wo_round = fields.Numeric('Gross Price without rounding',
        digits=(16, price_digits[1] + DISCOUNT_DIGITS), readonly=True)
    discount = fields.Numeric('Discount', digits=(16, DISCOUNT_DIGITS),
        states=STATES, depends=DEPENDS)

    @classmethod
    def __setup__(cls):
        super(InvoiceLine, cls).__setup__()
        cls.unit_price.states['readonly'] = True
        cls.unit_price.digits = (20, price_digits[1] + DISCOUNT_DIGITS)
        if 'discount' not in cls.amount.on_change_with:
            cls.amount.on_change_with.add('discount')
        if 'gross_unit_price' not in cls.amount.on_change_with:
            cls.amount.on_change_with.add('gross_unit_price')

    @staticmethod
    def default_discount():
        return Decimal(0)

    def update_prices(self):
        unit_price = self.unit_price
        digits = self.__class__.gross_unit_price.digits[1]
        gross_unit_price = gross_unit_price_wo_round = self.gross_unit_price

        if self.gross_unit_price is not None and self.discount is not None:
            unit_price = self.gross_unit_price * (1 - self.discount)
            digits = self.__class__.unit_price.digits[1]
            unit_price = unit_price.quantize(Decimal(str(10.0 ** -digits)))

            if self.discount != 1:
                gross_unit_price_wo_round = unit_price / (1 - self.discount)
            gross_unit_price = gross_unit_price_wo_round.quantize(
                Decimal(str(10.0 ** -digits)))
        elif self.unit_price and self.discount:
            gross_unit_price_wo_round = self.unit_price / (1 - self.discount)
            gross_unit_price = gross_unit_price_wo_round.quantize(
                Decimal(str(10.0 ** -digits)))

        self.gross_unit_price = gross_unit_price
        self.gross_unit_price_wo_round = gross_unit_price_wo_round
        self.unit_price = unit_price

    @fields.depends('gross_unit_price', 'discount', 'unit_price')
    def on_change_gross_unit_price(self):
        return self.update_prices()

    @fields.depends('gross_unit_price', 'discount', 'unit_price')
    def on_change_discount(self):
        return self.update_prices()

    @fields.depends('gross_unit_price', 'unit_price', 'discount')
    def on_change_product(self):
        super(InvoiceLine, self).on_change_product()
        if self.unit_price:
            self.gross_unit_price = self.unit_price
            self.discount = Decimal(0)
            self.update_prices()
        if not self.discount:
            self.discount = Decimal(0)

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for vals in vlist:
            if vals.get('type') != 'line':
                continue
            gross_unit_price = (vals.get('unit_price', Decimal('0.0'))
                or Decimal('0.0'))
            if 'discount' in vals and vals['discount'] != 1:
                gross_unit_price = gross_unit_price / (1 - vals['discount'])
                digits = cls.gross_unit_price.digits[1]
                gross_unit_price = gross_unit_price.quantize(
                    Decimal(str(10.0 ** -digits)))
            vals['gross_unit_price'] = gross_unit_price
            if 'discount' not in vals:
                vals['discount'] = Decimal(0)
        return super(InvoiceLine, cls).create(vlist)

    def _credit(self):
        res = super(InvoiceLine, self)._credit()
        for field in ('gross_unit_price', 'discount'):
            res[field] = getattr(self, field)
        return res
