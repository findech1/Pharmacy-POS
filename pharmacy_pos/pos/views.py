from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate, TruncMonth
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Medicine, Inventory, Customer, Sale, Supplier, Order, Category, Payment, Branch, SaleItem
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
    total_medicines = Medicine.objects.filter(is_active=True).count()
    total_customers = Customer.objects.count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()
    today = timezone.now().date()

    branch_filter = {} if request.active_branch_id is None else {'branch_id': request.active_branch_id}

    today_sales = Sale.objects.filter(sale_date__date=today, **branch_filter).aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    low_stock_inv_filter = {} if request.active_branch_id is None else {'inventory__branch_id': request.active_branch_id}
    low_stock = Medicine.objects.filter(
        inventory__quantity__lt=10,
        is_active=True,
        **low_stock_inv_filter
    ).distinct()

    recent_sales = Sale.objects.filter(**branch_filter).order_by('-sale_date')[:5]

    expired = Inventory.objects.filter(expiry_date__lt=today, **branch_filter)
    close_to_expiry = Inventory.objects.filter(
        expiry_date__gte=today, expiry_date__lte=today + timedelta(days=30), **branch_filter
    )

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


@login_required
def switch_branch(request, branch_id):
    profile = request.user.profile

    if branch_id == 0:
        if profile.role == 'admin':
            request.session['active_branch_id'] = None
            messages.success(request, 'Now viewing: All Branches')
        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

    if profile.role == 'admin' or profile.get_accessible_branches().filter(id=branch_id).exists():
        request.session['active_branch_id'] = branch_id
        branch = Branch.objects.get(id=branch_id)
        messages.success(request, f'Now viewing: {branch.name}')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


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
            Q(name__icontains=search_query),
            Q(phone__icontains=search_query),
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
    if request.active_branch_id is None:
        messages.warning(request, 'Please select a specific branch before making a sale.')
        return redirect('dashboard')

    medicines = Medicine.objects.filter(is_active=True)
    customers = Customer.objects.all().order_by('name')
    categories = Category.objects.filter(is_active=True)
    active_branch = Branch.objects.get(id=request.active_branch_id)
    return render(request, 'pos/pos_sale.html', {
        'medicines': medicines,
        'customers': customers,
        'categories': categories,
        'active_branch': active_branch,
    })


