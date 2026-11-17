from django.shortcuts import get_object_or_404 ,render, redirect
from payments.models import Payment, Gateway, Status as PaymentStatus
from payments.services import verify_payment, create_payment
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from payments.forms import PaymentForm
from orders.models import Order, Status as OrderStatus
from django.utils import timezone
from orders.services import expire_order
from django.views.decorators.http import require_POST

# Create your views here.

@login_required
def payment_select_gateway(request, order_id):
    order = get_object_or_404(Order,id=order_id, user=request.user)
    
    if order.status != OrderStatus.PENDING_PAYMENT:
        messages.error(request, "این سفارش قابل پرداخت نیست")
        return redirect("orders:detail", order_id=order.id)

    if order.expires_at is not None and order.expires_at <= timezone.now():
        expire_order(order)
        messages.error(request, "مهلت پرداخت این سفارش به پایان رسیده است.")
        return redirect("orders:detail", order_id=order.id)
        
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            gateway_type = form.cleaned_data["gateway"]
            
            existing_payment = Payment.objects.filter(order=order, status=PaymentStatus.PENDING).order_by("-created_at").first()
            
            if existing_payment is not None and existing_payment.expires_at is not None and existing_payment.expires_at > timezone.now():
                if existing_payment.gateway == Gateway.TEST:
                    return redirect("payments:test_gateway", payment_id = existing_payment.id)
                messages.error(request, "برای این سفارش پرداخت فعالی وجود دارد. ادامه این درگاه هنوز در دسترس نیست.")
                return render(request, "payments/select_gateway.html", {"form":form, "order":order})
            
            try:
                payment = create_payment(order=order, gateway_type=gateway_type)
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, "payments/select_gateway.html",{"form":form, "order":order})
            if payment.gateway == Gateway.TEST:
                return redirect("payments:test_gateway", payment_id = payment.id)
            elif payment.gateway == Gateway.FAKE:
                messages.error (request, "درگاه فیک فعلا به این صفحه اضافه نشده است")
            else:
                messages.error(request, "این درگاه هنوز فعال نشده است")
    else:
        form = PaymentForm()
    return render(request, "payments/select_gateway.html",{"form":form,"order":order})

@login_required
def test_gateway(request, payment_id):
    payment = get_object_or_404(Payment.objects.select_related("order"),id=payment_id,order__user=request.user)
    return render(request,"payments/test_gateway.html",{"payment":payment})

@login_required
@require_POST
def test_payment_result(request, payment_id, result):
    
    payment = get_object_or_404(Payment.objects.select_related("order"),id=payment_id, order__user=request.user)

    try:
        payment =verify_payment(payment, result = result)
    
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect("payments:test_gateway", payment_id=payment.id)

    if payment.status == PaymentStatus.SUCCESS:
        return render(request, "payments/payment_success.html",{"payment":payment})
    elif payment.status == PaymentStatus.FAILED:
        return render(request, "payments/payment_failed.html", {"payment":payment})
    elif payment.status == PaymentStatus.EXPIRED:
        messages.error(request, "مهلت پرداخت این سفارش به پایان رسیده است.")
        return redirect("core:home")
    elif payment.status == PaymentStatus.CANCELLED:
        messages.error(request, "پرداخت لغو شده است")
        return redirect("core:home")
    else:
        messages.error(request, "وضعیت پرداخت مشخص نیست")
        return redirect("payments:test_gateway", payment_id = payment.id)
