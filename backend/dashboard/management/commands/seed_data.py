"""
Management command: python manage.py seed_data
Seeds the database with sample products, customers, and transactions.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import random

from dashboard.models import Category, Product, Customer, Transaction, Shop


CATEGORIES = ['Electronics', 'Workstations', 'Peripherals', 'Networking', 'Software']

PRODUCTS = [
    {'name': 'MacBook Pro M3 Max', 'variant': 'Space Black, 64GB RAM', 'sku': 'APP-MBP-14-BK',
     'category': 'Workstations', 'price': '3499.00', 'stock': 42},
    {'name': 'Studio Display Ultra', 'variant': '5K Retina, Nano-texture', 'sku': 'MON-SDU-27-NT',
     'category': 'Peripherals', 'price': '1899.00', 'stock': 8},
    {'name': 'iPad Pro 12.9"', 'variant': 'Wi-Fi + Cellular, 1TB', 'sku': 'APP-IPD-12-1T',
     'category': 'Electronics', 'price': '1499.00', 'stock': 0},
    {'name': 'Mechanical Master Keyboard', 'variant': 'Brown Switches, Wireless', 'sku': 'LOG-MXK-BRW-BT',
     'category': 'Peripherals', 'price': '159.00', 'stock': 124},
    {'name': 'Pro Wireless Buds', 'variant': 'Noise Cancelling, ANC', 'sku': 'SNY-WF-XM5-BLK',
     'category': 'Electronics', 'price': '349.00', 'stock': 2},
    {'name': '4K Smart Display', 'variant': '32-inch, HDR600', 'sku': 'SAM-UD32-4K',
     'category': 'Peripherals', 'price': '799.00', 'stock': 5},
    {'name': 'Quantum Laptop Pro', 'variant': 'i9, 32GB RAM, 1TB SSD', 'sku': 'DEL-XPS-15-I9',
     'category': 'Workstations', 'price': '2499.00', 'stock': 18},
    {'name': 'Smart Audio Buds', 'variant': 'Active Noise Cancellation', 'sku': 'APP-AIRP-PRO-2',
     'category': 'Electronics', 'price': '249.00', 'stock': 67},
    {'name': 'Managed 24-Port Switch', 'variant': 'PoE+, Gigabit', 'sku': 'CSC-SG350-24P',
     'category': 'Networking', 'price': '599.00', 'stock': 14},
    {'name': 'Enterprise SSD 2TB', 'variant': 'NVMe PCIe 4.0', 'sku': 'SAM-990-PRO-2T',
     'category': 'Electronics', 'price': '189.00', 'stock': 93},
    {'name': 'Ergonomic Pro Mouse', 'variant': 'Wireless, 8K DPI', 'sku': 'LOG-MX-MASTER-3',
     'category': 'Peripherals', 'price': '99.00', 'stock': 203},
    {'name': 'Developer Workstation', 'variant': 'AMD Threadripper, 128GB', 'sku': 'HP-Z8-TRX-128',
     'category': 'Workstations', 'price': '7999.00', 'stock': 7},
]

CUSTOMERS = [
    {'name': 'Julianne Doe', 'email': 'julianne.doe@example.com', 'phone': '+1-555-0101'},
    {'name': 'Marcus Kane', 'email': 'marcus.kane@example.com', 'phone': '+1-555-0102'},
    {'name': 'Sarah Wilson', 'email': 'sarah.wilson@example.com', 'phone': '+1-555-0103'},
    {'name': 'Alex Rivera', 'email': 'alex.rivera@example.com', 'phone': '+1-555-0104'},
    {'name': 'Priya Sharma', 'email': 'priya.sharma@example.com', 'phone': '+91-555-0201'},
    {'name': 'Chen Wei', 'email': 'chen.wei@example.com', 'phone': '+86-555-0301'},
]


class Command(BaseCommand):
    help = 'Seed database with sample data'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing data first')

    def handle(self, *args, **options):
        if options['clear']:
            Transaction.objects.all().delete()
            Product.objects.all().delete()
            Customer.objects.all().delete()
            Category.objects.all().delete()
            Shop.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing data.'))

        shop, _ = Shop.objects.get_or_create(
            name='Main Store',
            defaults={
                'shop_type': Shop.TYPE_ELECTRONICS,
                'owner_name': 'Store Admin',
                'phone_number': '+91-99999-99999',
                'address': 'Primary shop',
                'complete_address': 'Primary shop',
            }
        )
        self.stdout.write(f'  ✓ shop ready: {shop.name}')

        # Categories
        cat_objs = {}
        for cat_name in CATEGORIES:
            obj, _ = Category.objects.get_or_create(name=cat_name, shop=shop)
            cat_objs[cat_name] = obj
        self.stdout.write(f'  ✓ {len(cat_objs)} categories')

        # Products
        p_count = 0
        for p in PRODUCTS:
            product, created = Product.objects.get_or_create(
                sku=p['sku'],
                defaults={
                    'name': p['name'],
                    'variant': p['variant'],
                    'shop': shop,
                    'category': cat_objs[p['category']],
                    'price': Decimal(p['price']),
                    'stock': p['stock'],
                    'low_stock_threshold': 10,
                }
            )
            if created:
                p_count += 1
        self.stdout.write(f'  ✓ {p_count} products created')

        # Customers
        c_count = 0
        cust_objs = []
        for c in CUSTOMERS:
            obj, created = Customer.objects.get_or_create(
                email=c['email'],
                defaults={'name': c['name'], 'phone': c['phone']}
            )
            cust_objs.append(obj)
            if created:
                c_count += 1
        self.stdout.write(f'  ✓ {c_count} customers created')

        # Transactions
        products_list = list(Product.objects.all())
        statuses = [Transaction.STATUS_COMPLETED, Transaction.STATUS_PROCESSING,
                    Transaction.STATUS_SHIPPED, Transaction.STATUS_CANCELLED]
        t_count = 0
        for i in range(20):
            cust = random.choice(cust_objs)
            prod = random.choice(products_list)
            status = random.choices(statuses, weights=[50, 25, 20, 5])[0]
            Transaction.objects.get_or_create(
                txn_id=f'#SHP-{90421 + i}',
                defaults={
                    'customer': cust,
                    'product': prod,
                    'amount': prod.price,
                    'status': status,
                    'created_at': timezone.now(),
                }
            )
            t_count += 1
        self.stdout.write(f'  ✓ {t_count} transactions created')

        self.stdout.write(self.style.SUCCESS('Seed data complete!'))
