================
Invoice Scenario
================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install account_invoice::

    >>> Module = Model.get('ir.module.module')
    >>> account_invoice_module, = Module.find(
    ...     [('name', '=', 'account_invoice_discount')])
    >>> Module.install([account_invoice_module.id], config.context)
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='US Dollar', symbol=u'$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[]',
    ...         mon_decimal_point='.')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find([])

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create fiscal year::

    >>> FiscalYear = Model.get('account.fiscalyear')
    >>> Sequence = Model.get('ir.sequence')
    >>> SequenceStrict = Model.get('ir.sequence.strict')
    >>> fiscalyear = FiscalYear(name=str(today.year))
    >>> fiscalyear.start_date = today + relativedelta(month=1, day=1)
    >>> fiscalyear.end_date = today + relativedelta(month=12, day=31)
    >>> fiscalyear.company = company
    >>> post_move_seq = Sequence(name=str(today.year), code='account.move',
    ...     company=company)
    >>> post_move_seq.save()
    >>> fiscalyear.post_move_sequence = post_move_seq
    >>> invoice_seq = SequenceStrict(name=str(today.year),
    ...     code='account.invoice', company=company)
    >>> invoice_seq.save()
    >>> fiscalyear.out_invoice_sequence = invoice_seq
    >>> fiscalyear.in_invoice_sequence = invoice_seq
    >>> fiscalyear.out_credit_note_sequence = invoice_seq
    >>> fiscalyear.in_credit_note_sequence = invoice_seq
    >>> fiscalyear.save()
    >>> FiscalYear.create_period([fiscalyear.id], config.context)