@csrf_exempt
@login_required
def process_sale(request):
    if request.method == 'POST':
        if request.active_branch_id is None:
            return JsonResponse({'success': False, 'error': 'Select a branch before processing a sale.'}, status=400)
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                customer_id = data.get('customer_id')
                new_customer_data = data.get('new_customer', {})
                notes = data.get('notes', '')
                payments = data.get('payments', [])
                discount = float(data.get('discount_percent', 0))
                tax = float(data.get('tax_percent', 0))
                items = data.get('items', [])
            else:
                customer_id = request.POST.get('customer_id')
                customer_type = request.POST.get('customer_type')
                new_customer_data = {
                    'name': request.POST.get('new_customer_name', '').strip(),
                    'phone': request.POST.get('new_customer_phone', '').strip(),
                    'email': request.POST.get('new_customer_email', '').strip(),
                    'address': request.POST.get('new_customer_address', '').strip(),
                }
                notes = request.POST.get('notes', '')
                payments = []
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

            customer = None
            if customer_id:
                customer = Customer.objects.filter(id=customer_id).first()
            elif new_customer_data and new_customer_data.get('name'):
                customer = Customer.objects.create(
                    name=new_customer_data.get('name'),
                    phone=new_customer_data.get('phone', ''),
                    email=new_customer_data.get('email', ''),
                    address=new_customer_data.get('address', ''),
                )

            subtotal = 0
            for item in items:
                medicine_id = item.get('medicine_id')
                quantity = int(item.get('quantity', 0))
                if quantity > 0 and medicine_id:
                    medicine = Medicine.objects.get(id=medicine_id)
                    unit_price = float(item.get('unit_price', medicine.price if hasattr(medicine, 'price') else 0))
                    subtotal += quantity * unit_price
            discount_amount = subtotal * (discount / 100)
            taxable_amount = subtotal - discount_amount
            tax_amount = taxable_amount * (tax / 100)
            total_amount = taxable_amount + tax_amount

            if not payments:
                return JsonResponse({'success': False, 'error': 'At least one payment method is required.'}, status=400)

            payment_total = 0
            for payment in payments:
                payment_total += float(payment.get('amount', 0))
            if round(payment_total, 2) != round(total_amount, 2):
                return JsonResponse({'success': False, 'error': 'Payment total must exactly match amount due.'}, status=400)

            sale_method = 'split' if len(payments) > 1 else payments[0].get('payment_method', 'cash')
            sale = Sale.objects.create(
                branch_id=request.active_branch_id,
                customer=customer,
                payment_method=sale_method,
                notes=notes,
                discount=discount,
                tax=tax,
                served_by=request.user,
                total_amount=round(total_amount, 2)
            )

            for item in items:
                medicine_id = item.get('medicine_id')
                quantity = int(item.get('quantity', 0))
                unit_price = float(item.get('unit_price', 0)) if 'unit_price' in item else None
                if quantity > 0 and medicine_id:
                    medicine = Medicine.objects.get(id=medicine_id)
                    if unit_price is None:
                        unit_price = float(medicine.price)
                    total_price = quantity * unit_price
                    SaleItem.objects.create(
                        sale=sale,
                        medicine=medicine,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )

            for payment in payments:
                Payment.objects.create(
                    sale=sale,
                    payment_method=payment.get('payment_method', 'cash'),
                    amount=round(float(payment.get('amount', 0)), 2),
                    reference_number=payment.get('reference_number', '').strip()
                )
            return JsonResponse({'success': True, 'sale_id': sale.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


# Inventory Views
@login_required
def inventory_list(request):
    branch_filter = {} if request.active_branch_id is None else {'branch_id': request.active_branch_id}
    inventories = Inventory.objects.select_related('medicine', 'branch').filter(**branch_filter).order_by('medicine__name')
    return render(request, 'pos/inventory_list.html', {'inventories': inventories})


@login_required
def inventory_add(request):
    if request.method == 'POST':
        form = InventoryForm(request.POST, user=request.user)
        if form.is_valid():
            inv = form.save(commit=False)
            if not request.is_branch_admin:
                inv.branch_id = request.active_branch_id
            inv.save()
            messages.success(request, 'Inventory added successfully!')
            return redirect('inventory_list')
    else:
        form = InventoryForm(user=request.user)
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
    branch_filter = {} if request.active_branch_id is None else {'branch_id': request.active_branch_id}

    sales_qs = Sale.objects.filter(**branch_filter).order_by('-sale_date').prefetch_related('payments', 'items').select_related('customer', 'served_by', 'branch')

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    payment_method = request.GET.get('payment_method')
    if start_date:
        sales_qs = sales_qs.filter(sale_date__date__gte=start_date)
    if end_date:
        sales_qs = sales_qs.filter(sale_date__date__lte=end_date)
    if payment_method:
        sales_qs = sales_qs.filter(
            Q(payment_method=payment_method) |
            Q(payments__payment_method=payment_method)
        ).distinct()

    payment_summary = Payment.objects.filter(sale__in=sales_qs).values('payment_method').annotate(total=Sum('amount')).order_by('-total')

    sales_chart_data = list(
        sales_qs.annotate(day=TruncDate('sale_date')).values('day').annotate(total_sales=Sum('total_amount')).order_by('day')
    )
    sales_chart_data = [
        {
            'label': item['day'].strftime('%b %d') if item['day'] else 'Unknown',
            'value': float(item['total_sales'] or 0),
        }
        for item in sales_chart_data
    ]

    top_items = list(
        SaleItem.objects.filter(sale__in=sales_qs)
        .values('medicine__name')
        .annotate(units_sold=Sum('quantity'))
        .order_by('-units_sold')[:5]
    )
    top_items = [
        {
            'label': item['medicine__name'],
            'value': int(item['units_sold'] or 0),
        }
        for item in top_items
    ]

    paginator = Paginator(sales_qs, 10)
    page = request.GET.get('page')
    sales = paginator.get_page(page)
    return render(request, 'pos/sales_report.html', {
        'sales': sales,
        'payment_method': payment_method,
        'payment_summary': payment_summary,
        'sales_chart_data': sales_chart_data,
        'top_items': top_items,
    })


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
    branch_filter = {} if request.active_branch_id is None else {'branch_id': request.active_branch_id}

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category_id = request.GET.get('category')
    medicine_id = request.GET.get('medicine')
    expiry_status = request.GET.get('expiry_status')

    inventories = Inventory.objects.select_related('medicine', 'medicine__category', 'branch').filter(**branch_filter)

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

    stock_summary = inventories.values('medicine__name').annotate(
        total_stock=Sum('quantity')
    ).order_by('-total_stock')

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
    branch_filter = {} if request.active_branch_id is None else {'branch_id': request.active_branch_id}

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    customer_id = request.GET.get('customer')

    customers = Customer.objects.all()
    sales = Sale.objects.filter(**branch_filter).select_related('customer', 'served_by', 'branch').prefetch_related('payments', 'items')

    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)
    if customer_id:
        sales = sales.filter(customer_id=customer_id)

    customer_summary = sales.values(
        'customer__id',
        'customer__name',
        'customer__email',
        'customer__phone'
    ).annotate(
        total_sales=Sum('total_amount'),
        num_purchases=Count('id')
    ).order_by('-total_sales')

    selected_customer = None
    customer_history = []
    selected_customer_sales_total = 0
    if customer_id:
        selected_customer = Customer.objects.filter(id=customer_id).first()
        customer_history = sales.order_by('-sale_date')
        selected_customer_sales_total = customer_history.aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        'customer_summary': list(customer_summary),
        'customers': customers,
        'selected_customer': selected_customer,
        'customer_history': customer_history,
        'selected_customer_sales_total': selected_customer_sales_total,
        'start_date': start_date,
        'end_date': end_date,
        'selected_customer_id': customer_id,
    }
    return render(request, 'pos/customer_report.html', context)


