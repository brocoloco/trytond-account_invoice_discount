# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, StateTransition, Button

from trytond.config import config
DIGITS = int(config.get('digits', 'unit_price_digits', 4))
DISCOUNT_DIGITS = int(config.get('digits', 'discount_digits', 4))

__all__ = ['InvoiceLine', 'ApplyInvoiceDiscountStart', 'ApplyInvoiceDiscount']
__metaclass__ = PoolMeta

STATES = {
    'invisible': Eval('type') != 'line',
    'required': Eval('type') == 'line',
    }


class InvoiceLine:
    __name__ = 'account.invoice.line'

    gross_unit_price = fields.Numeric('Gross Price', digits=(16, DIGITS),
        states=STATES)
    gross_unit_price_wo_round = fields.Numeric('Gross Price without rounding',
        digits=(16, DIGITS + DISCOUNT_DIGITS), readonly=True)
    discount = fields.Numeric('Discount', digits=(16, DISCOUNT_DIGITS),
        states=STATES)
    invoice_discount = fields.Numeric('Invoice Discount',
        digits=(16, DISCOUNT_DIGITS))

    @classmethod
    def __setup__(cls):
        super(InvoiceLine, cls).__setup__()
        cls.unit_price.states['readonly'] = True
        cls.unit_price.digits = (20, DIGITS + DISCOUNT_DIGITS)
        if 'discount' not in cls.amount.on_change_with:
            cls.amount.on_change_with.add('discount')
        if 'invoice_discount' not in cls.amount.on_change_with:
            cls.amount.on_change_with.add('invoice_discount')
        if 'gross_unit_price' not in cls.amount.on_change_with:
            cls.amount.on_change_with.add('gross_unit_price')

    @staticmethod
    def default_discount():
        return Decimal(0)

    def update_prices(self):
        unit_price = None
        gross_unit_price = gross_unit_price_wo_round = self.gross_unit_price
        if self.gross_unit_price is not None and (self.discount is not None
                or self.invoice_discount is not None):
            unit_price = self.gross_unit_price
            if self.discount:
                unit_price *= (1 - self.discount)
            if self.invoice_discount:
                unit_price *= (1 - self.invoice_discount)

            if self.discount and self.invoice_discount:
                discount = (self.discount + self.invoice_discount
                    - self.discount * self.invoice_discount)
                if discount != 1:
                    gross_unit_price_wo_round = (
                        unit_price / (1 - discount))
            elif self.discount and self.discount != 1:
                gross_unit_price_wo_round = (
                    unit_price / (1 - self.discount))
            elif self.invoice_discount and self.invoice_discount != 1:
                gross_unit_price_wo_round = (
                    unit_price / (1 - self.invoice_discount))

            digits = self.__class__.unit_price.digits[1]
            unit_price = unit_price.quantize(Decimal(str(10.0 ** -digits)))

            digits = self.__class__.gross_unit_price.digits[1]
            gross_unit_price = gross_unit_price_wo_round.quantize(
                Decimal(str(10.0 ** -digits)))
        return {
            'gross_unit_price': gross_unit_price,
            'gross_unit_price_wo_round': gross_unit_price_wo_round,
            'unit_price': unit_price,
            }

    @fields.depends('gross_unit_price', 'discount', 'invoice_discount')
    def on_change_gross_unit_price(self):
        return self.update_prices()

    @fields.depends('gross_unit_price', 'discount', 'invoice_discount')
    def on_change_discount(self):
        return self.update_prices()

    @fields.depends('discount', 'invoice_discount')
    def on_change_product(self):
        res = super(InvoiceLine, self).on_change_product()
        if 'unit_price' in res:
            self.gross_unit_price = res['unit_price']
            self.discount = Decimal(0)
            res.update(self.update_prices())
        if 'discount' not in res:
            res['discount'] = Decimal(0)
        return res

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for vals in vlist:
            if vals.get('type') != 'line':
                continue
            if vals.get('unit_price') is None:
                vals['gross_unit_price'] = Decimal(0)
                continue

            gross_unit_price = vals['unit_price']
            if vals.get('discount') not in (None, 1):
                gross_unit_price = gross_unit_price / (1 - vals['discount'])
            if vals.get('invoice_discount') not in (None, 1):
                gross_unit_price = (gross_unit_price
                    / (1 - vals['invoice_discount']))
            if gross_unit_price != vals['unit_price']:
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


class ApplyInvoiceDiscountStart(ModelView):
    'Apply Invoice Discount'
    __name__ = 'account.invoice.apply_invoice_discount.start'
    discount = fields.Numeric("Invoice's Global Discount",
        digits=(16, DISCOUNT_DIGITS), required=True)


class ApplyInvoiceDiscount(Wizard):
    'Apply Invoice Discount'
    __name__ = 'account.invoice.apply_invoice_discount'
    start = StateView('account.invoice.apply_invoice_discount.start',
        'account_invoice_discount.apply_invoice_discount_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Apply', 'apply_discount', 'tryton-ok', default=True),
            ])
    apply_discount = StateTransition()

    @classmethod
    def __setup__(cls):
        super(ApplyInvoiceDiscount, cls).__setup__()
        cls._error_messages.update({
                'invalid_invoice_sate': (
                    'You cannot change the applied discount to invoice "%s" '
                    'because it isn\'t in Draft state.'),
                })

    def default_start(self, fields):
        Invoice = Pool().get('account.invoice')
        invoice = Invoice(Transaction().context['active_id'])
        if invoice.state != 'draft':
            self.raise_user_error('invalid_invoice_sate', (invoice.rec_name,))
        return {}

    def transition_apply_discount(self):
        Invoice = Pool().get('account.invoice')
        invoice = Invoice(Transaction().context['active_id'])
        for line in invoice.lines:
            if line.type != 'line':
                continue
            line.invoice_discount = self.start.discount
            prices = line.update_prices()
            line.gross_unit_price = prices['gross_unit_price']
            line.gross_unit_price_wo_round = (
                prices['gross_unit_price_wo_round'])
            line.unit_price = prices['unit_price']
            line.save()
        Invoice.update_taxes([invoice], exception=False)
        return 'end'
