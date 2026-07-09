from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import *
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Row, Column


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.filter(is_active=True),
        required=False,
        help_text="Leave blank for System Admins with all-branch access."
    )
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, initial='cashier')

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        branch = cleaned_data.get('branch')
        if role != 'admin' and not branch:
            raise forms.ValidationError("A branch is required for non-admin roles.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
            profile = user.profile
            profile.branch = self.cleaned_data.get('branch')
            profile.role = self.cleaned_data.get('role')
            profile.save()
        return user


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_number', 'email', 'address', 'is_active']


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ['name', 'category', 'price', 'description', 'manufacturer', 'is_active']


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('phone', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('email', css_class='form-group col-md-6 mb-0'),
                Column('address', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
        )


class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ['branch', 'medicine', 'quantity', 'expiry_date', 'batch_number', 'cost_price']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'profile'):
            if user.profile.role != 'admin':
                self.fields.pop('branch')
            else:
                self.fields['branch'].queryset = Branch.objects.filter(is_active=True)


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer', 'payment_method', 'discount', 'tax']
        