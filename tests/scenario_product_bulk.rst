========================
Product Bulk Scenario
========================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> today = datetime.date.today()

Install product_bulk module::

    >>> config = activate_modules('product_bulk')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create bulk product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> bulk_product = Product()
    >>> bulk_template = ProductTemplate()
    >>> bulk_template.name = 'bulk product'
    >>> bulk_template.default_uom = unit
    >>> bulk_template.type = 'goods'
    >>> bulk_template.list_price = Decimal('40')
    >>> bulk_template.bulk_type = True
    >>> bulk_template.save()
    >>> bulk_product, = bulk_template.products
    >>> bulk_product.save()

Create packaging product::

    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> packaging_product = Product()
    >>> packaging_template = ProductTemplate()
    >>> packaging_template.name = 'packaging product'
    >>> packaging_template.default_uom = unit
    >>> packaging_template.type = 'goods'
    >>> packaging_template.list_price = Decimal('40')
    >>> packaging_template.packaging = True
    >>> packaging_template.save()
    >>> packaging_product, = packaging_template.products
    >>> packaging_product.save()

Create extra product::

    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> extra_product = Product()
    >>> extra_template = ProductTemplate()
    >>> extra_template.name = 'other product'
    >>> extra_template.default_uom = unit
    >>> extra_template.type = 'goods'
    >>> extra_template.list_price = Decimal('40')
    >>> extra_template.save()
    >>> extra_product, = extra_template.products
    >>> extra_product.save()

Add packaging product to bulk product::

    >>> TemplateProductPackaging = Model.get('product.template-product.packaging')
    >>> package = TemplateProductPackaging()
    >>> package.packaging_product = packaging_template
    >>> bulk_template.packaging_products.append(package)

Add extra product to bulk product::

    >>> ExtraProductPackaging = Model.get('product.template-extra.product')
    >>> extra = ExtraProductPackaging()
    >>> extra.extra_product = extra_template
    >>> extra.quantity = Decimal(1)
    >>> bulk_template.extra_products.append(extra)
    >>> bulk_template.save()

Create packaged products::

    >>> bulk_template.click('create_packaging_products')
    >>> bulk_template.packaging_products[0].packaged_product.name
    'bulk product (packaging product)'
    >>> (bulk_template.packaging_products[0].packaged_product.bulk_product ==
    ...   bulk_template.products[0])
    True
    >>> len(bulk_template.packaging_products[0].packaged_product.products[0].boms)
    1
    >>> packaged, = ProductTemplate.find([('name', '=',
    ...   'bulk product (packaging product)')])
    >>> input1, = ([x.product for x in packaged.products[0].boms[0].bom.inputs
    ...   if x.product == bulk_product])
    >>> input1 == bulk_product
    True
    >>> input2, = ([x.product for x in packaged.products[0].boms[0].bom.inputs
    ...   if x.product == packaging_product])
    >>> input2 == packaging_product
    True
    >>> input3, = ([x for x in packaged.products[0].boms[0].bom.inputs
    ...   if x.product == extra_product])
    >>> input3.product == extra_product
    True
    >>> input3.quantity
    1.0
    >>> packaged.products[0].boms[0].bom.outputs[0].product == packaged.products[0]
    True
