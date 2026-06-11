from django.shortcuts import render, redirect

from dashboard.forms import ShopSetupForm
from dashboard.models import Shop


def landing_page(request):
    """
    Public landing page — Quiick AI marketing / home screen.
    """
    context = {
        'page_title': 'Quiick AI | Aesthetic Intelligence for Commerce',
    }
    return render(request, 'core/landing.html', context)


def onboarding_start(request):
    shop_types = [
        {
            'value': Shop.TYPE_GROCERY,
            'title': 'Grocery',
            'description': 'Daily essentials, food items, and fast-moving stock.',
        },
        {
            'value': Shop.TYPE_CLOTHS,
            'title': 'Cloths',
            'description': 'Apparel, fashion, sizes, and seasonal collections.',
        },
        {
            'value': Shop.TYPE_ELECTRONICS,
            'title': 'Electronics',
            'description': 'Devices, accessories, gadgets, and serial-driven stock.',
        },
    ]

    if request.method == 'POST':
        selected_type = request.POST.get('shop_type', '').strip()
        allowed = {item['value'] for item in shop_types}
        if selected_type in allowed:
            request.session['selected_shop_type'] = selected_type
            return redirect('core:onboarding_details')

    context = {
        'page_title': 'Select Your Shop | Quiick AI',
        'shop_types': shop_types,
    }
    return render(request, 'core/onboarding_start.html', context)


def onboarding_details(request):
    selected_type = request.session.get('selected_shop_type')
    if not selected_type:
        return redirect('core:onboarding_start')

    if request.method == 'POST':
        form = ShopSetupForm(request.POST)
        if form.is_valid():
            shop = form.save(commit=False)
            shop.shop_type = selected_type
            shop.address = shop.complete_address
            shop.save()
            request.session['current_shop_id'] = shop.id
            request.session.pop('selected_shop_type', None)
            return redirect('dashboard:main')
    else:
        form = ShopSetupForm()

    shop_type_label = dict(Shop.TYPE_CHOICES).get(selected_type, 'Electronics')
    context = {
        'page_title': 'Set Up Your Shop | Quiick AI',
        'selected_type': selected_type,
        'shop_type_label': shop_type_label,
        'form': form,
    }
    return render(request, 'core/onboarding_details.html', context)
