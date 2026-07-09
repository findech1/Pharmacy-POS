from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class Branch(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)  # e.g. KNG, KWG, KIB, BGM
    location = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'System Admin'),
        ('branch_manager', 'Branch Manager'),
        ('pharmacist', 'Pharmacist'),
        ('cashier', 'Cashier'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, null=True, blank=True, related_name='staff')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier')

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    def get_accessible_branches(self):
        if self.role == 'admin':
            return Branch.objects.filter(is_active=True)
        return Branch.objects.filter(id=self.branch_id, is_active=True) if self.branch_id else Branch.objects.none()


class Category(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(max_length=100)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Medicine(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    description = models.TextField(blank=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def total_quantity(self):
        return sum(inv.quantity for inv in self.inventory_set.all())


class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Inventory(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='inventory_items', null=True, blank=True)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(0)])
    expiry_date = models.DateField()
    batch_number = models.CharField(max_length=50, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Inventories"

    def __str__(self):
        branch_code = self.branch.code if self.branch_id else 'N/A'
        return f"{self.medicine.name} - {self.quantity} units ({branch_code})"


class Order(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    order_date = models.DateField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.supplier.name}"


class Sale(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='sales', null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    sale_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=[
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mobile', 'MPESA'),
        ('split', 'Split Payment'),
    ], default='cash')
    notes = models.TextField(blank=True, default='')
    served_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale #{self.id} - {self.sale_date.strftime('%Y-%m-%d')}"

    @property
    def payment_summary(self):
        payments = self.payments.all()
        if payments.count() <= 1:
            if payments.exists():
                p = payments.first()
                ref = f" ({p.reference_number})" if p.reference_number else ''
                return f"{p.get_payment_method_display()}{ref}"
            return self.get_payment_method_display()
        return ", ".join(
            f"{p.get_payment_method_display()} Ksh {p.amount:.2f}{(' (' + p.reference_number + ')' if p.reference_number else '')}"
            for p in payments
        )


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mobile', 'MPESA'),
    ]
    sale = models.ForeignKey('Sale', on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    reference_number = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_payment_method_display()} - Ksh {self.amount:.2f}"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        from django.db import transaction
        self.total_price = self.quantity * self.unit_price
        is_new = self._state.adding
        with transaction.atomic():
            super().save(*args, **kwargs)
            if is_new:
                qty_to_deduct = self.quantity
                inventories = Inventory.objects.filter(
                    branch=self.sale.branch,
                    medicine=self.medicine,
                    quantity__gt=0,
                    expiry_date__gte=models.functions.Now()
                ).order_by('expiry_date')
                for inv in inventories:
                    if qty_to_deduct <= 0:
                        break
                    deduct = min(inv.quantity, qty_to_deduct)
                    inv.quantity -= deduct
                    inv.save()
                    qty_to_deduct -= deduct
                if qty_to_deduct > 0:
                    raise ValueError(f"Not enough stock for {self.medicine.name} at {self.sale.branch}")

    def __str__(self):
        return f"{self.medicine.name} x {self.quantity}"