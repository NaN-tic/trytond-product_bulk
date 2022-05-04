# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.modules.stock.move import STATES, DEPENDS

__all__ = ['StockMove']


class StockMove(metaclass=PoolMeta):
    __name__ = 'stock.move'

    bulk_product = fields.Many2One('product.product', 'Bulk Product', context={
            'company': Eval('company'),
            },
        states=STATES, depends=DEPENDS + ['company'])

    # TODO: check if is necessary
    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Product = pool.get('product.product')

        vlist = [x.copy() for x in vlist]
        for vals in vlist:
            product = Product(vals['product'])
            if product.bulk_type:
                vals['bulk_product'] = product
            else:
                vals['bulk_product'] = product.bulk_product
        moves = super().create(vlist)
        return moves
