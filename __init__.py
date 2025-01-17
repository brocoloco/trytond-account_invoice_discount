# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import commission
from . import invoice
from . import sale

def register():
    Pool.register(
        invoice.InvoiceLine,
        module='account_invoice_discount', type_='model')
    Pool.register(
        commission.Commission,
        depends=['commission'],
        module='account_invoice_discount', type_='model')
    Pool.register(
        sale.Line,
        depends=['sale_discount'],
        module='account_invoice_discount', type_='model')
