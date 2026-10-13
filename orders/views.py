from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from orders.models import Address, Order, OrderItem, Status as OrderStatus
from orders.forms import CheckoutForm
from cart.models import Cart
from django.contrib import messages
from orders.services import checkout, cancel_order, reorder
from payments.models import Gateway
from django.core.exceptions import ValidationError
import uuid
from django.http import HttpResponseNotAllowed
from django.views.decorators.http import require_POST
from django.utils import timezone

# Create your views here.

@login_required
def checkout_view(request):
    
    if request.method not in ("GET","POST"):
        return HttpResponseNotAllowed
    
    cart , created = Cart.objects.get_or_create(user = request.user)
    cart_items = cart.items.select_related("product", "variant").all()
    checkout_key = request.session.get("checkout_key")
    checkout_order_id = request.session.get("checkout_order_id")
    order = None
    
    if checkout_order_id:
        order= Order.objects.filter(id=checkout_order_id, user=request.user,).first()
    
        print("ORDER FOUND:", order)
    
        if (
            order is None
            or order.status != OrderStatus.PENDING_PAYMENT
            or str(order.checkout_key) != str(checkout_key)
        ):
            request.session.pop("checkout_order_id",None)
            request.session.pop("checkout_key", None)
            
            checkout_order_id = None
            checkout_key = None
            order = None
            
            print("GET/REQUEST METHOD:", request.method)
            print("SESSION CHECKOUT KEY:", checkout_key)
            print("SESSION ORDER ID BEFORE LOOKUP:", checkout_order_id)
    
    if not cart_items.exists() and order is None:
        return render(request, "orders/checkout.html",{"cart_empty": True})
    
    if request.method == "GET":
        
        if not checkout_key:
            checkout_key = str(uuid.uuid4())
            request.session["checkout_key"] = checkout_key
            request.session.modified = True
            
        form = CheckoutForm(user=request.user)
        addresses = Address.objects.filter(user=request.user)
        
        order_items = (order.items.select_related("product","variant").all() if order is not None else None)
        
        return render(request, "orders/checkout.html",{"form": form, "addresses":addresses,"cart_items":cart_items, "order":order,"order_items":order_items, "has_pending_order":order is not None,})
    
    elif request.method == "POST":       
        form = CheckoutForm(request.POST, user=request.user)
        addresses = Address.objects.filter(user = request.user)
        
        print("POST DATA:", request.POST)
        print("FORM VALID:", form.is_valid())
        print("FORM ERRORS:", form.errors)
        
        if form.is_valid():
            
            print("ORDER INVALIDATION CHECK:")
            print("ORDER IS NONE:", order is None)
            
            if order is not None:
                print("ORDER STATUS:", order.status)
                print("ORDER CHECKOUT KEY:", order.checkout_key)
                print("SESSION CHECKOUT KEY:",  checkout_key)
            
            address = form.cleaned_data["address"]
            checkout_key = request.session.get("checkout_key")
            
            if not checkout_key:
                messages.error(request, "Checkout معبتر نیست. لطفا دوباره وارد صفحه پرداخت شوید")
                return redirect("orders:checkout")
            try:
                order = checkout(user=request.user, address=address, checkout_key = checkout_key)
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request,"orders/checkout.html", {"form":form, "addresses":addresses, "cart_items":cart_items, "has_pending_order":False,})

            
            request.session["checkout_order_id"]=order.id
            request.session["checkout_key"] = str(order.checkout_key)
            request.session.modified = True
            print("CREATED/REUSED ORDER:", order.id, order.order_number, order.status)
            print("SESSION ORDER ID:", request.session.get("checkout_order_id"))
            
            return redirect("orders:checkout")
        
        return render(request, "orders/checkout.html",{"form":form, "addresses":addresses, "cart_items":cart_items, "has_pending_order":False})

@login_required
@require_POST
def cancel_order_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    try:
        order=cancel_order(order)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect("orders:checkout")
    
    if order.status == OrderStatus.CANCELLED:
        messages.success(request,"سفارش شما با موفقیت لغو شد.")
        
    elif order.status == OrderStatus.EXPIRED:
        messages.warning(request, "مهلت این سفارش به پایان رسیده و سفارش منقضی شده است")
        
    return redirect("orders:order_history")



@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request,"orders/order_history.html", {"orders":orders})

@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    order_items = order.items.all().select_related("product","variant")
    
    payments = order.payments.all().order_by("-created_at")
    
    can_pay = (
        order.status == OrderStatus.PENDING_PAYMENT
        and (
            order.expires_at is None
            or order.expires_at > timezone.now()
        )
    )
    
    return render(request, "orders/order_detail.html",{"order":order, "order_items":order_items, "payments":payments, "can_pay":can_pay})

@login_required
@require_POST
def reorder_view(request, order_id):
    previous_order = get_object_or_404(Order, id = order_id, user=request.user)
    try:
        result = reorder(user=request.user, previous_order=previous_order)
    except ValidationError as error:
        messages.error(request, error.message)
        
    else:
        added_cont = result["added_count"]
        skipped_items = result["skipped_items"]
        
        if added_cont > 0:
            messages.success(request, f"عملیات سفارش مجدد برای {added_cont} ردیف محصول انجام شد")
        
        if skipped_items:
            skipped_message = "موارد زیر به سبد خرید اضافه نشدند:\n" + "\n".join(skipped_items)
            messages.warning(request, skipped_message)
            
        if added_cont == 0 and not skipped_items:
            messages.warning(request, "این سفارش  محصولی برای سفارش مجدد ندارد")
        
    return redirect("cart:cart_detail")