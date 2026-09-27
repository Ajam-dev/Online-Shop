from django.db import models
from orders.models import Order

# Create your models here.

class Status(models.TextChoices):
    PENDING =("pending", "در انتظار پرداخت")
    SUCCESS =("success", "موفق")
    FAILED =("failed", "ناموفق")
    CANCELLED =("cancelled", "لغو شده")
    EXPIRED = ("expired", "منقضی شده")
    
class Gateway(models.TextChoices):
    ZARINPAL = ("zarinpal", "زرین پال")
    TEST = ("test","درگاه آزمایشی")

class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments", verbose_name="سفارش")
    amount = models.PositiveBigIntegerField(verbose_name="مبلغ")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="وضعیت پرداخت")
    gateway = models.CharField(max_length=30, choices=Gateway.choices, verbose_name="درگاه پرداخت")
    authority = models.CharField(max_length=100, blank=True, verbose_name="شناسه درگاه")
    reference_id = models.CharField(max_length=100, blank=True, verbose_name="شماره پیگیری")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    update_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ انقضای پرداخت")
    
    class Meta:
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت"
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"{self.order.order_number} - {self.amount}"
    