from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db.models import Q, Avg
from decimal import Decimal

from .models import Product, Order, OrderItem, Category, Review, Coupon, Wishlist
from .forms import RegisterForm, ReviewForm, CheckoutForm
from .validators import validate_username_latin, validate_fio, validate_phone


def get_cart(request):
    return request.session.get('cart', {})


def index(request):
    categories = cache.get('categories_list')
    if not categories:
        categories = list(Category.objects.all())
        cache.set('categories_list', categories, 900)

    products = Product.objects.all()

    category_slug = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    search = request.GET.get('search')
    sort_by = request.GET.get('sort', 'name')

    if category_slug:
        products = products.filter(category__slug=category_slug)
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass
    if search:
        products = products.filter(Q(name__icontains=search) | Q(description__icontains=search))

    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:
        products = products.order_by('name')

    for product in products:
        product.avg_rating = product.average_rating()
        product.reviews_count = product.reviews.count()

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    return render(request, 'main/index.html', {
        'products': products,
        'categories': categories,
        'selected_category': category_slug,
        'min_price': min_price,
        'max_price': max_price,
        'search': search,
        'sort_by': sort_by,
        'wishlist_ids': wishlist_ids,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    reviews = product.reviews.all()
    avg_rating = product.average_rating()

    can_leave_review = False
    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
        can_leave_review = OrderItem.objects.filter(
            order__user=request.user,
            order__status='delivered',
            product=product
        ).exists() and not user_review

    if request.method == 'POST' and request.user.is_authenticated:
        if not can_leave_review:
            messages.error(request, 'Отзыв можно оставить только после завершения заказа')
            return redirect('product_detail', slug=slug)
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, 'Отзыв добавлен!')
            return redirect('product_detail', slug=slug)
    else:
        form = ReviewForm()

    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    return render(request, 'main/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'form': form,
        'user_review': user_review,
        'can_leave_review': can_leave_review,
        'in_wishlist': in_wishlist,
    })


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна!')
            return redirect('index')
    else:
        form = RegisterForm()
    return render(request, 'main/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, 'Вы вошли в систему')
            return redirect(request.GET.get('next', 'index'))
    else:
        form = AuthenticationForm()
    return render(request, 'main/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('index')


def validate_field(request):
    field = request.POST.get('field')
    value = request.POST.get('value', '')
    try:
        if field == 'username':
            validate_username_latin(value)
            if User.objects.filter(username=value).exists():
                raise ValidationError('Логин уже занят')
        elif field == 'fio':
            validate_fio(value)
        elif field == 'phone':
            validate_phone(value)
        elif field == 'email':
            from django.contrib.auth.models import User as U
            if U.objects.filter(email=value).exists():
                raise ValidationError('Email уже занят')
        return JsonResponse({'valid': True})
    except ValidationError as e:
        return JsonResponse({'valid': False, 'error': e.message})


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = get_cart(request)
    key = str(product_id)
    if key in cart:
        cart[key]['quantity'] += 1
    else:
        cart[key] = {'quantity': 1, 'price': str(product.price), 'name': product.name}
    request.session['cart'] = cart
    messages.success(request, f'{product.name} добавлен в корзину')
    return redirect(request.META.get('HTTP_REFERER', 'index'))


@login_required
def cart_view(request):
    cart = get_cart(request)
    items = []
    total = Decimal('0')
    for key, item in cart.items():
        product = Product.objects.filter(id=int(key)).first()
        if product:
            subtotal = product.price * item['quantity']
            items.append({'product': product, 'quantity': item['quantity'], 'subtotal': subtotal})
            total += subtotal

    discount = Decimal('0')
    coupon = None
    promo = request.session.get('promo_code')
    if promo:
        coupon = Coupon.objects.filter(code=promo, active=True).first()
        if coupon and coupon.is_valid():
            discount = coupon.calculate_discount(total)
        else:
            coupon = None
            request.session['promo_code'] = None

    final_total = total - discount

    return render(request, 'main/cart.html', {
        'items': items,
        'total': total,
        'discount': discount,
        'final_total': final_total,
        'coupon': coupon,
    })


@login_required
def remove_from_cart(request, product_id):
    cart = get_cart(request)
    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session['cart'] = cart
        messages.success(request, 'Товар удалён из корзины')
    return redirect('cart')


@login_required
def checkout(request):
    cart = get_cart(request)
    if not cart:
        messages.error(request, 'Корзина пуста')
        return redirect('cart')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = Order.objects.create(
                user=request.user,
                total=0,
                address=form.cleaned_data['address'],
                phone=form.cleaned_data['phone'],
                delivery_method=form.cleaned_data['delivery_method'],
                delivery_date=form.cleaned_data['delivery_date'],
                payment_method=form.cleaned_data['payment_method'],
                status='pending',
            )

            total = Decimal('0')
            for key, item in cart.items():
                product = Product.objects.get(id=int(key))
                if product.stock >= item['quantity']:
                    OrderItem.objects.create(
                        order=order, product=product,
                        quantity=item['quantity'], price=product.price
                    )
                    product.stock -= item['quantity']
                    product.save()
                    total += product.price * item['quantity']

            promo = request.session.get('promo_code')
            if promo:
                coupon = Coupon.objects.filter(code=promo, active=True).first()
                if coupon and coupon.is_valid():
                    discount = coupon.calculate_discount(total)
                    order.coupon = coupon
                    order.discount = discount
                    total -= discount

            order.total = total
            order.save()
            request.session['cart'] = {}
            request.session['promo_code'] = None
            messages.success(request, 'Заказ оформлен!')
            return redirect('success')
    else:
        form = CheckoutForm()

    return render(request, 'main/checkout.html', {'form': form})


@login_required
def success_view(request):
    return render(request, 'main/success.html')


@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'main/profile.html', {'orders': orders})


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'main/my_orders.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.items.all()
    return render(request, 'main/order_detail.html', {'order': order, 'items': items})


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'pending':
        order.status = 'cancelled'
        order.save()
        for item in order.items.all():
            product = item.product
            product.stock += item.quantity
            product.save()
        messages.success(request, f'Заказ #{order.id} отменён')
    else:
        messages.error(request, f'Нельзя отменить заказ в статусе "{order.get_status_display()}"')
    return redirect('my_orders')


@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'main/wishlist.html', {'items': items})


@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.delete()
        messages.info(request, 'Товар удалён из избранного')
    else:
        messages.success(request, 'Товар добавлен в избранное')
    return redirect(request.META.get('HTTP_REFERER', 'index'))


@login_required
def apply_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        coupon = Coupon.objects.filter(code=code, active=True).first()
        if coupon and coupon.is_valid():
            request.session['promo_code'] = code
            messages.success(request, f'Промокод {code} применён')
        else:
            messages.error(request, 'Промокод не найден или недействителен')
    return redirect('cart')