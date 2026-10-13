from django.core.exceptions import ValidationError
from payments.models import Payment, Status as PaymentStatus
from orders.models import Order, Status as OrderStatus
from django.db import transaction
from orders.services import finalize_order, reserve_order_stock, release_order_stock, refresh_order_prices, expire_order
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from payments.gateways.factory import get_gateway

def create_payment(order, gateway_type):
    order_expired = False
    payment = None
    
    with transaction.atomic():
        order = (Order.objects.select_for_update().get(pk=order.pk))
        
        if order.status != OrderStatus.PENDING_PAYMENT:
            raise ValidationError(
                "این سفارش در وضعیت قابل پرداخت نیست"
            )
            
        now = timezone.now()
        
        if order.expires_at is not None and order.expires_at <= now:
            expire_order(order)
            order_expired = True
        
        else:
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
                gateway = gateway_type,
                expires_at = now + timedelta(minutes = settings.PAYMENT_TIMEOUT_MINUTES),
            )
            
            gateway = get_gateway(payment.gateway)
            gateway_result = gateway.create_payment(payment)
            
            
            if not gateway_result["success"]:
                raise ValidationError("پرداخت در درگاه با خطا مواجه شد")

            payment.authority = gateway_result["authority"]
            payment.save(update_fields=["authority","update_at"])
        
    if order_expired:
        raise ValidationError("مهلت پرداخت این سفارش به پایان رسیده است")
            
    return payment

def verify_payment(payment, result = None):
    
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
            
        if order.expires_at is not None and order.expires_at <= now:
            expire_order(order)
            payment.refresh_from_db()
            return payment
            
        if payment.expires_at and payment.expires_at <= now:
            payment.status = PaymentStatus.EXPIRED
            payment.save(update_fields=["status","update_at"])
            release_order_stock(order)
            return payment
                  
        gateway = get_gateway(payment.gateway)
        gateway_result = gateway.verify_payment(payment, result = result)
        print("GATEWAY RESULT:", gateway_result)
        
        if not gateway_result["success"]:
            payment.status = PaymentStatus.FAILED
            payment.save(update_fields=["status","update_at"])
            release_order_stock(order)
            return payment
        
        if gateway_result["amount"] != payment.amount:
            payment.status = PaymentStatus.FAILED
            payment.save(update_fields=["status","update_at"])
            release_order_stock(order)
            return payment
        
        payment.status = PaymentStatus.SUCCESS
        payment.reference_id = gateway_result["reference_id"]
        payment.save(update_fields=["status","reference_id","update_at"])
              
        order.status = OrderStatus.PAID
        order.paid_at = now
        order.save(update_fields=["status","paid_at","update_at"])
        
        finalize_order(order)
        
    return payment
