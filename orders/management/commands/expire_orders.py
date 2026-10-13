from django.core.management.base import BaseCommand
from django.utils import timezone
from orders.models import Order, Status
from orders.services import expire_order

class Command(BaseCommand):
    help = "منقضی کردن سفارش هایی که زمان پرداخت آنها به پایان رسیده است."
    
    def handle(self, *args, **options):
        now =  timezone.now()
        orders = Order.objects.filter(
            status = Status.PENDING_PAYMENT,
            expires_at__isnull = False,
            expires_at__lte = now,
        ).order_by("id")
        
        expired_count = 0
        
        for order in orders:
            expired_order = expire_order(order)
            if expired_order.status == Status.EXPIRED:
                expired_count += 1
                
        self.stdout.write(
            self.style.SUCCESS(f"{expired_count} سفارش منقضی شد.")
        )