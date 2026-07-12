# pos/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add-user/', views.add_user, name='add_user'),
    path('switch-branch/<int:branch_id>/', views.switch_branch, name='switch_branch'),
    path('audit-log/', views.audit_log_list, name='audit_log_list'),

    # Medicine URLs
    path('medicines/', views.medicine_list, name='medicine_list'),
    path('medicines/add/', views.medicine_add, name='medicine_add'),
    path('medicines/edit/<int:pk>/', views.medicine_edit, name='medicine_edit'),

    # Customer URLs
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.customer_add, name='customer_add'),
    path('customers/edit/<int:pk>/', views.customer_edit, name='customer_edit'),

    # POS URLs
    path('pos/', views.pos_sale, name='pos_sale'),
    path('pos/process/', views.process_sale, name='process_sale'),

    # Inventory URLs
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/add/', views.inventory_add, name='inventory_add'),
    path('inventory/edit/<int:pk>/', views.inventory_edit, name='inventory_edit'),

    # Category URLs
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/edit/<int:pk>/', views.category_edit, name='category_edit'),

    # Supplier URLs
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_add, name='supplier_add'),
    path('suppliers/edit/<int:pk>/', views.supplier_edit, name='supplier_edit'),

    # Reports URLs
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/inventory/', views.inventory_report, name='inventory_report'),
    path('reports/customers/', views.customer_report, name='customer_report'),
    path('reports/suppliers/', views.supplier_report, name='supplier_report'),
    path('reports/financial/', views.financial_report, name='financial_report'),
    path('receipt/<int:sale_id>/', views.receipt, name='receipt'),

    # Prescription URLs
    path('prescriptions/', views.prescription_list, name='prescription_list'),
    path('prescriptions/add/', views.prescription_add, name='prescription_add'),
    path('prescriptions/<int:pk>/', views.prescription_detail, name='prescription_detail'),
    path('prescriptions/item/<int:item_id>/dispense/', views.dispense_item, name='dispense_item'),
]
