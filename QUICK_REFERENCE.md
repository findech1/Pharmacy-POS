# Pharmacy POS - Quick Reference Card

## 🎯 CORE FEATURES AT A GLANCE

### 1️⃣ Point of Sale (POS)
- **URL:** `/pos/`
- **Key Features:**
  - Real-time product search & category filter
  - Multi-method payments (Cash, Card, MPESA, Split)
  - Walk-in customer support
  - Discount & tax fields
  - Receipt printing
- **⚠️ Issue:** Cart not editable (no remove/quantity edit)

### 2️⃣ Dashboard
- **URL:** `/`
- **Key Features:**
  - 4 KPI cards (medicines, customers, suppliers, today's sales)
  - Low stock alerts (<10 units)
  - Recent sales (last 5)
  - Expired inventory warning
  - Close-to-expiry alerts (30 days)

### 3️⃣ Inventory Management
- **URLs:** `/inventory/`, `/inventory/add/`
- **Key Features:**
  - Batch-level tracking (FIFO by expiry date)
  - Cost price tracking
  - Batch number tracking
  - Auto-decrement on sales

### 4️⃣ Reporting (5 Types)
| Report | URL | Key Metrics | Filters |
|--------|-----|-------------|---------|
| Sales | `/reports/sales/` | Total sales, payment mode | Date, payment method |
| Inventory | `/reports/inventory/` | Stock levels, value | Expiry status, medicine |
| Customer | `/reports/customers/` | Top customers, spend | Date range, customer |
| Supplier | `/reports/suppliers/` | Orders, spending | Date range, supplier |
| Financial⚙️ | `/reports/financial/` | Revenue, tax, discount | Date, cashier, payment |

**⚠️ Issue:** Charts are placeholders, CSV export not working

### 5️⃣ Customer Management
- **URL:** `/customers/`, `/customers/add/`
- **Features:** Search, add new, history tracking

### 6️⃣ Medicines
- **URL:** `/medicines/`, `/medicines/add/`, `/medicines/edit/<id>/`
- **Features:** List, add, edit, stock display

---

## 🗂️ DATA MODELS (8 Total)

```
Category → (1-to-M) → Medicine
                         ├─→ (1-to-M) → Inventory
                         └─→ (1-to-M) → SaleItem
                                            ↑
                                            │
Sale ←─ (1-to-M) ← SaleItem
 ├─→ (1-to-M) → Payment
 └─→ Customer (nullable for walk-ins)
 └─→ User (cashier/served_by)

Supplier → (1-to-M) → Order
```

---

## 🔗 URL QUICK MAP

```
/                    = Dashboard
/pos/                = Point of Sale
/pos/process/        = Transaction handler (AJAX)
/receipt/<id>/       = Receipt view & print

/medicines/          = Medicine list
/medicines/add/      = Add medicine
/medicines/edit/<id> = Edit medicine

/customers/          = Customer list
/customers/add/      = Add customer

/inventory/          = Inventory list
/inventory/add/      = Add inventory batch

/categories/, /categories/add/
/suppliers/, /suppliers/add/

/reports/sales/      = Sales report
/reports/inventory/  = Inventory report
/reports/customers/  = Customer report
/reports/suppliers/  = Supplier report
/reports/financial/  = Financial report (permission-gated)

/add-user/           = Create new user
/login/, /logout/    = Auth
```

---

## 📱 TEMPLATE MAPPING

| Template | Purpose | URL | Complexity |
|----------|---------|-----|-----------|
| `base.html` | Main layout (sidebar nav) | All | High |
| `dashboard.html` | KPI dashboard | / | High |
| `pos_sale.html` | POS checkout interface | /pos/ | High |
| `receipt.html` | Receipt display & print | /receipt/<id>/ | Medium |
| `*_list.html` (5) | List pages | /medicines/, /customers/, etc. | Low |
| `*_form.html` (5) | Form pages | /add/, /edit/ | Low |
| `*_report.html` (5) | Report pages | /reports/* | High |

---

## 🎯 KEY WORKFLOWS

### Sell Items (Primary Flow)
```
Login → Dashboard → POS
  ↓
Search/Filter Products
  ↓
Add to Cart
  ↓
Select Customer (existing/new/walk-in)
  ↓
Add Discount & Tax
  ↓
Select Payment Method(s)
  ↓
Process Sale (validate payment = total)
  ↓
Create Sale + SaleItems (auto-decrement inventory) + Payments
  ↓
Show Receipt (print option)
```

### Add Inventory
```
Dashboard → Inventory → Add
  ↓
Select Medicine → Enter Qty → Enter Expiry → Batch# → Cost
  ↓
Save
```

### View Reports
```
Dashboard → Reports → Choose Type
  ↓
Apply Filters (date, customer, payment method, etc.)
  ↓
View Table Data + Aggregations
  ↓
Export (CSV - not working) or Print
```

---

## 🎨 UI COLORS & BADGES

| Element | Color | Usage |
|---------|-------|-------|
| Sidebar | Blue #3b82f6 | Main navigation |
| Buttons | Blue (primary), Green (action) | CTAs |
| Success | Green #10b981 | OK status, good stock |
| Warning | Yellow #eab308 | Close to expiry (30d) |
| Danger | Red #ef4444 | Expired, low stock, critical |
| Badge | Inline pills | Status indicators |

---

## 🔧 VIEW SUMMARY

| View Name | Route | Method | Purpose |
|-----------|-------|--------|---------|
| **login_view** | /login/ | GET, POST | User authentication |
| **dashboard** | / | GET | Homepage, KPIs, alerts |
| **medicine_list** | /medicines/ | GET | List medicines (paginated) |
| **medicine_add** | /medicines/add/ | GET, POST | Create medicine |
| **medicine_edit** | /medicines/edit/<id>/ | GET, POST | Update medicine |
| **customer_list** | /customers/ | GET | List customers (searchable) |
| **customer_add** | /customers/add/ | GET, POST | Create customer |
| **pos_sale** | /pos/ | GET | POS interface (products + cart) |
| **process_sale** | /pos/process/ | POST | Transaction handler (AJAX) |
| **receipt** | /receipt/<id>/ | GET | Receipt display |
| **inventory_list** | /inventory/ | GET | Stock batches |
| **inventory_add** | /inventory/add/ | GET, POST | Add inventory batch |
| **category_list** | /categories/ | GET | Categories |
| **category_add** | /categories/add/ | GET, POST | Add category |
| **supplier_list** | /suppliers/ | GET | Suppliers |
| **supplier_add** | /suppliers/add/ | GET, POST | Add supplier |
| **sales_report** | /reports/sales/ | GET | Sales analytics |
| **inventory_report** | /reports/inventory/ | GET | Stock analytics |
| **customer_report** | /reports/customers/ | GET | Customer analytics |
| **supplier_report** | /reports/suppliers/ | GET | Supplier analytics |
| **financial_report** | /reports/financial/ | GET | Financial analytics ⚙️ |
| **add_user** | /add-user/ | GET, POST | User creation |

---

## ⚡ PERFORMANCE NOTES

| Optimization | Location | Details |
|--------------|----------|---------|
| **Pagination** | medicine_list, sales | 10 items/page |
| **select_related** | dashboard, reports | Joins foreign keys |
| **prefetch_related** | dashboard, sales_report | Batch fetch related |
| **Filtering** | medicine_list, reports | Q objects for OR |
| **Aggregation** | reports | Sum, Count, TruncDate, TruncMonth |
| **Caching** | - | ❌ Not implemented |
| **Async** | - | ❌ Not implemented |

---

## 🐛 TOP 5 UX ISSUES

1. **POS cart not reactive** - Can't edit/remove without reload
2. **Charts incomplete** - Report placeholders only
3. **Mobile unusable** - Not optimized for touch
4. **CSV export broken** - Buttons exist, no handler
5. **No inventory adjustment** - Manual corrections unavailable

---

## ✅ DEPLOYMENT CHECKLIST

- [ ] DEBUG = False in settings.py
- [ ] ALLOWED_HOSTS configured
- [ ] Database migrated (`python manage.py migrate`)
- [ ] Static files collected (`python manage.py collectstatic`)
- [ ] Secret key changed
- [ ] Email backend configured (if needed)
- [ ] Backup restored (db.sqlite3)
- [ ] Permissions set for financial_report

---

## 🔐 PERMISSION NOTES

- Financial report requires: `pos.view_financial_report` permission
- Most views require: `@login_required` decorator
- No custom permission groups visible in codebase

---

## 📚 FORMS (7 Total)

| Form | Model | Fields | Notes |
|------|-------|--------|-------|
| CustomUserCreationForm | User | 5 | Extends Django |
| CategoryForm | Category | 3 | name, description, is_active |
| SupplierForm | Supplier | 5 | Full contact info |
| MedicineForm | Medicine | 6 | name, category, price, description, manufacturer, is_active |
| CustomerForm | Customer | 4 | Crispy 2-column layout |
| InventoryForm | Inventory | 5 | Includes date widget |
| SaleForm | Sale | 4 | Unused in current views |

---

## 🎓 CODE PATTERNS

### Form Display Pattern
```django
{% for message in messages %}
  <div class="bg-{{ message.tags }}-100">{{ message }}</div>
{% endfor %}

<form method="post">
  {% csrf_token %}
  {{ form|crispy }}
  <button>Submit</button>
</form>
```

### Pagination Pattern
```django
{% if pages.has_other_pages %}
  <a href="?page={{ pages.previous_page_number }}">← Prev</a>
  Page {{ pages.number }} of {{ pages.paginator.num_pages }}
  <a href="?page={{ pages.next_page_number }}">Next →</a>
{% endif %}
```

### Status Badge Pattern
```django
{% if item.quantity < 10 %}
  <span class="bg-red-100 text-red-800">Low Stock</span>
{% else %}
  <span class="bg-green-100 text-green-800">{{ item.quantity }}</span>
{% endif %}
```

### Active Menu Pattern
```django
<a href="{% url 'view_name' %}" 
   class="{% if request.resolver_match.url_name == 'view_name' %}sidebar-active{% endif %}">
```

---

## 💾 BACKUP LOCATIONS

| File | Path | Type |
|------|------|------|
| Database | `/backups/db.sqlite3.20260707_234012` | SQLite |
| Payments | `/backups/payments_2025_export_20260707_234118.csv` | CSV |
| Items | `/backups/saleitems_2025_export_20260707_234118.csv` | CSV |
| Sales | `/backups/sales_2025_export_20260707_234118.csv` | CSV |

---

## 🚀 NEXT STEPS FOR DEVELOPMENT

**High Priority:**
1. Fix POS cart reactivity (add JS for remove/edit)
2. Implement Chart.js visualizations
3. Complete CSV export functionality
4. Mobile optimization for pos_sale.html

**Medium Priority:**
5. Add better error messages
6. Create inventory adjustment form
7. Add breadcrumbs navigation
8. Paginate dashboard cards

**Lower Priority:**
9. Barcode scanning integration
10. Refund/return flow
11. System settings page
12. Audit logging

---

## 📖 HOW TO FIND THINGS

**Need to understand a feature?**
1. Check URL in `pos/urls.py`
2. Find view name in `pos/views.py`
3. Check template in `templates/pos/<view_name>.html`
4. See form in `pos/forms.py` (if applicable)
5. Check model in `pos/models.py`

**Need to add a feature?**
1. Add model in `pos/models.py` (if new data type)
2. Add view in `pos/views.py`
3. Add form in `pos/forms.py` (if form needed)
4. Add URL in `pos/urls.py`
5. Add template in `templates/pos/`
6. Add link in `templates/base.html` navigation

**Need to test something?**
1. Open `python manage.py shell`
2. Import models: `from pos.models import *`
3. Query: `Medicine.objects.all()[:5]`
4. Test views in browser after changes

---

## 📞 SUPPORT

- **Framework Docs:** https://docs.djangoproject.com/
- **Tailwind Docs:** https://tailwindcss.com/docs
- **Chart.js Docs:** https://www.chartjs.org/docs/latest/
- **Font Awesome:** https://fontawesome.com/icons

---

**Generated:** July 8, 2026  
**Django Version:** 5.2  
**Status:** ✅ Functional | ⚠️ UX Improvements Needed
