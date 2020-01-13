# This file is part product_bulk module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import product
from . import stock

module = 'product_bulk'

def register():
    Pool.register(
        product.Product,
        product.TemplateProductPackaging,
        product.Template,
        stock.StockMove,
        module=module, type_='model')
