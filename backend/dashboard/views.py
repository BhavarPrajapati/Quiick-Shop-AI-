import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q, F
from django.db import models as django_models
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal

from .models import Product, Category, Transaction, Customer, Shop, ChatSession, ChatMessage, StockLog, Supplier, SupplierOrder
from .forms import ProductForm, SupplierForm, SupplierOrderForm
from .services.chatbot import handle_chat_message


def _get_current_shop(request):
    shop_id = request.session.get('current_shop_id')
    if not shop_id:
        return None
    shop = Shop.objects.filter(pk=shop_id).first()
    if shop is None:
        request.session.pop('current_shop_id', None)
    return shop


def _require_current_shop(request):
    shop = _get_current_shop(request)
    if shop is None:
        return None, redirect('core:onboarding_start')
    return shop, None


# ──────────────────────────────────────────────
# MAIN DASHBOARD
# ──────────────────────────────────────────────

def main_dashboard(request):
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    from django.utils import timezone
    today = timezone.now().date()

    products_qs = Product.objects.filter(shop=current_shop)
    total_products   = products_qs.count()
    active_count     = products_qs.filter(status=Product.STATUS_ACTIVE).count()
    low_stock_count  = products_qs.filter(status=Product.STATUS_LOW).count()
    out_of_stock_count = products_qs.filter(status=Product.STATUS_OUT).count()

    # Revenue
    total_revenue = Transaction.objects.filter(
        status=Transaction.STATUS_COMPLETED, product__shop=current_shop
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Today stats
    today_sales_count = Transaction.objects.filter(
        created_at__date=today, product__shop=current_shop
    ).count()
    today_revenue = Transaction.objects.filter(
        created_at__date=today, product__shop=current_shop,
        status=Transaction.STATUS_COMPLETED
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Inventory value
    total_inventory_value = products_qs.aggregate(
        val=Sum(F('price') * F('stock'), output_field=django_models.DecimalField())
    )['val'] or Decimal('0.00')

    # Recent transactions (last 5)
    recent_transactions = Transaction.objects.select_related('customer', 'product').filter(
        product__shop=current_shop
    ).order_by('-created_at')[:5]

    # Recent AI stock actions (last 6)
    recent_stock_logs = StockLog.objects.select_related('product', 'category').filter(
        shop=current_shop
    ).order_by('-created_at')[:6]

    # Low stock items for alerts
    low_items = products_qs.filter(
        status__in=[Product.STATUS_LOW, Product.STATUS_OUT]
    ).order_by('stock')[:5]

    # Top categories
    top_categories = Category.objects.filter(shop=current_shop).annotate(
        product_count=Count('products'),
        total_stock=Sum('products__stock')
    ).order_by('-product_count')[:5]

    # Suppliers summary
    total_suppliers   = Supplier.objects.filter(shop=current_shop).count()
    pending_orders    = SupplierOrder.objects.filter(
        supplier__shop=current_shop, status=SupplierOrder.STATUS_PENDING
    ).count()

    # AI chatbot command suggestions based on shop type
    if current_shop.is_grocery:
        ai_suggestions = [
            ('sell 10 wheat flour', 'Sell 10 wheat flour'),
            ('add 50 rice', 'Restock 50 rice'),
            ('check low stock', 'Check low stock'),
            ('show sales', 'Show today sales'),
        ]
    elif current_shop.is_cloths:
        ai_suggestions = [
            ('sell 5 shirts', 'Sell 5 shirts'),
            ('add 20 jeans', 'Restock 20 jeans'),
            ('check low stock', 'Check low stock'),
            ('show sales', 'Show today sales'),
        ]
    else:
        ai_suggestions = [
            ('sell 2 laptops', 'Sell 2 laptops'),
            ('add 10 phones', 'Restock 10 phones'),
            ('check low stock', 'Check low stock'),
            ('show sales', 'Show today sales'),
        ]

    context = {
        'page_title': f'{current_shop.name} | Quiick AI',
        'active_nav': 'dashboard',
        'current_shop': current_shop,
        'has_inventory': total_products > 0,
        # Core metrics
        'total_products': total_products,
        'active_count': active_count,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_revenue': total_revenue,
        'today_sales_count': today_sales_count,
        'today_revenue': today_revenue,
        'total_inventory_value': total_inventory_value,
        # Lists
        'recent_transactions': recent_transactions,
        'recent_stock_logs': recent_stock_logs,
        'low_items': low_items,
        'top_categories': top_categories,
        # Suppliers
        'total_suppliers': total_suppliers,
        'pending_orders': pending_orders,
        # AI
        'ai_suggestions': ai_suggestions,
    }
    return render(request, 'dashboard/main_dashboard.html', context)


# ──────────────────────────────────────────────
# INVENTORY (LIST)
# ──────────────────────────────────────────────

def inventory(request):
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    qs = Product.objects.select_related('category', 'shop').filter(shop=current_shop).order_by('-created_at')

    # Only the active shop is relevant in this flow
    shops = Shop.objects.filter(pk=current_shop.pk)
    selected_shop = str(current_shop.pk)

    # Filter by category
    selected_category = request.GET.get('category', '')
    if selected_category:
        qs = qs.filter(category__name=selected_category)

    # Filter by status
    selected_status = request.GET.get('status', '')
    if selected_status:
        qs = qs.filter(status=selected_status)

    # Search
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(variant__icontains=q) | Q(size__icontains=q) | Q(unit__icontains=q))

    # Pagination — 10 per page
    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    if selected_shop:
        categories = Category.objects.filter(shop__id=selected_shop)
    else:
        categories = Category.objects.all()

    total_inventory_value = sum((product.price * product.stock for product in qs), Decimal('0.00'))
    total_products = paginator.count

    context = {
        'page_title': 'Inventory | Quiick AI Enterprise',
        'active_nav': 'inventory',
        'current_shop': current_shop,
        'products': page_obj,
        'categories': categories,
        'shops': shops,
        'selected_shop': selected_shop,
        'selected_category': selected_category,
        'selected_status': selected_status,
        'search_query': q,
        'total_products': total_products,
        'page_start': page_obj.start_index(),
        'page_end': page_obj.end_index(),
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'current_page': page_obj.number,
        'page_range': list(paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1)),
        'inventory_summary': {
            'total_products': total_products,
            'low_stock_count': qs.filter(status=Product.STATUS_LOW).count(),
            'out_of_stock_count': qs.filter(status=Product.STATUS_OUT).count(),
            'total_inventory_value': total_inventory_value,
        },
    }
    return render(request, 'dashboard/inventory.html', context)


