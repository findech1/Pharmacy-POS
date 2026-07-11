from django.contrib import admin
from .models import (
    Medicine, Category, Customer, Supplier, Sale, SaleItem,
    Branch, UserProfile, Inventory, Order,
    DrugInteraction, Prescription, PrescriptionItem, DispensingLog
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
admin.site.register(DrugInteraction)
admin.site.register(Prescription)
admin.site.register(PrescriptionItem)
admin.site.register(DispensingLog)
