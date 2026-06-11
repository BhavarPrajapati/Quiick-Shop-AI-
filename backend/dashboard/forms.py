from django import forms
from .models import Product, Category, Shop, Supplier, SupplierOrder


class ShopSetupForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = ['owner_name', 'phone_number', 'name', 'complete_address']
        widgets = {
            'owner_name': forms.TextInput(attrs={
                'placeholder': 'Your full name',
                'class': 'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none transition-all',
            }),
            'phone_number': forms.TextInput(attrs={
                'placeholder': 'Mobile number',
                'class': 'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none transition-all',
            }),
            'name': forms.TextInput(attrs={
                'placeholder': 'Store name',
                'class': 'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none transition-all',
            }),
            'complete_address': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Complete shop address with landmark, city and pincode',
                'class': 'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none transition-all',
            }),
        }


class ProductForm(forms.ModelForm):
    GROCERY_UNIT_CHOICES = [
        ('kg', 'Kilogram (kg)'),
        ('g', 'Gram (g)'),
        ('l', 'Litre (l)'),
        ('ml', 'Millilitre (ml)'),
        ('pcs', 'Pieces'),
        ('pack', 'Pack'),
    ]
    CLOTH_SIZE_CHOICES = [
        ('XS', 'XS'),
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
        ('Free Size', 'Free Size'),
    ]
    ELECTRONICS_UNIT_CHOICES = [
        ('inch', 'Inch'),
        ('cm', 'Centimetre'),
        ('pcs', 'Pieces'),
        ('unit', 'Unit'),
    ]

    # Allow creating a new category inline
    new_category = forms.CharField(
        max_length=100,
        required=False,
        label='Or create new category',
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Networking',
            'class': (
                'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                'outline-none transition-all'
            ),
        }),
    )

    size = forms.CharField(
        max_length=50,
        required=False,
        label='Size',
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. 500, M, 14',
            'class': (
                'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                'outline-none transition-all'
            ),
        }),
    )

    unit = forms.ChoiceField(
        required=False,
        label='Unit',
        choices=[('', 'Select unit')],
        widget=forms.Select(attrs={
            'class': (
                'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                'outline-none transition-all'
            ),
        }),
    )

    def __init__(self, *args, **kwargs):
        shop = kwargs.pop('shop', None)
        shop_type = kwargs.pop('shop_type', None)
        super().__init__(*args, **kwargs)

        self.shop = shop
        self.shop_type = shop_type or getattr(shop, 'shop_type', None)

        self.fields['shop'].required = True
        if shop:
            self.fields['shop'].queryset = Shop.objects.filter(pk=shop.pk)
            self.fields['shop'].initial = shop
        else:
            self.fields['shop'].queryset = Shop.objects.all()

        if shop:
            self.fields['category'].queryset = Category.objects.filter(shop=shop).order_by('name')
        elif self.instance and getattr(self.instance, 'shop_id', None):
            self.fields['category'].queryset = Category.objects.filter(shop_id=self.instance.shop_id).order_by('name')

        self._configure_size_fields()

    class Meta:
        model = Product
        fields = ['shop', 'name', 'variant', 'size', 'unit', 'sku', 'category', 'price', 'stock', 'low_stock_threshold', 'image']
        widgets = {
            'shop': forms.Select(attrs={
                'class': (
                    'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                    'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                    'outline-none transition-all'
                ),
            }),
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g. MacBook Pro M3 Max',
                'class': (
                    'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                    'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                    'outline-none transition-all'
                ),
            }),
            'variant': forms.TextInput(attrs={
                'placeholder': 'e.g. Space Black, 64GB RAM',
                'class': (
                    'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                    'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                    'outline-none transition-all'
                ),
            }),
            'sku': forms.TextInput(attrs={
                'placeholder': 'e.g. APP-MBP-14-BK',
                'class': (
                    'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                    'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                    'outline-none transition-all font-mono'
                ),
            }),
            'category': forms.Select(attrs={
                'class': (
                    'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                    'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                    'outline-none transition-all'
                ),
            }),
            'price': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'class': (
                    'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                    'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                    'outline-none transition-all'
                ),
            }),
            'stock': forms.NumberInput(attrs={
                'placeholder': '0',
                'min': '0',
                'class': (
                    'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                    'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                    'outline-none transition-all'
                ),
            }),
            'low_stock_threshold': forms.NumberInput(attrs={
                'placeholder': '10',
                'min': '1',
                'class': (
                    'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                    'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                    'outline-none transition-all'
                ),
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': (
                    'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                    'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                    'outline-none transition-all file:mr-4 file:py-1 file:px-3 file:rounded-lg '
                    'file:border-0 file:text-body-sm file:font-medium file:bg-primary file:text-on-primary '
                    'hover:file:opacity-90'
                ),
            }),
        }

    def _configure_size_fields(self):
        if self.shop_type == Shop.TYPE_GROCERY:
            self.fields['size'].label = 'Pack / Quantity'
            self.fields['size'].widget = forms.NumberInput(attrs={
                'placeholder': 'e.g. 500',
                'min': '0',
                'class': (
                    'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                    'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                    'outline-none transition-all'
                ),
            })
            self.fields['unit'].choices = [('', 'Select unit')] + self.GROCERY_UNIT_CHOICES
        elif self.shop_type == Shop.TYPE_CLOTHS:
            self.fields['size'].label = 'Cloth Size'
            self.fields['size'] = forms.ChoiceField(
                required=False,
                choices=[('', 'Select size')] + self.CLOTH_SIZE_CHOICES,
                widget=forms.Select(attrs={
                    'class': (
                        'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
                        'rounded-xl text-body-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
                        'outline-none transition-all'
                    ),
                }),
            )
            self.fields['unit'].choices = [('', 'Select unit'), ('size', 'Size')]
            self.fields['unit'].initial = 'size'
        else:
            self.fields['size'].label = 'Model / Size'
            self.fields['unit'].choices = [('', 'Select unit')] + self.ELECTRONICS_UNIT_CHOICES

    def clean(self):
        cleaned = super().clean()
        new_cat = cleaned.get('new_category', '').strip()
        shop = cleaned.get('shop') or self.shop

        if shop and not cleaned.get('shop'):
            cleaned['shop'] = shop

        # If user typed a new category name, create or get it
        if new_cat:
            if shop:
                cat_obj, _ = Category.objects.get_or_create(name=new_cat, shop=shop)
            else:
                cat_obj, _ = Category.objects.get_or_create(name=new_cat)
            cleaned['category'] = cat_obj

        return cleaned


