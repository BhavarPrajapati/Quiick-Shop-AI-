from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid


class Shop(models.Model):
    TYPE_GROCERY = 'grocery'
    TYPE_CLOTHS = 'cloths'
    TYPE_ELECTRONICS = 'electronics'
    TYPE_CHOICES = [
        (TYPE_GROCERY, 'Grocery'),
        (TYPE_CLOTHS, 'Cloths'),
        (TYPE_ELECTRONICS, 'Electronics'),
    ]

    name = models.CharField(max_length=200, unique=True)
    shop_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_ELECTRONICS)
    owner_name = models.CharField(max_length=200, blank=True, default='')
    phone_number = models.CharField(max_length=30, blank=True, default='')
    address = models.CharField(max_length=400, blank=True, default='')
    complete_address = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def shop_type_label(self):
        return dict(self.TYPE_CHOICES).get(self.shop_type, 'Electronics')

    @property
    def is_grocery(self):
        return self.shop_type == self.TYPE_GROCERY

    @property
    def is_cloths(self):
        return self.shop_type == self.TYPE_CLOTHS

    @property
    def is_electronics(self):
        return self.shop_type == self.TYPE_ELECTRONICS


class Category(models.Model):
    name = models.CharField(max_length=100)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='categories', null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
        unique_together = ('shop', 'name')

    def __str__(self):
        return self.name


class Product(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_LOW = 'low_stock'
    STATUS_OUT = 'out_of_stock'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_LOW, 'Low Stock'),
        (STATUS_OUT, 'Out of Stock'),
    ]

    name = models.CharField(max_length=255)
    variant = models.CharField(max_length=255, blank=True, default='')
    size = models.CharField(max_length=50, blank=True, default='')
    unit = models.CharField(max_length=30, blank=True, default='')
    sku = models.CharField(max_length=100, unique=True)
    shop = models.ForeignKey(Shop, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-set status based on stock level
        if self.stock == 0:
            self.status = self.STATUS_OUT
        elif self.stock <= self.low_stock_threshold:
            self.status = self.STATUS_LOW
        else:
            self.status = self.STATUS_ACTIVE
        super().save(*args, **kwargs)

    @property
    def stock_percent(self):
        """Returns stock as a percentage relative to 100 (reference max)."""
        if self.stock == 0:
            return 0
        # Treat 100 units as 100%, cap at 100
        return min(int((self.stock / 100) * 100), 100)

    @property
    def status_color(self):
        mapping = {
            self.STATUS_ACTIVE: 'emerald',
            self.STATUS_LOW: 'amber',
            self.STATUS_OUT: 'error',
        }
        return mapping.get(self.status, 'outline')

    @property
    def size_display(self):
        if not self.size:
            return '—'
        if self.unit:
            return f'{self.size} {self.unit}'
        return self.size


class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

    @property
    def initials(self):
        parts = self.name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.name[:2].upper()


class Transaction(models.Model):
    STATUS_COMPLETED = 'Completed'
    STATUS_PROCESSING = 'Processing'
    STATUS_SHIPPED = 'Shipped'
    STATUS_CANCELLED = 'Cancelled'
    STATUS_CHOICES = [
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    txn_id = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name='transactions')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PROCESSING)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.txn_id:
            last = Transaction.objects.order_by('-id').first()
            next_num = (last.id + 1) if last else 1
            self.txn_id = f'#SHP-{90000 + next_num}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.txn_id


# ──────────────────────────────────────────────
# CHAT SESSION & MESSAGES
# ──────────────────────────────────────────────

class ChatSession(models.Model):
    """One conversation thread, scoped to a shop."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=200, default='New Chat')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.shop.name} — {self.title}'

    @property
    def preview(self):
        """Last AI message content truncated to 60 chars."""
        last = self.messages.filter(role='ai').last()
        if last:
            return last.content[:60] + ('…' if len(last.content) > 60 else '')
        return 'No messages yet'


class ChatMessage(models.Model):
    ROLE_USER = 'user'
    ROLE_AI = 'ai'
    ROLE_CHOICES = [(ROLE_USER, 'User'), (ROLE_AI, 'AI')]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    intent = models.CharField(max_length=50, blank=True, default='')
    query_preview = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'[{self.role}] {self.content[:40]}'


# ──────────────────────────────────────────────
# STOCK LOG  (AI chatbot actions)
# ──────────────────────────────────────────────

class StockLog(models.Model):
    ACTION_SELL = 'sell'
    ACTION_ADD  = 'add'
    ACTION_CHOICES = [
        (ACTION_SELL, 'Sell'),
        (ACTION_ADD,  'Restock / Add'),
    ]

    shop        = models.ForeignKey(Shop,     on_delete=models.CASCADE,  related_name='stock_logs')
    product     = models.ForeignKey(Product,  on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_logs')
    category    = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_logs')
    action      = models.CharField(max_length=10, choices=ACTION_CHOICES)
    quantity    = models.PositiveIntegerField()
    stock_before= models.IntegerField(default=0)
    stock_after = models.IntegerField(default=0)
    note        = models.TextField(blank=True, default='')   # AI reply summary
    created_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} {self.quantity} — {self.product} @ {self.shop}'

    @property
    def amount(self):
        """Estimated value moved = qty × product price."""
        if self.product and self.product.price:
            return self.quantity * self.product.price
        return Decimal('0.00')


# ──────────────────────────────────────────────
# SUPPLIER  (companies / agencies shop buys from)
# ──────────────────────────────────────────────

class Supplier(models.Model):
    shop            = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='suppliers')
    name            = models.CharField(max_length=255)
    contact_person  = models.CharField(max_length=255, blank=True, default='')
    phone           = models.CharField(max_length=30,  blank=True, default='')
    email           = models.EmailField(blank=True, default='')
    address         = models.TextField(blank=True, default='')
    gst_number      = models.CharField(max_length=20, blank=True, default='')
    notes           = models.TextField(blank=True, default='')
    created_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['name']
        unique_together = ('shop', 'name')

    def __str__(self):
        return self.name

    @property
    def initials(self):
        parts = self.name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.name[:2].upper()

    @property
    def total_orders(self):
        return self.orders.count()

    @property
    def total_spent(self):
        return self.orders.aggregate(t=models.Sum('total_amount'))['t'] or Decimal('0.00')


class SupplierOrder(models.Model):
    STATUS_PENDING   = 'pending'
    STATUS_RECEIVED  = 'received'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_RECEIVED,  'Received'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    supplier        = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='orders')
    order_number    = models.CharField(max_length=30, unique=True, editable=False)
    product         = models.ForeignKey(Product,  on_delete=models.SET_NULL, null=True, blank=True, related_name='supplier_orders')
    product_name    = models.CharField(max_length=255, blank=True, default='')   # free-text fallback
    quantity        = models.PositiveIntegerField()
    unit_price      = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount    = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    expected_date   = models.DateField(null=True, blank=True)
    received_date   = models.DateField(null=True, blank=True)
    notes           = models.TextField(blank=True, default='')
    created_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        self.total_amount = Decimal(str(self.quantity)) * self.unit_price
        if not self.order_number:
            last = SupplierOrder.objects.order_by('-id').first()
            next_num = (last.id + 1) if last else 1
            self.order_number = f'PO-{10000 + next_num}'
        if not self.product_name and self.product:
            self.product_name = self.product.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number

