from django.db import migrations


def forwards(apps, schema_editor):
    Shop = apps.get_model('dashboard', 'Shop')
    Category = apps.get_model('dashboard', 'Category')
    Product = apps.get_model('dashboard', 'Product')

    shop, _ = Shop.objects.get_or_create(name='Main Store', defaults={'address': 'Primary shop'})
    Category.objects.filter(shop__isnull=True).update(shop=shop)
    Product.objects.filter(shop__isnull=True).update(shop=shop)


def backwards(apps, schema_editor):
    Shop = apps.get_model('dashboard', 'Shop')
    Category = apps.get_model('dashboard', 'Category')
    Product = apps.get_model('dashboard', 'Product')

    default_shop = Shop.objects.filter(name='Main Store').first()
    if default_shop:
        Category.objects.filter(shop=default_shop).update(shop=None)
        Product.objects.filter(shop=default_shop).update(shop=None)


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_shop_alter_category_name_category_shop_product_shop_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