_INPUT = (
    'w-full px-4 py-3 bg-surface-container-low border border-outline-variant/40 '
    'rounded-xl text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary '
    'outline-none transition-all'
)


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 'address', 'gst_number', 'notes']
        widgets = {
            'name':           forms.TextInput(attrs={'placeholder': 'Company / Agency name', 'class': _INPUT}),
            'contact_person': forms.TextInput(attrs={'placeholder': 'Contact person name',   'class': _INPUT}),
            'phone':          forms.TextInput(attrs={'placeholder': 'Phone number',           'class': _INPUT}),
            'email':          forms.EmailInput(attrs={'placeholder': 'Email address',         'class': _INPUT}),
            'address':        forms.Textarea(attrs={'rows': 3, 'placeholder': 'Full address', 'class': _INPUT}),
            'gst_number':     forms.TextInput(attrs={'placeholder': 'GST number (optional)',  'class': _INPUT}),
            'notes':          forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any additional notes', 'class': _INPUT}),
        }


class SupplierOrderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        shop = kwargs.pop('shop', None)
        super().__init__(*args, **kwargs)
        if shop:
            self.fields['product'].queryset = Product.objects.filter(shop=shop).order_by('name')
        self.fields['product'].required = False

    class Meta:
        model = SupplierOrder
        fields = ['product', 'product_name', 'quantity', 'unit_price', 'status', 'expected_date', 'notes']
        widgets = {
            'product':       forms.Select(attrs={'class': _INPUT}),
            'product_name':  forms.TextInput(attrs={'placeholder': 'Or type product name manually', 'class': _INPUT}),
            'quantity':      forms.NumberInput(attrs={'min': '1', 'placeholder': '0', 'class': _INPUT}),
            'unit_price':    forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'placeholder': '0.00', 'class': _INPUT}),
            'status':        forms.Select(attrs={'class': _INPUT}),
            'expected_date': forms.DateInput(attrs={'type': 'date', 'class': _INPUT}),
            'notes':         forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes', 'class': _INPUT}),
        }

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('product') and not cleaned.get('product_name', '').strip():
            self.add_error('product_name', 'Provide a product or enter a product name.')
        return cleaned
