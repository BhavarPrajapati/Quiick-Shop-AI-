import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from django.db import transaction as db_transaction
from django.db.models import Q

from dashboard.models import Category, Product, Shop, StockLog
from dashboard.services.intent_model import predict_intent


ACTION_SELL = 'sell'
ACTION_ADD = 'add'
ACTION_SHOW_SALES = 'show_sales'
ACTION_CHECK_STOCK = 'check_stock'
ACTION_LOW_STOCK = 'low_stock'


@dataclass
class IntentResult:
    intent: str
    quantity: int
    shop: Shop | None = None
    category: Category | None = None
    product: Product | None = None
    matched_products: list[dict[str, Any]] = field(default_factory=list)
    reply: str = ''
    query_preview: str = ''
    raw_message: str = ''
    confidence: float | None = None
    error: str | None = None


def _first_int(text: str, default: int = 1) -> int:
    match = re.search(r'\b(\d+)\b', text)
    if not match:
        return default
    return max(int(match.group(1)), 1)


def _extract_action(text: str) -> str:
    lowered = text.lower().strip()
    
    # Check for show_sales/analytics
    if re.search(r'\b(show|sales|revenue|today|daily|report|analytics|bikri)\b', lowered):
        return ACTION_SHOW_SALES
    
    # Check for low_stock
    if re.search(r'\b(low|critical|out|empty|running out|low stock|kam stock|stock kam|khatam)\b', lowered):
        if re.search(r'\b(stock|inventory|items)\b', lowered):
            return ACTION_LOW_STOCK
    
    # Check for check_stock
    if re.search(r'\b(check|current|available|stock|inventory|kitna|how many)\b', lowered):
        if not re.search(r'\b(sell|add|increase|deduct)\b', lowered):
            return ACTION_CHECK_STOCK
    
    # Sell patterns (English + Hindi/Hinglish)
    if re.search(r'\b(sell|sold|bech|beche|discharge|dispatch|deduct|decrease|remove|dispose|nikaal|nikale|kam karo|kam kar|sell kar|diye|diya)\b', lowered):
        return ACTION_SELL
    
    # Add patterns (English + Hindi/Hinglish)
    if re.search(r'\b(add|added|increase|stock|restock|purchase|buy|bought|receive|add karo|add kar|joda|jode|le aaya|aaya|laye|stock karo|store)\b', lowered):
        return ACTION_ADD
    
    return ''


def _match_shop(text: str, explicit_name: str | None = None) -> Shop | None:
    candidate = (explicit_name or '').strip()
    if candidate:
        shop = Shop.objects.filter(name__iexact=candidate).first()
        if shop:
            return shop

    lowered = text.lower()
    for shop in Shop.objects.all():
        if shop.name.lower() in lowered:
            return shop

    return Shop.objects.first()


def _match_category(text: str, shop: Shop | None = None, explicit_name: str | None = None) -> Category | None:
    candidate = (explicit_name or '').strip()
    qs = Category.objects.all()
    if shop:
        qs = qs.filter(Q(shop=shop) | Q(shop__isnull=True))

    if candidate:
        category = qs.filter(name__iexact=candidate).first()
        if category:
            return category

    lowered = text.lower()
    categories = list(qs.order_by('name'))
    for category in sorted(categories, key=lambda item: len(item.name), reverse=True):
        if category.name.lower() in lowered:
            return category
    return None


def _match_product(text: str, shop: Shop | None = None, explicit_name: str | None = None) -> Product | None:
    candidate = (explicit_name or '').strip()
    qs = Product.objects.select_related('shop', 'category')
    if shop:
        qs = qs.filter(Q(shop=shop) | Q(shop__isnull=True))

    if candidate:
        product = qs.filter(name__iexact=candidate).first()
        if product:
            return product

    lowered = text.lower()
    for product in qs.order_by('name'):
        if product.name.lower() in lowered:
            return product
    return None


