from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from datetime import timedelta
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
        ('inventory_manager', 'Inventory Manager'),
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
    generic_name = models.CharField(max_length=150, blank=True, help_text="Clinical/active-ingredient name.")
    is_controlled_substance = models.BooleanField(default=False)
    barcode = models.CharField(max_length=50, blank=True, unique=True, null=True, help_text="Scannable SKU/barcode identifier.")
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
    reorder_level = models.PositiveIntegerField(default=10, help_text="Triggers low-stock alert when quantity falls at or below this.")
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

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()


class Order(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='orders', null=True, blank=True)
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


# ---------------------------------------------------------------------------
# Patient Profile & Prescription Lifecycle Management (SRS Section 3.3)
# ---------------------------------------------------------------------------

doctor_license_validator = RegexValidator(
    regex=r'^[A-Z]{2,4}-\d{4,8}$',
    message="Doctor license must match the format XX-NNNNN (e.g., PPB-102345)."
)


class DrugInteraction(models.Model):
    SEVERITY_CHOICES = [
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ]
    medicine_a = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='interactions_as_a')
    medicine_b = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='interactions_as_b')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='moderate')
    description = models.TextField(help_text="Clinical explanation of the interaction risk.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('medicine_a', 'medicine_b')

    def clean(self):
        if self.medicine_a_id == self.medicine_b_id:
            raise DjangoValidationError("A medicine cannot interact with itself.")

    def __str__(self):
        return f"{self.medicine_a.name} \u26a0 {self.medicine_b.name} ({self.severity})"

    @staticmethod
    def check_interaction(medicine_a_id, medicine_b_id):
        """Returns the DrugInteraction record if these two medicines interact, else None."""
        return DrugInteraction.objects.filter(
            models.Q(medicine_a_id=medicine_a_id, medicine_b_id=medicine_b_id) |
            models.Q(medicine_a_id=medicine_b_id, medicine_b_id=medicine_a_id)
        ).first()


class Prescription(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='prescriptions')
    patient = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='prescriptions')
    doctor_name = models.CharField(max_length=100)
    doctor_license_number = models.CharField(max_length=20, validators=[doctor_license_validator])
    diagnosis_notes = models.TextField(blank=True)
    validated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='validated_prescriptions')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prescription #{self.id} - {self.patient.name} ({self.created_at.strftime('%Y-%m-%d')})"

    def has_controlled_substances(self):
        return self.items.filter(medicine__is_controlled_substance=True).exists()


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    dosage_instructions = models.CharField(max_length=255)
    quantity_per_refill = models.PositiveIntegerField()
    refill_interval_days = models.PositiveIntegerField(default=30, help_text="Days between authorized refills.")
    total_refills_allowed = models.PositiveIntegerField(default=1)
    refills_used = models.PositiveIntegerField(default=0)
    last_dispensed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.medicine.name} \u2014 {self.dosage_instructions}"

    @property
    def refills_remaining(self):
        return max(self.total_refills_allowed - self.refills_used, 0)

    def can_dispense_now(self):
        """REQ-MED-3.3: locks refill actions until the authorized interval has passed."""
        if self.refills_remaining <= 0:
            return False, "No refills remaining on this prescription item."
        if self.last_dispensed_at is None:
            return True, None
        next_allowed = self.last_dispensed_at + timedelta(days=self.refill_interval_days)
        if timezone.now() < next_allowed:
            return False, f"Next refill not authorized until {next_allowed.strftime('%Y-%m-%d')}."
        return True, None

    def check_interactions_against_active_history(self):
        """
        REQ-MED-3.2: checks this medicine against the patient's other prescriptions
        dispensed within the last 30 days. Returns a list of (other_item, interaction) tuples.
        """
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_items = PrescriptionItem.objects.filter(
            prescription__patient=self.prescription.patient,
            last_dispensed_at__gte=thirty_days_ago,
        ).exclude(id=self.id).exclude(medicine_id=self.medicine_id)

        flagged = []
        for other in recent_items:
            interaction = DrugInteraction.check_interaction(self.medicine_id, other.medicine_id)
            if interaction:
                flagged.append((other, interaction))
        return flagged


class DispensingLog(models.Model):
    """Immutable ledger - one row per actual dispensing event (the 'Dispensary Release' action)."""
    prescription_item = models.ForeignKey(PrescriptionItem, on_delete=models.PROTECT, related_name='dispensing_logs')
    quantity_dispensed = models.PositiveIntegerField()
    dispensed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='dispensing_actions')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='dispensing_logs')
    sale = models.ForeignKey(Sale, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispensing_logs')
    interaction_warning_acknowledged = models.BooleanField(default=False)
    dispensed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dispensed {self.quantity_dispensed}x {self.prescription_item.medicine.name}"