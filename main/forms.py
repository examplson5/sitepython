from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import Review, UserProfile, Order
from .validators import validate_username_latin, validate_fio, validate_phone


class RegisterForm(UserCreationForm):
    username = forms.CharField(
        label='Логин',
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Латиница и цифры, от 6 символов',
            'data-validate': 'username',
        })
    )
    email = forms.EmailField(
        required=True,
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'data-validate': 'email'})
    )
    fio = forms.CharField(
        label='ФИО',
        max_length=150,
        validators=[validate_fio],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иванов Иван Иванович',
            'data-validate': 'fio',
        })
    )
    phone = forms.CharField(
        label='Телефон',
        max_length=20,
        validators=[validate_phone],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '8 (999) 123-45-67',
            'data-validate': 'phone',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'fio', 'phone', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        validate_username_latin(username)
        if User.objects.filter(username=username).exists():
            raise ValidationError('Пользователь с таким логином уже существует')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже существует')
        return email

    def clean_password2(self):
        password = self.cleaned_data.get('password2')
        if len(password) < 8:
            raise ValidationError('Пароль должен содержать минимум 8 символов')
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.fio = self.cleaned_data['fio']
            profile.phone = self.cleaned_data['phone']
            profile.save()
        return user


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'rating': forms.Select(attrs={'class': 'form-control'})
        }


class CheckoutForm(forms.Form):
    address = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        label='Адрес доставки'
    )
    phone = forms.CharField(
        max_length=20,
        validators=[validate_phone],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '8 (999) 123-45-67'
        })
    )
    delivery_method = forms.ChoiceField(
        choices=Order.DELIVERY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Способ доставки'
    )
    delivery_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Желаемая дата доставки'
    )
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_CHOICES,
        widget=forms.RadioSelect(),
        label='Способ оплаты'
    )