# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .invoice import *


def register():
    Pool.register(
        InvoiceLine,
        ApplyInvoiceDiscountStart,
        module='account_invoice_discount', type_='model')
    Pool.register(
        ApplyInvoiceDiscount,
        module='account_invoice_discount', type_='wizard')
