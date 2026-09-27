from django.core.exceptions import ValidationError
from payments.models import Payment, Status as PaymentStatus, Gateway
from orders.models import Order, Status as OrderStatus
from django.db import transaction
from orders.services import finalize_order, reserve_order_stock, release_order_stock, refresh_order_prices
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

def create_payment(order):
    
    with transaction.atomic():
        order = (Order.objects.select_for_update().get(pk=order.pk))
        
        if order.status != OrderStatus.PENDING_PAYMENT:
            raise ValidationError(
                "این سفارش در وضعیت قابل پرداخت نیست"
            )
            
        now = timezone.now()
            
        existing_payment = Payment.objects.select_for_update().filter(order=order, status = PaymentStatus.PENDING).order_by("-created_at").first()
        
        if existing_payment:
            if existing_payment.expires_at and existing_payment.expires_at > now:
                raise ValidationError(
                    "برای این سفارش یک پرداخت در حال انجام وجود دارد"
                )

            existing_payment.status = PaymentStatus.EXPIRED
            existing_payment.save(update_fields=["status","update_at"])
            release_order_stock(order)
        
        order = refresh_order_prices(order)
        
        if order.total_amount <= 0:
            raise ValidationError("مبلغ سفارش معتبر نیست.")
                        
        reserve_order_stock(order)
            
        payment = Payment.objects.create(
            order = order,
            amount = order.total_amount,
            status = PaymentStatus.PENDING,
            gateway = Gateway.TEST,
            expires_at = now + timedelta(minutes = settings.PAYMENT_TIMEOUT_MINUTES),
        )
        
    return payment

def verify_payment(payment, success):
    
    with transaction.atomic():
        now = timezone.now()
        payment = (Payment.objects.select_for_update().get(pk=payment.pk))
        
        if payment.status != PaymentStatus.PENDING:
            raise ValidationError(
                "این پرداخت قبلا تعیین تکلیف شده است."
            )
        
        order = (Order.objects.select_for_update().get(pk=payment.order_id))
            
        if order.status != OrderStatus.PENDING_PAYMENT:
            raise ValidationError(
                "این سفارش در وضعیت قابل پرداخت نیست"
            )
            
        if payment.expires_at and payment.expires_at <= now:
            payment.status = PaymentStatus.EXPIRED
            payment.save(update_fields=["status","update_at"])
            release_order_stock(order)
            return payment
     
        if not success:
            payment.status = PaymentStatus.FAILED
            payment.save(update_fields = ["status", "update_at"])
            release_order_stock(order)
            return payment
                  
        payment.status = PaymentStatus.SUCCESS
        payment.reference_id = f"TEST-{payment.id}"
        payment.save(update_fields=["status","reference_id","update_at"])
        
        order.status = OrderStatus.PAID
        order.save(update_fields=["status","update_at"])
        
        finalize_order(order)
        
    return payment