# ──────────────────────────────────────────────
# PRODUCT ADD
# ──────────────────────────────────────────────

def product_add(request):
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, shop=current_shop, shop_type=current_shop.shop_type)
        if form.is_valid():
            product = form.save(commit=False)
            product.shop = current_shop
            product.save()
            messages.success(request, 'Product added successfully.')
            return redirect('dashboard:inventory')
    else:
        form = ProductForm(shop=current_shop, shop_type=current_shop.shop_type, initial={'shop': current_shop})

    context = {
        'page_title': 'Add Product | Quiick AI',
        'active_nav': 'inventory',
        'current_shop': current_shop,
        'form': form,
        'form_title': 'Add New Product',
        'submit_label': 'Add Product',
        'cancel_url': 'dashboard:inventory',
    }
    return render(request, 'dashboard/product_form.html', context)


# ──────────────────────────────────────────────
# PRODUCT EDIT
# ──────────────────────────────────────────────

def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, shop=product.shop, shop_type=product.shop.shop_type if product.shop else None)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{product.name}" updated successfully.')
            return redirect('dashboard:inventory')
    else:
        form = ProductForm(instance=product, shop=product.shop, shop_type=product.shop.shop_type if product.shop else None)

    context = {
        'page_title': f'Edit {product.name} | Quiick AI',
        'active_nav': 'inventory',
        'current_shop': current_shop,
        'form': form,
        'form_title': f'Edit Product',
        'product': product,
        'submit_label': 'Save Changes',
        'cancel_url': 'dashboard:inventory',
    }
    return render(request, 'dashboard/product_form.html', context)


# ──────────────────────────────────────────────
# PRODUCT DELETE
# ──────────────────────────────────────────────

def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'"{name}" deleted.')
    return redirect('dashboard:inventory')


# ──────────────────────────────────────────────
# AI ASSISTANT — DB-backed chat sessions
# ──────────────────────────────────────────────

