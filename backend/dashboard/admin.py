from django.contrib import admin
from .models import Product, Category, Customer, Transaction, Shop


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'shop_type', 'owner_name', 'phone_number', 'address']
    search_fields = ['name', 'owner_name', 'phone_number', 'address', 'complete_address']
    list_filter = ['shop_type']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'shop']
    search_fields = ['name']
    list_filter = ['shop']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'shop', 'category', 'size', 'unit', 'price', 'stock', 'status', 'updated_at']
    list_filter = ['shop', 'status', 'category']
    search_fields = ['name', 'sku', 'variant', 'size', 'unit']
    list_editable = ['stock', 'price']
    readonly_fields = ['status', 'created_at', 'updated_at']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'created_at']
    search_fields = ['name', 'email']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['txn_id', 'customer', 'product', 'amount', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['txn_id', 'customer__name']
    readonly_fields = ['txn_id', 'created_at']
