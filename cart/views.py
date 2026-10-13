from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from cart.models import Cart, CartItem
from products.models import Product

# Create your views here.

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product,id=product_id, is_active = True, is_available = True)
    
    cart, created = Cart.objects.get_or_create(user = request.user)
    cart_item, created = CartItem.objects.get_or_create(
        cart = cart,
        product = product,
        variant = None,
    )
    
    if created:
        new_quantity = 1
    else:
        new_quantity = cart_item.quantity + 1
        
    if product.can_order(new_quantity):
        cart_item.quantity = new_quantity
        cart_item.save()
    
    return redirect("products:product_detail", slug = product.slug,)

@login_required
def cart_detail(request):
    cart , created = Cart.objects.get_or_create(user = request.user)
    
    items = cart.items.select_related("product","variant",).prefetch_related("product__images").all()
    total_price = sum(item.total_price for item in items)
    return render(request,"cart/cart_detail.html",{"cart":cart,"items":items, "total_price":total_price})

@login_required
def increase_quantity(request, item_id):
    cart_item = get_object_or_404(CartItem, id = item_id, cart__user = request.user)
    new_quantity = cart_item.quantity + 1
    if cart_item.product.can_order(new_quantity):
        cart_item.quantity = new_quantity
        cart_item.save()
        
    return redirect("cart:cart_detail")

@login_required
def decrease_quantity(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user = request.user)
    if cart_item.quantity > cart_item.product.min_order_quantity:
        cart_item.quantity -= 1
        cart_item.save()
        
    return redirect("cart:cart_detail")

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id = item_id, cart__user = request.user,)
    cart_item.delete()
    return redirect("cart:cart_detail")