Create chart of accounts::

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> revenue, = Account.find([
    ...         ('kind', '=', 'revenue'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> expense, = Account.find([
    ...         ('kind', '=', 'expense'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> account_tax, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('company', '=', company.id),
    ...         ('name', '=', 'Main Tax'),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')

Create tax::

    >>> TaxCode = Model.get('account.tax.code')
    >>> Tax = Model.get('account.tax')
    >>> tax = Tax()
    >>> tax.name = 'Tax'
    >>> tax.description = 'Tax'
    >>> tax.type = 'percentage'
    >>> tax.rate = Decimal('.10')
    >>> tax.invoice_account = account_tax
    >>> tax.credit_note_account = account_tax
    >>> invoice_base_code = TaxCode(name='invoice base')
    >>> invoice_base_code.save()
    >>> tax.invoice_base_code = invoice_base_code
    >>> invoice_tax_code = TaxCode(name='invoice tax')
    >>> invoice_tax_code.save()
    >>> tax.invoice_tax_code = invoice_tax_code
    >>> credit_note_base_code = TaxCode(name='credit note base')
    >>> credit_note_base_code.save()
    >>> tax.credit_note_base_code = credit_note_base_code
    >>> credit_note_tax_code = TaxCode(name='credit note tax')
    >>> credit_note_tax_code.save()
    >>> tax.credit_note_tax_code = credit_note_tax_code
    >>> tax.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.list_price = Decimal('20')
    >>> template.cost_price = Decimal('12')
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.customer_taxes.append(tax)
    >>> template.save()
    >>> product.template = template
    >>> product.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> PaymentTermLine = Model.get('account.invoice.payment_term.line')
    >>> payment_term = PaymentTerm(name='Term')
    >>> payment_term_line = PaymentTermLine(type='percent', days=20,
    ...     percentage=Decimal(50))
    >>> payment_term.lines.append(payment_term_line)
    >>> payment_term_line = PaymentTermLine(type='remainder', days=40)
    >>> payment_term.lines.append(payment_term_line)
    >>> payment_term.save()

Create invoice::

    >>> Invoice = Model.get('account.invoice')
    >>> InvoiceLine = Model.get('account.invoice.line')
    >>> invoice = Invoice()
    >>> invoice.party = party
    >>> invoice.payment_term = payment_term

Add line defining Gross Unit Price and Discount (Unit Price is calculated)::

    >>> line = InvoiceLine()
    >>> invoice.lines.append(line)
    >>> line.account = revenue
    >>> line.description = 'Test'
    >>> line.quantity = 1
    >>> line.discount = Decimal('0.2577')
    >>> line.gross_unit_price = Decimal('25.153')
    >>> line.unit_price
    Decimal('18.67107190')
    >>> line.amount
    Decimal('18.67')

Add line defining Unit Price and Discount, Gross Unit Price is calculated::

    >>> line = InvoiceLine()
    >>> invoice.lines.append(line)
    >>> line.product = product
    >>> line.quantity = 5
    >>> line.unit_price = Decimal('17.60')
    >>> line.discount = Decimal('0.12')
    >>> line.gross_unit_price
    Decimal('20.0000')
    >>> line.amount
    Decimal('88.00')

Add line defining a discount of 100%. Despite of the List Price of product,
after set the Discount the Unit Price is recomputed to 0.::

    >>> line = InvoiceLine()
    >>> invoice.lines.append(line)
    >>> line.product = product
    >>> line.quantity = 2
    >>> line.unit_price
    Decimal('20.00000000')
    >>> line.gross_unit_price = Decimal('25.153')
    >>> line.discount = Decimal('1.0')
    >>> line.unit_price == Decimal('0.00')
    True
    >>> line.amount
    Decimal('0.00')

Check invoice totals::

    >>> invoice.untaxed_amount
    Decimal('106.67')
    >>> invoice.tax_amount
    Decimal('8.80')
    >>> invoice.total_amount
    Decimal('115.47')
    >>> invoice.save()
    >>> lines_by_qty = {int(l.quantity): l for l in invoice.lines}
    >>> lines_by_qty[1].amount
    Decimal('18.67')
    >>> lines_by_qty[5].amount
    Decimal('88.00')
    >>> lines_by_qty[2].amount
    Decimal('0.00')

Applying global invoice discount::

    >>> invoice_discount = Wizard('account.invoice.apply_invoice_discount',
    ...     [invoice])
    >>> invoice_discount.form.discount = Decimal('0.15')
    >>> invoice_discount.execute('apply_discount')
    >>> invoice.reload()
    >>> invoice.untaxed_amount
    Decimal('90.67')
    >>> invoice.tax_amount
    Decimal('7.48')
    >>> invoice.total_amount
    Decimal('98.15')
    >>> lines_by_qty[1].reload()
    >>> lines_by_qty[1].amount
    Decimal('15.87')
    >>> lines_by_qty[5].reload()
    >>> lines_by_qty[5].amount
    Decimal('74.80')
    >>> lines_by_qty[2].reload()
    >>> lines_by_qty[2].amount
    Decimal('0.00')

Remove global invoice discount::

    >>> invoice_discount = Wizard('account.invoice.apply_invoice_discount',
    ...     [invoice])
    >>> invoice_discount.form.discount = Decimal(0)
    >>> invoice_discount.execute('apply_discount')
    >>> invoice.reload()
    >>> invoice.untaxed_amount
    Decimal('106.67')
    >>> invoice.tax_amount
    Decimal('8.80')
    >>> invoice.total_amount
    Decimal('115.47')
    >>> lines_by_qty[1].reload()
    >>> lines_by_qty[1].amount
    Decimal('18.67')
    >>> lines_by_qty[5].reload()
    >>> lines_by_qty[5].amount
    Decimal('88.00')
    >>> lines_by_qty[2].reload()
    >>> lines_by_qty[2].amount
    Decimal('0.00')

Applying global invoice discount::

    >>> invoice_discount = Wizard('account.invoice.apply_invoice_discount',
    ...     [invoice])
    >>> invoice_discount.form.discount = Decimal('0.10')
    >>> invoice_discount.execute('apply_discount')
    >>> invoice.reload()
    >>> invoice.untaxed_amount
    Decimal('96.00')
    >>> invoice.tax_amount
    Decimal('7.92')
    >>> invoice.total_amount
    Decimal('103.92')
    >>> lines_by_qty[1].reload()
    >>> lines_by_qty[1].amount
    Decimal('16.80')
    >>> lines_by_qty[5].reload()
    >>> lines_by_qty[5].amount
    Decimal('79.20')
    >>> lines_by_qty[2].reload()
    >>> lines_by_qty[2].amount
    Decimal('0.00')

Post invoice and check again invoice totals and taxes::

    >>> Invoice.post([invoice.id], config.context)
    >>> invoice.reload()
    >>> invoice.state
    u'posted'
    >>> invoice.untaxed_amount
    Decimal('96.00')
    >>> invoice.tax_amount
    Decimal('7.92')
    >>> invoice.total_amount
    Decimal('103.92')
    >>> receivable.reload()
    >>> receivable.debit
    Decimal('103.92')
    >>> receivable.credit
    Decimal('0.00')
    >>> revenue.reload()
    >>> revenue.debit
    Decimal('0.00')
    >>> revenue.credit
    Decimal('96.00')
    >>> account_tax.reload()
    >>> account_tax.debit
    Decimal('0.00')
    >>> account_tax.credit
    Decimal('7.92')
    >>> invoice_base_code.reload()
    >>> invoice_base_code.sum
    Decimal('79.20')
    >>> invoice_tax_code.reload()
    >>> invoice_tax_code.sum
    Decimal('7.92')
    >>> credit_note_base_code.reload()
    >>> credit_note_base_code.sum
    Decimal('0.00')
    >>> credit_note_tax_code.reload()
    >>> credit_note_tax_code.sum
    Decimal('0.00')