def _get_or_create_active_session(request, shop):
    """Return the active ChatSession for this shop (stored in session), creating one if needed."""
    session_key = f'active_chat_session_{shop.pk}'
    session_id = request.session.get(session_key)
    if session_id:
        chat_session = ChatSession.objects.filter(id=session_id, shop=shop).first()
        if chat_session:
            return chat_session
    # Create fresh session
    chat_session = ChatSession.objects.create(shop=shop, title='New Chat')
    request.session[session_key] = str(chat_session.id)
    return chat_session


def _set_active_session(request, shop, chat_session):
    request.session[f'active_chat_session_{shop.pk}'] = str(chat_session.id)


def _process_ai_chat(request, message, shop, chat_session):
    """Send message, persist both sides, update session title."""
    # Save user message
    ChatMessage.objects.create(session=chat_session, role=ChatMessage.ROLE_USER, content=message)

    result = handle_chat_message(message, model_payload={'shop': shop.name})
    response_text = result.reply
    if result.query_preview:
        response_text = f"{response_text}\nQuery: {result.query_preview}"

    # Save AI message
    ChatMessage.objects.create(
        session=chat_session,
        role=ChatMessage.ROLE_AI,
        content=result.reply,
        intent=result.intent or '',
        query_preview=result.query_preview or '',
    )

    # Auto-title the session from first user message (first time only)
    if chat_session.title == 'New Chat':
        chat_session.title = message[:60]
        chat_session.save(update_fields=['title', 'updated_at'])
    else:
        # bump updated_at so it sorts to top
        from django.utils import timezone as tz
        ChatSession.objects.filter(pk=chat_session.pk).update(updated_at=tz.now())

    return result


def ai_assistant(request):
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    chat_session = _get_or_create_active_session(request, current_shop)
    result = None

    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        if message:
            result = _process_ai_chat(request, message, current_shop, chat_session)
        else:
            messages.error(request, 'Please enter a command for the assistant.')

    # All sessions for this shop, ordered newest first
    all_sessions = ChatSession.objects.filter(shop=current_shop).order_by('-updated_at')
    chat_messages = chat_session.messages.all()

    context = {
        'page_title': 'AI Insights | Quiick AI',
        'active_nav': 'ai_insights',
        'current_shop': current_shop,
        'chat_session': chat_session,
        'all_sessions': all_sessions,
        'chat_messages': chat_messages,
        'suggestion_chips': [
            "Show today's sales",
            'Check low stock',
            'Compare monthly growth',
            'Draft marketing email',
        ],
        'intent_result': result,
    }
    return render(request, 'dashboard/ai_assistant.html', context)


def ai_new_chat(request):
    """Create a brand-new chat session for the current shop."""
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    chat_session = ChatSession.objects.create(shop=current_shop, title='New Chat')
    _set_active_session(request, current_shop, chat_session)
    return redirect('dashboard:ai_assistant')


def ai_switch_session(request, session_id):
    """Switch active chat to an existing session."""
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    chat_session = get_object_or_404(ChatSession, id=session_id, shop=current_shop)
    _set_active_session(request, current_shop, chat_session)
    return redirect('dashboard:ai_assistant')


def ai_delete_session(request, session_id):
    """Delete a chat session (POST only)."""
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    chat_session = get_object_or_404(ChatSession, id=session_id, shop=current_shop)
    # If deleting the active one, clear it so a new one gets created on next visit
    active_key = f'active_chat_session_{current_shop.pk}'
    if request.session.get(active_key) == str(session_id):
        request.session.pop(active_key, None)
    chat_session.delete()
    return redirect('dashboard:ai_assistant')


@csrf_exempt
def ai_chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)

    if request.content_type and 'application/json' in request.content_type:
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'invalid JSON body'}, status=400)
        message = (payload.get('message') or '').strip()
    else:
        message = request.POST.get('message', '').strip()

    if not message:
        return JsonResponse({'ok': False, 'error': 'message is required'}, status=400)

    current_shop = _get_current_shop(request)
    if not current_shop:
        return JsonResponse({'ok': False, 'error': 'No active shop'}, status=400)

    chat_session = _get_or_create_active_session(request, current_shop)
    result = _process_ai_chat(request, message, current_shop, chat_session)

    return JsonResponse({
        'ok': result.error is None,
        'intent': result.intent,
        'quantity': result.quantity,
        'shop': result.shop.name if result.shop else None,
        'category': result.category.name if result.category else None,
        'product': result.product.name if result.product else None,
        'reply': result.reply,
        'query_preview': result.query_preview,
        'matched_products': result.matched_products,
        'error': result.error,
        'session_id': str(chat_session.id),
    })


