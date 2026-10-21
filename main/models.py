from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

from .validators import validate_fio, validate_phone


class Category(models.Model):
    name = models.CharField('Название', max_length=100)
    slug = models.SlugField('URL', unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class Product(models.Model):
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('URL', unique=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Категория'
    )
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    description = models.TextField('Описание')
    stock = models.IntegerField('Количество на складе', default=0)
    image = models.ImageField('Изображение', upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            original = self.slug
            counter = 1
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f'{original}-{counter}'
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', args=[self.slug])

    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(r.rating for r in reviews) / len(reviews)
        return 0

    def reviews_count(self):
        return self.reviews.count()

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    fio = models.CharField('ФИО', max_length=150, validators=[validate_fio], blank=True)
    phone = models.CharField('Телефон', max_length=20, validators=[validate_phone], blank=True)

    def __str__(self):
        return f'{self.user.username} - {self.fio}'

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, fio='', phone='')


class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 - Ужасно'),
        (2, '2 - Плохо'),
        (3, '3 - Нормально'),
        (4, '4 - Хорошо'),
        (5, '5 - Отлично'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='Товар')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    rating = models.IntegerField('Оценка', choices=RATING_CHOICES)
    text = models.TextField('Текст отзыва')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    def __str__(self):
        return f'{self.user.username} - {self.product.name} ({self.rating})'

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']


class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('percent', 'Процент'),
        ('fixed', 'Фиксированная сумма'),
    ]

    code = models.CharField('Код', max_length=50, unique=True)
    discount_type = models.CharField('Тип', max_length=10, choices=DISCOUNT_TYPES)
    value = models.DecimalField('Значение', max_digits=10, decimal_places=2)
    active = models.BooleanField('Активен', default=True)
    valid_until = models.DateTimeField('Действует до', null=True, blank=True)
    min_amount = models.DecimalField('Минимальная сумма', max_digits=10, decimal_places=2, default=0)

    def is_valid(self):
        from django.utils import timezone
        if not self.active:
            return False
        if self.valid_until and self.valid_until < timezone.now():
            return False
        return True

    def calculate_discount(self, amount):
        if amount < self.min_amount:
            return Decimal('0')
        if self.discount_type == 'percent':
            return amount * self.value / Decimal('100')
        return self.value

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает обработки'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменён'),
    ]

    DELIVERY_CHOICES = [
        ('courier', 'Курьером'),
        ('pickup', 'Самовывоз'),
        ('post', 'Почтой России'),
    ]

    PAYMENT_CHOICES = [
        ('on_receipt', 'При очном получении'),
        ('sbp', 'Переводом по СБП'),
    ]

    STATUS_COLORS = {
        'pending': '#f39c12',
        'processing': '#3498db',
        'shipped': '#9b59b6',
        'delivered': '#27ae60',
        'cancelled': '#e74c3c',
    }

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    total = models.DecimalField('Итого', max_digits=10, decimal_places=2)
    address = models.TextField('Адрес доставки')
    phone = models.CharField('Телефон', max_length=20)
    delivery_method = models.CharField('Способ доставки', max_length=20, choices=DELIVERY_CHOICES, default='courier')
    delivery_date = models.DateField('Желаемая дата доставки', null=True, blank=True)
    payment_method = models.CharField('Способ оплаты', max_length=20, choices=PAYMENT_CHOICES, default='on_receipt')
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Промокод')
    discount = models.DecimalField('Скидка', max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'Заказ #{self.id} - {self.user.username}'

    def get_status_color(self):
        return self.STATUS_COLORS.get(self.status, '#95a5a6')

    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def is_completed(self):
        return self.status == 'delivered'

    @property
    def status_order(self):
        statuses = ['pending', 'processing', 'shipped', 'delivered']
        if self.status in statuses:
            return statuses.index(self.status) + 1
        return 0

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заказ')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    quantity = models.IntegerField('Количество')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'

    def subtotal(self):
        return self.price * self.quantity

    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField('Дата добавления', auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.product.name}'

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        unique_together = ('user', 'product')
        ordering = ['-added_at']