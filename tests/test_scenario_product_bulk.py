import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.company.tests.tools import create_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install product_bulk module
        activate_modules('product_bulk')

        # Create company
        _ = create_company()

        # Create bulk product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        bulk_product = Product()
        bulk_template = ProductTemplate()
        bulk_template.name = 'bulk product'
        bulk_template.default_uom = unit
        bulk_template.type = 'goods'
        bulk_template.list_price = Decimal('40')
        bulk_template.bulk_type = True
        bulk_template.save()
        bulk_product, = bulk_template.products
        bulk_product.save()

        # Create packaging product
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        packaging_product = Product()
        packaging_template = ProductTemplate()
        packaging_template.name = 'packaging product'
        packaging_template.default_uom = unit
        packaging_template.type = 'goods'
        packaging_template.list_price = Decimal('40')
        packaging_template.packaging = True
        packaging_template.save()
        packaging_product, = packaging_template.products
        packaging_product.save()

        # Create extra product
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        extra_product = Product()
        extra_template = ProductTemplate()
        extra_template.name = 'other product'
        extra_template.default_uom = unit
        extra_template.type = 'goods'
        extra_template.list_price = Decimal('40')
        extra_template.save()
        extra_product, = extra_template.products
        extra_product.save()

        # Add packaging product to bulk product
        TemplateProductPackaging = Model.get(
            'product.template-product.packaging')
        package = TemplateProductPackaging()
        package.packaging_product = packaging_template
        bulk_template.packaging_products.append(package)

        # Add extra product to bulk product
        ExtraProductPackaging = Model.get('product.template-extra.product')
        extra = ExtraProductPackaging()
        extra.extra_product = extra_template
        extra.quantity = Decimal(1)
        bulk_template.extra_products.append(extra)
        bulk_template.save()

        # Create packaged products
        bulk_template.click('create_packaging_products')
        self.assertEqual(
            bulk_template.packaging_products[0].packaged_product.name,
            'bulk product (packaging product)')
        self.assertEqual(
            (bulk_template.packaging_products[0].packaged_product.bulk_product
             == bulk_template.products[0]), True)
        self.assertEqual(
            len(bulk_template.packaging_products[0].packaged_product.
                products[0].boms), 1)
        packaged, = ProductTemplate.find([('name', '=',
                                           'bulk product (packaging product)')])
        input1, = ([
            x.product for x in packaged.products[0].boms[0].bom.inputs
            if x.product == bulk_product
        ])
        self.assertEqual(input1, bulk_product)
        input2, = ([
            x.product for x in packaged.products[0].boms[0].bom.inputs
            if x.product == packaging_product
        ])
        self.assertEqual(input2, packaging_product)
        input3, = ([
            x for x in packaged.products[0].boms[0].bom.inputs
            if x.product == extra_product
        ])
        self.assertEqual(input3.product, extra_product)
        self.assertEqual(input3.quantity, 1.0)
        self.assertEqual(packaged.products[0].boms[0].bom.outputs[0].product,
                         packaged.products[0])
