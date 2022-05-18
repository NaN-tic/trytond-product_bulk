# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Bool, Id
from trytond.transaction import Transaction
from decimal import Decimal

NON_MEASURABLE = ['service']


class ProductProductPackaging(ModelSQL, ModelView):
    "Product - Product Packaging"
    __name__ = 'product.product-product.packaging'
    packaging_product = fields.Many2One('product.product', 'Packaging Product',
        required=True, ondelete='CASCADE',
        states = {
            'readonly': Bool(Eval('packaged_product')),
            },
        domain=[
            ('packaging', '=', True),
        ])
    product = fields.Many2One('product.product', 'Product', required=True)
    packaged_product = fields.Many2One('product.template', 'Packaged Product',
        states = {
            'readonly': True,
            },
        )

class ExtraProductPackaging(ModelSQL, ModelView):
    "Template - Product Packaging"
    __name__ = 'product.product-extra.product'
    extra_product = fields.Many2One('product.product', 'Extra Product',
        required=True, ondelete='CASCADE',
        states = {
            'readonly': Bool(Eval('packaged_product')),
            })
    product = fields.Many2One('product.product', 'Product', required=True)
    unit_digits = fields.Function(fields.Integer('Unit Digits'),
        'on_change_with_unit_digits')
    quantity = fields.Float('Quantity',
        digits=(16, Eval('unit_digits', 2)),
        depends=['unit_digits'])

    @fields.depends('extra_product')
    def on_change_with_unit_digits(self, name=None):
        if self.extra_product:
            return self.extra_product.default_uom.digits
        return 2


class Template(metaclass=PoolMeta):
    __name__ = 'product.template'

    bulk_type = fields.Boolean('Bulk')
    bulk_quantity = fields.Function(fields.Float('Bulk Quantity',
        help="The amount of bulk stock in the location."),
        'sum_product')


    def sum_product(self, name):
        if name in ('bulk_quantity'):
            sum_ = 0.
            for product in self.products:
                sum_ += getattr(product, name)
            return sum_
        return super().sum_product(name)


