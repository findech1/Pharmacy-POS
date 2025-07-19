from django.contrib import admin
from .models import Medicine, Category, Customer, Supplier, Sale, SaleItem

admin.site.register(Medicine)
admin.site.register(Category)
admin.site.register(Customer)
admin.site.register(Supplier)
admin.site.register(Sale)