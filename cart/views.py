from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from cart.models import Cart, CartItem
from products.models import Product, ProductVariant
from django.views.decorators.http import require_POST
from django.contrib import messages

# Create your views here.

@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product,id=product_id, is_active = True, is_available = True)
    variant_id = request.POST.get("variant_id")
    variant = None
    
    if product.has_variant:
        if not variant_id:
            messages.error(request, "لطفا تنوع محصول را انتخاب کنید")
            return redirect("products:product_detail", slug = product.slug)

        variant = ProductVariant.objects.filter(id=variant_id, product = product, is_active = True).first()
                
        if variant is None:
            messages.error(request, "تنوع انتخاب شده معتبر نیست.")
            return redirect("products:product_detail", slug = product.slug)
    
    elif variant_id:
        messages.error(request, "این محصول نیازی به انتخاب تنوع ندارد.")
        return redirect("products:product_detail", slug = product.slug)
        
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(
        cart = cart,
        product = product,
        variant = variant,
        defaults={"quantity": 0},
    )
    
    if created:
        new_quantity = product.min_order_quantity
    else:
        new_quantity = cart_item.quantity + 1
        
    if variant is not None:
        can_order = variant.can_order(new_quantity)
    else:
        can_order = product.can_order(new_quantity)
    
    if can_order:
        cart_item.quantity = new_quantity
        cart_item.save(update_fields=["quantity","update_at"])
        messages.success(request, "محصول به سبد خرید اضافه شد")
        
    else:
        if created:
            cart_item.delete()
        messages.error(request, "تعداد درخواستی با موجودی یا محدودیت سفارش سازگار نیست.")
    
    return redirect("products:product_detail", slug=product.slug)

@login_required
def cart_detail(request):
    cart , _ = Cart.objects.get_or_create(user = request.user)
    
    items = cart.items.select_related("product","variant",).prefetch_related("product__images").all()
    total_price = sum(item.total_price for item in items)
    return render(request,"cart/cart_detail.html",{"cart":cart,"items":items, "total_price":total_price})

@login_required
@require_POST
def increase_quantity(request, item_id):
    cart_item = get_object_or_404(CartItem.objects.select_related("product","variant"), id = item_id, cart__user = request.user)
    new_quantity = cart_item.quantity + 1
    
    if cart_item.variant_id is not None:
        can_increase = cart_item.variant.can_order(new_quantity)
    else:
        can_increase = cart_item.product.can_order(new_quantity)

    if can_increase:
        cart_item.quantity = new_quantity
        cart_item.save()
        messages.success(request, "تعداد محصول افزایش یافت")
    
    else:
        messages.error(request, "امکان افزایش تعداد وجود ندارد موجودی و محدودیت سفارش را بررسی کن")        
    return redirect("cart:cart_detail")

@login_required
@require_POST
def decrease_quantity(request, item_id):
    cart_item = get_object_or_404(CartItem.objects.select_related("product","variant"), id=item_id, cart__user = request.user)
    min_quantity = cart_item.product.min_order_quantity
    
    if cart_item.quantity > min_quantity:
        cart_item.quantity -= 1
        cart_item.save(update_fields=["quantity","update_at"])
        messages.success(request,"تعداد محصول کاهش یافت.")
    
    else:
        messages.error(request, "تعداد محصول نمی تواند از حداقل تعداد سفارش کمتر باشد")
        
    return redirect("cart:cart_detail")

@login_required
@require_POST
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id = item_id, cart__user = request.user,)
    cart_item.delete()
    return redirect("cart:cart_detail")
