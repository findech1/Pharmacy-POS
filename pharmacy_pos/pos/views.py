# pos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from .models import *
from .forms import *

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'registration/login.html')

@login_required
def dashboard(request):
    # Get dashboard statistics
    total_medicines = Medicine.objects.filter(is_active=True).count()
    total_customers = Customer.objects.count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()
    
    # Sales statistics
    today = timezone.now().date()
    today_sales = Sale.objects.filter(sale_date__date=today).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Low stock items (less than 10 units)
    low_stock = Medicine.objects.filter(
        inventory__quantity__lt=10,
        is_active=True
    ).distinct()
    
    # Recent sales
    recent_sales = Sale.objects.order_by('-sale_date')[:5]
    
    context = {
        'total_medicines': total_medicines,
        'total_customers': total_customers,
        'total_suppliers': total_suppliers,
        'today_sales': today_sales,
        'low_stock': low_stock,
        'recent_sales': recent_sales,
    }
    return render(request, 'pos/dashboard.html', context)

@login_required
def add_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'User created successfully!')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'pos/add_user.html', {'form': form})

# Medicine Views
@login_required
def medicine_list(request):
    search_query = request.GET.get('search', '')
    medicines = Medicine.objects.filter(is_active=True)
    
    if search_query:
        medicines = medicines.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    paginator = Paginator(medicines, 10)
    page = request.GET.get('page')
    medicines = paginator.get_page(page)
    
    return render(request, 'pos/medicine_list.html', {
        'medicines': medicines,
        'search_query': search_query
    })

@login_required
def medicine_add(request):
    if request.method == 'POST':
        form = MedicineForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicine added successfully!')
            return redirect('medicine_list')
    else:
        form = MedicineForm()
    return render(request, 'pos/medicine_form.html', {'form': form, 'title': 'Add Medicine'})

@login_required
def medicine_edit(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicine updated successfully!')
            return redirect('medicine_list')
    else:
        form = MedicineForm(instance=medicine)
    return render(request, 'pos/medicine_form.html', {'form': form, 'title': 'Edit Medicine'})

# Customer Views
@login_required
def customer_list(request):
    search_query = request.GET.get('search', '')
    customers = Customer.objects.all()
    
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) ,
            Q(phone__icontains=search_query) ,
            Q(email__icontains=search_query),
        )
    
    paginator = Paginator(customers, 10)
    page = request.GET.get('page')
    customers = paginator.get_page(page)
    
    return render(request, 'pos/customer_list.html', {
        'customers': customers,
        'search_query': search_query
    })

@login_required
def customer_add(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer added successfully!')
            return redirect('customer_list')
    else:
        form = CustomerForm()
    return render(request, 'pos/customer_form.html', {'form': form, 'title': 'Add Customer'})

# POS/Sales Views
@login_required
def pos_sale(request):
    medicines = Medicine.objects.filter(is_active=True)
    customers = Customer.objects.all()
    return render(request, 'pos/pos_sale.html', {
        'medicines': medicines,
        'customers': customers
    })

@login_required
def process_sale(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        payment_method = request.POST.get('payment_method', 'cash')
        discount = float(request.POST.get('discount', 0))
        tax = float(request.POST.get('tax', 0))
        
        # Create sale
        sale = Sale.objects.create(
            customer_id=customer_id if customer_id else None,
            payment_method=payment_method,
            discount=discount,
            tax=tax,
            served_by=request.user
        )
        
        total_amount = 0
        
        # Process sale items
        for key, value in request.POST.items():
            if key.startswith('medicine_'):
                medicine_id = key.split('_')[1]
                quantity = int(value)
                
                if quantity > 0:
                    medicine = Medicine.objects.get(id=medicine_id)
                    unit_price = medicine.price
                    total_price = quantity * unit_price
                    
                    # Create sale item
                    SaleItem.objects.create(
                        sale=sale,
                        medicine=medicine,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                    
                    total_amount += total_price
        
        # Update sale total
        sale.total_amount = total_amount - discount + tax
        sale.save()
        
        messages.success(request, f'Sale completed successfully! Sale ID: {sale.id}')
        return redirect('pos_sale')
    
    return redirect('pos_sale')

# Inventory Views
@login_required
def inventory_list(request):
    inventories = Inventory.objects.select_related('medicine').all()
    return render(request, 'pos/inventory_list.html', {'inventories': inventories})

@login_required
def inventory_add(request):
    if request.method == 'POST':
        form = InventoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inventory added successfully!')
            return redirect('inventory_list')
    else:
        form = InventoryForm()
    return render(request, 'pos/inventory_form.html', {'form': form, 'title': 'Add Inventory'})

# Category Views
@login_required
def category_list(request):
    categories = Category.objects.filter(is_active=True)
    return render(request, 'pos/category_list.html', {'categories': categories})

@login_required
def category_add(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category added successfully!')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'pos/category_form.html', {'form': form, 'title': 'Add Category'})

# Supplier Views
@login_required
def supplier_list(request):
    suppliers = Supplier.objects.filter(is_active=True)
    return render(request, 'pos/supplier_list.html', {'suppliers': suppliers})

@login_required
def supplier_add(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier added successfully!')
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'pos/supplier_form.html', {'form': form, 'title': 'Add Supplier'})

# Sales Report Views
@login_required
def sales_report(request):
    sales = Sale.objects.order_by('-sale_date')
    
    # Filter by date range if provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)
    
    paginator = Paginator(sales, 10)
    page = request.GET.get('page')
    sales = paginator.get_page(page)
    
    return render(request, 'pos/sales_report.html', {'sales': sales})