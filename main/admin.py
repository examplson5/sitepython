from django.contrib import admin
from django.utils.html import format_html
from .models import Product, Category, Order, OrderItem, Review, Coupon, Wishlist


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'category', 'price', 'stock', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'description')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'text')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status_badge', 'delivery_method',
                    'delivery_date', 'payment_method', 'total', 'created_at')
    list_filter = ('status', 'delivery_method', 'payment_method', 'created_at')
    search_fields = ('user__username', 'phone', 'address')
    readonly_fields = ('user', 'created_at', 'total')
    inlines = [OrderItemInline]
    list_per_page = 20

    fieldsets = (
        ('Основное', {'fields': ('user', 'status', 'created_at', 'total')}),
        ('Доставка', {'fields': ('address', 'phone', 'delivery_method', 'delivery_date')}),
        ('Оплата', {'fields': ('payment_method', 'coupon', 'discount')}),
    )

    def status_badge(self, obj):
        color = obj.get_status_color()
        return format_html(
            '<span style="background:{};color:white;padding:4px 12px;'
            'border-radius:4px;font-weight:bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Статус'

    actions = ['mark_processing', 'mark_shipped', 'mark_delivered', 'mark_cancelled']

    @admin.action(description='Перевести в "В обработке"')
    def mark_processing(self, request, queryset):
        queryset.update(status='processing')

    @admin.action(description='Перевести в "Отправлен"')
    def mark_shipped(self, request, queryset):
        queryset.update(status='shipped')

    @admin.action(description='Перевести в "Доставлен"')
    def mark_delivered(self, request, queryset):
        queryset.update(status='delivered')

    @admin.action(description='Перевести в "Отменён"')
    def mark_cancelled(self, request, queryset):
        queryset.update(status='cancelled')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'value', 'active', 'valid_until')
    list_filter = ('active', 'discount_type')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'added_at')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')