# ──────────────────────────────────────────────
# SALES  (transactions + AI stock logs)
# ──────────────────────────────────────────────

def sales(request):
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    from django.utils import timezone
    today = timezone.now().date()

    tab = request.GET.get('tab', 'transactions')

    # ── Transactions tab ──
    txn_qs = Transaction.objects.select_related('customer', 'product').filter(
        product__shop=current_shop
    ).order_by('-created_at')

    selected_status = request.GET.get('status', '')
    if selected_status:
        txn_qs = txn_qs.filter(status=selected_status)

    q = request.GET.get('q', '')
    if q:
        txn_qs = txn_qs.filter(Q(txn_id__icontains=q) | Q(customer__name__icontains=q))

    total_revenue = Transaction.objects.filter(
        status=Transaction.STATUS_COMPLETED, product__shop=current_shop
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    today_count = Transaction.objects.filter(
        created_at__date=today, product__shop=current_shop
    ).count()

    txn_paginator = Paginator(txn_qs, 15)
    txn_page = txn_paginator.get_page(request.GET.get('page', 1))

    # ── AI Stock Logs tab ──
    log_qs = StockLog.objects.select_related('product', 'category').filter(
        shop=current_shop
    ).order_by('-created_at')

    log_action = request.GET.get('action', '')
    if log_action:
        log_qs = log_qs.filter(action=log_action)

    log_q = request.GET.get('lq', '')
    if log_q:
        log_qs = log_qs.filter(
            Q(product__name__icontains=log_q) | Q(note__icontains=log_q)
        )

    total_sold = StockLog.objects.filter(
        shop=current_shop, action=StockLog.ACTION_SELL
    ).aggregate(t=Sum('quantity'))['t'] or 0

    total_added = StockLog.objects.filter(
        shop=current_shop, action=StockLog.ACTION_ADD
    ).aggregate(t=Sum('quantity'))['t'] or 0

    log_paginator = Paginator(log_qs, 15)
    log_page = log_paginator.get_page(request.GET.get('lpage', 1))

    context = {
        'page_title': 'Sales | Quiick AI',
        'active_nav': 'sales',
        'current_shop': current_shop,
        'tab': tab,
        # Transactions
        'transactions': txn_page,
        'selected_status': selected_status,
        'search_query': q,
        'total_revenue': f'₹{total_revenue:,.2f}',
        'today_count': today_count,
        'total_transactions': txn_paginator.count,
        'txn_page_start': txn_page.start_index(),
        'txn_page_end': txn_page.end_index(),
        'txn_has_previous': txn_page.has_previous(),
        'txn_has_next': txn_page.has_next(),
        'txn_current_page': txn_page.number,
        'txn_page_range': list(txn_paginator.get_elided_page_range(txn_page.number, on_each_side=1, on_ends=1)),
        'status_choices': Transaction.STATUS_CHOICES,
        # AI Stock Logs
        'stock_logs': log_page,
        'log_action': log_action,
        'log_query': log_q,
        'total_sold': total_sold,
        'total_added': total_added,
        'total_logs': log_paginator.count,
        'log_page_start': log_page.start_index(),
        'log_page_end': log_page.end_index(),
        'log_has_previous': log_page.has_previous(),
        'log_has_next': log_page.has_next(),
        'log_current_page': log_page.number,
        'log_page_range': list(log_paginator.get_elided_page_range(log_page.number, on_each_side=1, on_ends=1)),
    }
    return render(request, 'dashboard/sales.html', context)


# ──────────────────────────────────────────────
# ANALYTICS
# ──────────────────────────────────────────────

def analytics(request):
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    # Category-wise product count
    category_stats = Category.objects.filter(shop=current_shop).annotate(product_count=Count('products')).order_by('-product_count')

    # Status breakdown
    status_stats = {
        'active': Product.objects.filter(shop=current_shop, status=Product.STATUS_ACTIVE).count(),
        'low_stock': Product.objects.filter(shop=current_shop, status=Product.STATUS_LOW).count(),
        'out_of_stock': Product.objects.filter(shop=current_shop, status=Product.STATUS_OUT).count(),
    }
    total = sum(status_stats.values()) or 1

    context = {
        'page_title': 'Analytics | Quiick AI',
        'active_nav': 'analytics',
        'current_shop': current_shop,
        'category_stats': category_stats,
        'status_stats': status_stats,
        'total_products': total,
        'active_pct': int(status_stats['active'] / total * 100),
        'low_pct': int(status_stats['low_stock'] / total * 100),
        'out_pct': int(status_stats['out_of_stock'] / total * 100),
    }
    return render(request, 'dashboard/analytics.html', context)


# ──────────────────────────────────────────────
# SUPPLIERS  (companies / agencies the shop buys from)
# ──────────────────────────────────────────────

def suppliers(request):
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    qs = Supplier.objects.filter(shop=current_shop).order_by('name')

    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(contact_person__icontains=q) | Q(phone__icontains=q))

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title': 'Suppliers | Quiick AI',
        'active_nav': 'customers',
        'current_shop': current_shop,
        'suppliers': page_obj,
        'search_query': q,
        'total_suppliers': paginator.count,
        'page_start': page_obj.start_index(),
        'page_end': page_obj.end_index(),
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'current_page': page_obj.number,
        'page_range': list(paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1)),
    }
    return render(request, 'dashboard/suppliers.html', context)