def _normalize_payload(message: str, model_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    model_payload = model_payload or {}
    return {
        'intent': (model_payload.get('intent') or _extract_action(message) or '').lower(),
        'quantity': int(model_payload.get('quantity') or _first_int(message)),
        'shop_name': model_payload.get('shop') or model_payload.get('shop_name'),
        'category_name': model_payload.get('category') or model_payload.get('category_name'),
        'product_name': model_payload.get('product') or model_payload.get('product_name'),
        'confidence': model_payload.get('confidence'),
    }


def _load_model_payload(payload: str | dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    if isinstance(payload, dict):
        return payload
    try:
        return json.loads(payload)
    except (TypeError, ValueError):
        return None


def handle_chat_message(message: str, model_payload: str | dict[str, Any] | None = None) -> IntentResult:
    # If no explicit model_payload provided, use trained model to predict
    if not model_payload:
        model_payload = predict_intent(message)
    
    parsed_payload = _load_model_payload(model_payload)
    normalized = _normalize_payload(message, parsed_payload)

    intent = normalized['intent']
    quantity = normalized['quantity']
    shop = _match_shop(message, normalized['shop_name'])
    category = _match_category(message, shop=shop, explicit_name=normalized['category_name'])
    product = _match_product(message, shop=shop, explicit_name=normalized['product_name'])

    result = IntentResult(
        intent=intent,
        quantity=quantity,
        shop=shop,
        category=category,
        product=product,
        raw_message=message,
        confidence=normalized['confidence'],
    )

    # Handle read-only queries first
    if intent == ACTION_SHOW_SALES:
        return _show_sales(result, shop)
    if intent == ACTION_CHECK_STOCK:
        return _check_stock(result, shop, category, product)
    if intent == ACTION_LOW_STOCK:
        return _low_stock_alert(result, shop, category)

    # Handle mutations
    if intent not in {ACTION_SELL, ACTION_ADD}:
        result.error = 'Unsupported intent'
        result.reply = (
            'I could not map that message to a stock action. Try commands like "sell 10 electronics" '
            'or "add 5 peripherals", or ask "show sales", "check stock", or "low stock items".'
        )
        return result

    if not shop:
        result.error = 'No shop found'
        result.reply = 'I could not find a shop to apply this action to.'
        return result

    if not product and not category:
        result.error = 'No target found'
        result.reply = 'I could not find a product or category in that request.'
        return result

    if intent == ACTION_SELL:
        return _apply_sell(result)
    return _apply_add(result)


def _apply_sell(result: IntentResult) -> IntentResult:
    quantity = result.quantity
    shop = result.shop
    assert shop is not None

    with db_transaction.atomic():
        if result.product:
            product = Product.objects.select_for_update().get(pk=result.product.pk)
            if product.stock < quantity:
                result.error = 'Insufficient stock'
                result.reply = f'Not enough stock in {product.name}. Available: {product.stock}, requested: {quantity}.'
                return result
            stock_before = product.stock
            product.stock -= quantity
            product.save(update_fields=['stock', 'status', 'updated_at'])
            StockLog.objects.create(
                shop=shop, product=product, category=product.category,
                action=StockLog.ACTION_SELL, quantity=quantity,
                stock_before=stock_before, stock_after=product.stock,
                note=f'AI chatbot sold {quantity} units of {product.name}',
            )
            result.matched_products = [{'product': product.name, 'delta': -quantity, 'stock': product.stock}]
            result.product = product
            result.query_preview = (
                f"UPDATE dashboard_product SET stock = stock - {quantity} WHERE id = {product.pk};"
            )
            result.reply = (
                f'Sold {quantity} units from {product.name}. New stock: {product.stock}. '
                f'Applied in {shop.name}.'
            )
            return result

        qs = Product.objects.select_for_update().filter(shop=shop)
        if result.category:
            qs = qs.filter(category=result.category)

        products = list(qs.order_by('-stock', 'updated_at'))
        total_stock = sum(product.stock for product in products)
        if total_stock < quantity:
            result.error = 'Insufficient category stock'
            result.reply = (
                f'Not enough stock to sell {quantity} units from {result.category.name if result.category else "this group"}. '
                f'Available: {total_stock}.'
            )
            return result

        remaining = quantity
        applied = []
        for product in products:
            if remaining <= 0:
                break
            if product.stock <= 0:
                continue
            take = min(product.stock, remaining)
            stock_before = product.stock
            product.stock -= take
            product.save(update_fields=['stock', 'status', 'updated_at'])
            StockLog.objects.create(
                shop=shop, product=product, category=result.category,
                action=StockLog.ACTION_SELL, quantity=take,
                stock_before=stock_before, stock_after=product.stock,
                note=f'AI chatbot sold {take} units of {product.name} (batch sell)',
            )
            remaining -= take
            applied.append({'product': product.name, 'delta': -take, 'stock': product.stock})

        result.matched_products = applied
        category_name = result.category.name if result.category else 'selected products'
        result.query_preview = (
            f"UPDATE dashboard_product SET stock = stock - <allocated_amount> WHERE shop_id = {shop.pk} "
            f"AND category_id = {result.category.pk if result.category else 'NULL'};"
        )
        lines = ', '.join(f"{item['product']} (-{abs(item['delta'])})" for item in applied)
        result.reply = f'Sold {quantity} units from {category_name} in {shop.name}: {lines}.'
        return result


def _apply_add(result: IntentResult) -> IntentResult:
    quantity = result.quantity
    shop = result.shop
    assert shop is not None

    with db_transaction.atomic():
        if result.product:
            product = Product.objects.select_for_update().get(pk=result.product.pk)
        else:
            qs = Product.objects.select_for_update().filter(shop=shop)
            if result.category:
                qs = qs.filter(category=result.category)
            product = qs.order_by('stock', 'updated_at').first()

        if not product:
            result.error = 'No product to update'
            result.reply = 'I found the shop/category, but no matching product exists to update stock.'
            return result

        stock_before = product.stock
        product.stock += quantity
        product.save(update_fields=['stock', 'status', 'updated_at'])
        StockLog.objects.create(
            shop=shop, product=product, category=result.category or product.category,
            action=StockLog.ACTION_ADD, quantity=quantity,
            stock_before=stock_before, stock_after=product.stock,
            note=f'AI chatbot added {quantity} units to {product.name}',
        )
        result.product = product
        result.matched_products = [{'product': product.name, 'delta': quantity, 'stock': product.stock}]
        result.query_preview = f"UPDATE dashboard_product SET stock = stock + {quantity} WHERE id = {product.pk};"
        result.reply = f'Added {quantity} units to {product.name}. New stock: {product.stock}. Applied in {shop.name}.'
        return result


def _show_sales(result: IntentResult, shop: Shop | None = None) -> IntentResult:
    """Show sales summary and revenue."""
    if not shop:
        shop = Shop.objects.first()
    
    if not shop:
        result.reply = 'No shops found in the system.'
        result.error = 'No shop'
        return result
    
    # Get top-selling products for this shop
    products = Product.objects.filter(shop=shop).order_by('-stock')[:5]
    
    if not products:
        result.reply = f'No products in {shop.name} yet.'
        return result
    
    # Calculate total inventory value
    total_value = sum(p.stock * p.price for p in products if p.price)
    total_items = sum(p.stock for p in products)
    
    lines = []
    for product in products:
        value = product.stock * product.price if product.price else 0
        lines.append(f"📦 {product.name}: {product.stock} units (₹{value:,.0f})")
    
    product_list = '\n'.join(lines)
    
    result.reply = (
        f"📊 Sales Summary for {shop.name}:\n"
        f"{product_list}\n\n"
        f"📈 Total Inventory: {total_items} items\n"
        f"💰 Inventory Value: ₹{total_value:,.0f}"
    )
    result.matched_products = [
        {'product': p.name, 'stock': p.stock, 'value': float(p.stock * p.price) if p.price else 0}
        for p in products
    ]
    return result


def _check_stock(result: IntentResult, shop: Shop | None = None, category: Category | None = None, product: Product | None = None) -> IntentResult:
    """Check current stock levels."""
    if not shop:
        shop = Shop.objects.first()
    
    if not shop:
        result.reply = 'No shops found in the system.'
        result.error = 'No shop'
        return result
    
    qs = Product.objects.filter(shop=shop)
    
    if product:
        qs = qs.filter(pk=product.pk)
    elif category:
        qs = qs.filter(category=category)
    
    products = list(qs.order_by('name'))
    
    if not products:
        target = f"in {category.name}" if category else f"in {shop.name}"
        result.reply = f'No products found {target}.'
        return result
    
    lines = []
    total_stock = 0
    for p in products:
        total_stock += p.stock
        status = "✅" if p.stock > 0 else "⚠️"
        lines.append(f"{status} {p.name}: {p.stock} units @ ₹{p.price}")
    
    product_list = '\n'.join(lines)
    target = f"{category.name} in" if category else ""
    
    result.reply = (
        f"📦 Stock Check for {target} {shop.name}:\n"
        f"{product_list}\n\n"
        f"Total: {total_stock} items"
    )
    result.matched_products = [
        {'product': p.name, 'stock': p.stock, 'price': float(p.price)}
        for p in products
    ]
    return result


def _low_stock_alert(result: IntentResult, shop: Shop | None = None, category: Category | None = None) -> IntentResult:
    """Show low stock alert items."""
    if not shop:
        shop = Shop.objects.first()
    
    if not shop:
        result.reply = 'No shops found in the system.'
        result.error = 'No shop'
        return result
    
    qs = Product.objects.filter(shop=shop, stock__lt=10)  # Items with less than 10 units
    
    if category:
        qs = qs.filter(category=category)
    
    products = list(qs.order_by('stock', 'name'))
    
    if not products:
        target = f"in {category.name}" if category else f"in {shop.name}"
        result.reply = f'✅ No low-stock items {target}. All inventory levels are healthy!'
        return result
    
    lines = []
    for p in products:
        lines.append(f"⚠️ {p.name}: {p.stock} units remaining (threshold: 10)")
    
    product_list = '\n'.join(lines)
    
    result.reply = (
        f"🚨 Low Stock Alert for {shop.name}:\n"
        f"{product_list}\n\n"
        f"Total items below threshold: {len(products)}"
    )
    result.matched_products = [
        {'product': p.name, 'stock': p.stock, 'category': p.category.name}
        for p in products
    ]
    return result