@login_required
def supplier_report(request):
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
    branch_filter = {} if request.active_branch_id is None else {'branch_id': request.active_branch_id}

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    cashier_id = request.GET.get('cashier')
    payment_method = request.GET.get('payment_method')

    sales = Sale.objects.filter(**branch_filter).select_related('served_by', 'branch').prefetch_related('payments')

    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)
    if cashier_id:
        sales = sales.filter(served_by_id=cashier_id)
    if payment_method:
        sales = sales.filter(
            Q(payment_method=payment_method) |
            Q(payments__payment_method=payment_method)
        ).distinct()

    total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    total_tax = sales.aggregate(total=Sum('tax'))['total'] or 0
    total_discount = sales.aggregate(total=Sum('discount'))['total'] or 0
    num_sales = sales.count()

    cashier_summary = sales.values('served_by__username').annotate(
        total_sales=Sum('total_amount'),
        num_sales=Count('id')
    ).order_by('-total_sales')

    payment_summary = Payment.objects.filter(sale__in=sales).values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    daily_summary = sales.annotate(day=TruncDate('sale_date')).values('day').annotate(
        total_sales=Sum('total_amount'),
        num_sales=Count('id')
    ).order_by('day')

    monthly_summary = sales.annotate(month=TruncMonth('sale_date')).values('month').annotate(
        total_sales=Sum('total_amount'),
        num_sales=Count('id')
    ).order_by('month')

    branch_summary = []
    if request.active_branch_id is None:
        branch_summary = list(
            sales.values('branch__name').annotate(
                total_sales=Sum('total_amount'),
                num_sales=Count('id')
            ).order_by('-total_sales')
        )

    cashiers = User.objects.filter(id__in=sales.values_list('served_by_id', flat=True).distinct())

    context = {
        'total_revenue': total_revenue,
        'total_tax': total_tax,
        'total_discount': total_discount,
        'num_sales': num_sales,
        'cashier_summary': list(cashier_summary),
        'payment_summary': list(payment_summary),
        'daily_summary': list(daily_summary),
        'monthly_summary': list(monthly_summary),
        'branch_summary': branch_summary,
        'payment_methods': Payment.PAYMENT_METHOD_CHOICES,
        'cashiers': cashiers,
        'start_date': start_date,
        'end_date': end_date,
        'selected_cashier': cashier_id,
        'selected_payment_method': payment_method,
    }
    return render(request, 'pos/financial_report.html', context)
    