class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    bulk_type = fields.Function(fields.Boolean('Bulk'), 'get_bulk')
    bulk_product = fields.Many2One('product.product', 'Bulk Product',
        domain=[
            ('template.bulk_type', '=', True),
            ],
        states= {
            'readonly': (~Eval('active', True) | Eval('bulk_type') == True),
            }, depends=['bulk_type'])
    bulk_quantity = fields.Function(fields.Float('Bulk Quantity',
        help="The amount of bulk stock in the location."),
        'get_bulk_quantity', searcher='search_bulk_quantity')
    packaging = fields.Boolean('Packaging')
    packaging_products = fields.One2Many('product.product-product.packaging',
        'product', 'Packaging Products',
        states = {
            'readonly': (~Eval('active', True) | Eval('bulk_type') != True),
            })
    capacity_pkg = fields.Float('Capacity', digits=(16, Eval('capacity_digits', 2)),
        states={
            'invisible': Eval('type').in_(NON_MEASURABLE),
            },
        depends=['type', 'capacity_digits'])
    capacity_uom = fields.Many2One('product.uom', 'Capacity Uom',
        domain=[('symbol', '=', 'l')],
        states={
            'invisible': Eval('type').in_(NON_MEASURABLE),
            'required': Bool(Eval('capacity')),
            },
        depends=['type', 'capacity'])
    capacity_digits = fields.Function(fields.Integer('Capacity Digits'),
        'on_change_with_capacity_digits')
    netweight = fields.Float('Net Weight',
        digits=(16, Eval('netweight_digits', 2)),
        states={
            'invisible': Eval('type').in_(NON_MEASURABLE),
            },
        depends=['type', 'netweight_digits'])
    netweight_uom = fields.Many2One('product.uom', 'Net Weight Uom',
        domain=[('category', '=', Id('product', 'uom_cat_weight'))],
        states={
            'invisible': Eval('type').in_(NON_MEASURABLE),
            'required': Bool(Eval('netweight')),
            },
        depends=['type', 'netweight'])
    netweight_digits = fields.Function(fields.Integer('Net Weight Digits'),
        'on_change_with_netweight_digits')
    extra_products = fields.One2Many('product.product-extra.product',
        'product', 'Extra Products',
        states = {
            'readonly': (~Eval('active', True) | Eval('bulk_type') != True),
            })

    @classmethod
    def __setup__(cls):
        super().__setup__()
        # cls._modify_no_move += [
        #     ('bulk_type', 'product_bulk.msg_product_bulk_type_has_stock'),
        #     ('bulk_product', 'product_bulk.msg_product_bulk_product_has_stock'),
        #     ]
        cls._buttons.update({
                'create_packaging_products': {
                    'invisible': (~Eval('active', True)
                        | Eval('bulk_type') != True)
                },
            })

    @fields.depends('capacity_uom')
    def on_change_with_capacity_digits(self, name=None):
        return (self.capacity_uom.digits if self.capacity_uom
            else self.default_capacity_digits())

    @staticmethod
    def default_capacity():
        return 0.

    @staticmethod
    def default_capacity_uom():
        return Pool().get('ir.model.data').get_id('product', 'uom_liter')

    @staticmethod
    def default_capacity_digits():
        return 2

    @fields.depends('netweight_uom')
    def on_change_with_netweight_digits(self, name=None):
        return (self.netweight_uom.digits if self.netweight_uom
            else self.default_netweight_digits())

    @staticmethod
    def default_netweight_digits():
        return 2

    def get_bulk(self, name=None):
        return self.template.bulk_type

    @classmethod
    @ModelView.button
    def create_packaging_products(cls, products):
        Template = Pool().get('product.template')
        Product = Pool().get('product.product')
        Bom = Pool().get('production.bom')
        BOMInput = Pool().get('production.bom.input')
        BOMOutput = Pool().get('production.bom.output')
        Uom = Pool().get('product.uom')
        ProductPackaging = Pool().get('product.product-product.packaging')
        ProductBom = Pool().get('product.product-production.bom')

        uom_unit, = Uom.search([('symbol', 'like', 'u')])
        uom_kg, = Uom.search([('symbol', 'like', 'kg')])
        product_to_save = []
        bom_to_save = []
        output_to_save = []
        inputs = []

        for bulk_product in products:
            for package_product in bulk_product.packaging_products:
                if package_product.packaged_product:
                    continue

                new_code = ((bulk_product.code
                    if bulk_product.code else '') + '' +
                    ('-' + package_product.packaging_product.code if
                    package_product.packaging_product.code else ''))
                new_name = (bulk_product.name +
                    ' (' + package_product.packaging_product.name + ')')
                capacity = package_product.packaging_product.capacity_pkg
                netweight = round(capacity/ 1000, uom_kg.digits)
                weight = round(netweight +
                    (package_product.packaging_product.weight
                    if package_product.packaging_product.weight else 0),
                        uom_kg.digits)


                output_template = Template()
                output_template.name = new_name
                output_template.code = new_code
                output_template.producible = True
                output_template.salable = True
                output_template.sale_uom = uom_unit
                output_template.default_uom = uom_unit
                output_template.list_price = Decimal(0)
                output_template.weight = weight
                output_template.weight_uom = uom_kg
                output_template.type = bulk_product.type
                output_template.account_category = bulk_product.account_category
                output_template.categories = bulk_product.categories
                output_template.save()

                output_product = Product()
                output_product.code = new_code
                output_product.template = output_template
                output_product.capacity_pkg = package_product.packaging_product.capacity
                output_product.netweight = netweight
                output_product.netweight_uom = uom_kg
                output_product.bulk_product = bulk_product.id
                output_product.save()


                package_product.packaged_product = output_template
                output_to_save.append(package_product)

                bom = Bom(name=new_name)
                bulk_input = BOMInput(
                    bom=bom,
                    product=bulk_product,
                    uom=bulk_product.default_uom,
                    quantity=netweight)
                inputs.append(bulk_input)
                package_input = BOMInput(
                    bom=bom,
                    product=package_product.packaging_product,
                    uom=package_product.packaging_product.default_uom,
                    quantity=1.0)
                inputs.append(package_input)

                if bulk_product.extra_products:
                    for extra in bulk_product.extra_products:
                        extra_input = BOMInput(
                            bom=bom,
                            product=extra.extra_product,
                            uom=extra.extra_product.default_uom,
                            quantity=extra.quantity)
                        inputs.append(extra_input)

                output = BOMOutput(
                    bom=bom,
                    product=output_product.id,
                    uom=uom_unit,
                    quantity=1.0)

                bom.inputs = inputs
                bom.outputs = [output]
                bom_to_save.append(bom)

                product_bom = ProductBom()
                product_bom.bom = bom
                product_bom.product = output_product
                product_to_save.append(product_bom)

            Bom.save(bom_to_save)
            ProductBom.save(product_to_save)
            ProductPackaging.save(output_to_save)


    @classmethod
    def get_bulk_quantity(cls, products, name):
        pool = Pool()
        Location = pool.get('stock.location')
        Product = pool.get('product.product')
        Date = pool.get('ir.date')
        today = Date().today()

        res = {}
        products_ids = []
        for product in products:
            res[product.id] = 0

        # location_ids = Transaction().context.get('locations')
        # if not location_ids:
        #     locations = Location.search(['type', '=', 'warehouse'])
        #     location_ids = [x.storage_location.id for x in locations
        #                     if x.storage_location]

        # output_products = Product.search([
        #                     ('bulk_product', 'in', products)
        #                     ])
        # output_products_ids = [x.id for x in output_products]

        # products_ids += [x.id for x in products]

        # with Transaction().set_context(locations=location_ids,
        #             stock_date_end=today,
        #             _check_access=False):

        #     bulk_quantity = cls._get_quantity(output_products, 'quantity',
        #         location_ids, grouping=('product',),
        #         grouping_filter=(output_products_ids,))
        #     quantity = cls._get_quantity(products, 'quantity', location_ids,
        #         grouping=('product',) , grouping_filter=(products_ids,))

        # res.update(quantity)
        # for product in output_products:
        #     res[product.bulk_product.id] += (bulk_quantity.get(product.id,0)
        #         * product.netweight if product.netweight else 0.0)
        return res

    @classmethod
    def search_bulk_quantity(cls, name, domain=None):
        location_ids = Transaction().context.get('locations')
        return cls._search_quantity('quantity', location_ids, domain,
            grouping=('bulk_product', 'product',))
