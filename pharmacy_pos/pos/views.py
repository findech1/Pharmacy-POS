# pos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Medicine, Inventory, Customer, Sale, Supplier, Order, Category
from .forms import *
from django.views.decorators.csrf import csrf_exempt
import json

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
    # Expiry logic
    expired = Inventory.objects.filter(expiry_date__lt=today)
    close_to_expiry = Inventory.objects.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=30))
    context = {
        'total_medicines': total_medicines,
        'total_customers': total_customers,
        'total_suppliers': total_suppliers,
        'today_sales': today_sales,
        'low_stock': low_stock,
        'recent_sales': recent_sales,
        'expired': expired,
        'close_to_expiry': close_to_expiry,
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
    customers = Customer.objects.all().order_by('name')
    
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

@csrf_exempt
@login_required
def process_sale(request):
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                customer_id = data.get('customer_id')
                payment_method = data.get('payment_method', 'cash')
                discount = float(data.get('discount_percent', 0))
                tax = float(data.get('tax_percent', 0))
                items = data.get('items', [])
            else:
                customer_id = request.POST.get('customer_id')
                payment_method = request.POST.get('payment_method', 'cash')
                discount = float(request.POST.get('discount', 0))
                tax = float(request.POST.get('tax', 0))
                items = []
                for key, value in request.POST.items():
                    if key.startswith('medicine_'):
                        medicine_id = key.split('_')[1]
                        quantity = int(value)
                        if quantity > 0:
                            items.append({
                                'medicine_id': medicine_id,
                                'quantity': quantity
                            })
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
            for item in items:
                medicine_id = item.get('medicine_id')
                quantity = int(item.get('quantity', 0))
                unit_price = float(item.get('unit_price', 0)) if 'unit_price' in item else None
                if quantity > 0 and medicine_id:
                    medicine = Medicine.objects.get(id=medicine_id)
                    if unit_price is None:
                        unit_price = float(medicine.selling_price)
                    total_price = quantity * unit_price
                    SaleItem.objects.create(
                        sale=sale,
                        medicine=medicine,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                    total_amount += total_price
            sale.total_amount = total_amount - discount + tax
            sale.save()
            return JsonResponse({'success': True, 'sale_id': sale.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

# Inventory Views
@login_required
def inventory_list(request):
    inventories = Inventory.objects.select_related('medicine').all().order_by('medicine__name')
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
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
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
    payment_method = request.GET.get('payment_method')  # new
    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)
    if payment_method:
        sales = sales.filter(payment_method=payment_method)
    paginator = Paginator(sales, 10)
    page = request.GET.get('page')
    sales = paginator.get_page(page)
    return render(request, 'pos/sales_report.html', {'sales': sales, 'payment_method': payment_method})

@login_required
def receipt(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    sale_items = sale.items.all()
    return render(request, 'pos/receipt.html', {
        'sale': sale,
        'sale_items': sale_items,
    })

@login_required
def inventory_report(request):
    # Filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category_id = request.GET.get('category')
    medicine_id = request.GET.get('medicine')
    expiry_status = request.GET.get('expiry_status')  # new
    inventories = Inventory.objects.select_related('medicine', 'medicine__category')
    if start_date:
        inventories = inventories.filter(expiry_date__gte=start_date)
    if end_date:
        inventories = inventories.filter(expiry_date__lte=end_date)
    if category_id:
        inventories = inventories.filter(medicine__category_id=category_id)
    if medicine_id:
        inventories = inventories.filter(medicine_id=medicine_id)
    if expiry_status == 'expired':
        inventories = inventories.filter(expiry_date__lt=timezone.now().date())
    elif expiry_status == 'close':
        inventories = inventories.filter(expiry_date__gte=timezone.now().date(), expiry_date__lte=timezone.now().date() + timedelta(days=30))
    # Aggregation: total stock per medicine
    stock_summary = inventories.values('medicine__name').annotate(
        total_stock=Sum('quantity')
    ).order_by('-total_stock')
    # Low stock
    low_stock = inventories.filter(quantity__lt=10)
    context = {
        'stock_summary': list(stock_summary),
        'low_stock': low_stock,
        'inventories': inventories,
        'expiry_status': expiry_status,
    }
    return render(request, 'pos/inventory_report.html', context)

@login_required
def customer_report(request):
    # Filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    customer_id = request.GET.get('customer')

    customers = Customer.objects.all()
    sales = Sale.objects.select_related('customer').all()
    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)
    if customer_id:
        sales = sales.filter(customer_id=customer_id)

    # Aggregation: total sales per customer
    customer_summary = sales.values('customer__name').annotate(
        total_sales=Sum('total_amount'),
        num_purchases=Count('id')
    ).order_by('-total_sales')

    context = {
        'customer_summary': list(customer_summary),
        'customers': customers,
        'sales': sales,
    }
    return render(request, 'pos/customer_report.html', context)

@login_required
def supplier_report(request):
    # Filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    supplier_id = request.GET.get('supplier')

    suppliers = Supplier.objects.all()
    orders = Order.objects.select_related('supplier').all()
    if start_date:
        orders = orders.filter(order_date__gte=start_date)
    if end_date:
        orders = orders.filter(order_date__lte=end_date)
    if supplier_id:
        orders = orders.filter(supplier_id=supplier_id)

    # Aggregation: total purchases per supplier
    supplier_summary = orders.values('supplier__name').annotate(
        total_purchases=Sum('total_amount'),
        num_orders=Count('id')
    ).order_by('-total_purchases')

    context = {
        'supplier_summary': list(supplier_summary),
        'suppliers': suppliers,
        'orders': orders,
    }
    return render(request, 'pos/supplier_report.html', context)

@permission_required('pos.view_financial_report', raise_exception=True)
def financial_report(request):
    # Filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    cashier_id = request.GET.get('cashier')

    sales = Sale.objects.select_related('served_by').all()
    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)
    if cashier_id:
        sales = sales.filter(served_by_id=cashier_id)

    # Aggregation: total revenue, total tax, total discount
    total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    total_tax = sales.aggregate(total=Sum('tax'))['total'] or 0
    total_discount = sales.aggregate(total=Sum('discount'))['total'] or 0
    num_sales = sales.count()

    # Revenue by cashier
    cashier_summary = sales.values('served_by__username').annotate(
        total_sales=Sum('total_amount'),
        num_sales=Count('id')
    ).order_by('-total_sales')

    context = {
        'total_revenue': total_revenue,
        'total_tax': total_tax,
        'total_discount': total_discount,
        'num_sales': num_sales,
        'cashier_summary': list(cashier_summary),
        'sales': sales,
    }
    return render(request, 'pos/financial_report.html', context)