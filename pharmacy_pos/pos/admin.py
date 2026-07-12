from django.contrib import admin
from .models import (
    Medicine, Category, Customer, Supplier, Sale, SaleItem,
    Branch, UserProfile, Inventory, Order, OrderItem,
    DrugInteraction, Prescription, PrescriptionItem, DispensingLog, AuditLog
)

admin.site.register(Medicine)
admin.site.register(Category)
admin.site.register(Customer)
admin.site.register(Supplier)
admin.site.register(Sale)
admin.site.register(Branch)
admin.site.register(UserProfile)
admin.site.register(Inventory)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(DrugInteraction)
admin.site.register(Prescription)
admin.site.register(PrescriptionItem)
admin.site.register(DispensingLog)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only in admin, satisfying the 'unalterable audit trail' requirement."""
    list_display = ('timestamp', 'user', 'branch', 'action', 'model_name', 'object_repr')
    list_filter = ('action', 'branch', 'timestamp')
    search_fields = ('user__username', 'object_repr', 'details')
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    