def supplier_add(request):
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.shop = current_shop
            supplier.save()
            messages.success(request, f'Supplier "{supplier.name}" added.')
            return redirect('dashboard:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm()

    context = {
        'page_title': 'Add Supplier | Quiick AI',
        'active_nav': 'customers',
        'current_shop': current_shop,
        'form': form,
        'form_title': 'Add New Supplier',
    }
    return render(request, 'dashboard/supplier_form.html', context)


def supplier_detail(request, pk):
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    supplier = get_object_or_404(Supplier, pk=pk, shop=current_shop)
    orders = supplier.orders.select_related('product').order_by('-created_at')

    total_orders = orders.count()
    total_spent = orders.aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00')
    pending_count = orders.filter(status=SupplierOrder.STATUS_PENDING).count()
    received_count = orders.filter(status=SupplierOrder.STATUS_RECEIVED).count()

    context = {
        'page_title': f'{supplier.name} | Quiick AI',
        'active_nav': 'customers',
        'current_shop': current_shop,
        'supplier': supplier,
        'orders': orders,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'pending_count': pending_count,
        'received_count': received_count,
    }
    return render(request, 'dashboard/supplier_detail.html', context)


def supplier_order_add(request, pk):
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    supplier = get_object_or_404(Supplier, pk=pk, shop=current_shop)

    if request.method == 'POST':
        form = SupplierOrderForm(request.POST, shop=current_shop)
        if form.is_valid():
            order = form.save(commit=False)
            order.supplier = supplier
            order.save()
            messages.success(request, f'Order {order.order_number} created.')
            return redirect('dashboard:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierOrderForm(shop=current_shop)

    context = {
        'page_title': f'New Order — {supplier.name} | Quiick AI',
        'active_nav': 'customers',
        'current_shop': current_shop,
        'supplier': supplier,
        'form': form,
    }
    return render(request, 'dashboard/supplier_order_form.html', context)


def supplier_order_update_status(request, order_pk):
    """Quick AJAX/POST to update order status."""
    current_shop, redirect_response = _require_current_shop(request)
    if redirect_response:
        return redirect_response

    order = get_object_or_404(SupplierOrder, pk=order_pk, supplier__shop=current_shop)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(SupplierOrder.STATUS_CHOICES):
            from django.utils import timezone as tz
            order.status = new_status
            if new_status == SupplierOrder.STATUS_RECEIVED:
                order.received_date = tz.now().date()
            order.save()
            messages.success(request, f'Order {order.order_number} marked as {order.get_status_display()}.')
    return redirect('dashboard:supplier_detail', pk=order.supplier.pk)


# ──────────────────────────────────────────────
# CUSTOMERS (legacy — kept for backward compat)
# ──────────────────────────────────────────────

def customers(request):
    return redirect('dashboard:suppliers')
