from django.db import models
from django.conf import settings
from products.models import Product, ProductVariant

# Create your models here.

class Status(models.TextChoices):
    PENDING_PAYMENT = ("pending_payment","درانتظار پرداخت")
    PAID = ("paid","پرداخت شده")
    COMPLETED = ("completed", "تکمیل شده")
    PROCESSING = ("processing","درحال پردازش")
    SHIPPED = ("shipped","ارسال شده")
    DELIVERED = ("delivered","تحویل داده شده")
    CANCELLED = ("cancelled","لغو شده")

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders", verbose_name="کاربر")
    order_number = models.CharField(max_length=30, unique=True, verbose_name="شماره سفارش")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT, verbose_name="وضعیت سفارش")
    recipient_name = models.CharField(max_length=100, verbose_name="نام گیرنده")
    phone_number = models.CharField(max_length=11, verbose_name="شماره تماس")
    province = models.CharField(max_length=100, verbose_name="استان")
    city = models.CharField(max_length=100, verbose_name="شهر")
    address = models.TextField(verbose_name="آدرس")
    postal_code = models.CharField(max_length=10, verbose_name="کد پستی")
    plaque = models.CharField(max_length=20, blank=True, verbose_name="پلاک")
    unit = models.CharField(max_length=20,blank=True , verbose_name="واحد")
    total_amount =models.PositiveBigIntegerField(default=0, verbose_name="مبلغ کل")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    update_at = models.DateTimeField(auto_now = True, verbose_name="تاریخ بروز رسانی")    
    
    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش"
        ordering = ["-created_at"]
        
    def __str__(self):
        return self.order_number
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="سفارش")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items", verbose_name="محصول")
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items", verbose_name="تنوع محصول")
    product_name = models.CharField(max_length=150, verbose_name="نام محصول")
    sku = models.CharField(max_length=50, blank=True, verbose_name="کد کالا")
    quantity = models.PositiveIntegerField(verbose_name="تعداد")
    unit_price = models.PositiveBigIntegerField(verbose_name="قیمت واحد")
    total_price = models.PositiveBigIntegerField(verbose_name="قیمت کل")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        verbose_name = "آیتم سفارش"
        verbose_name_plural = "آیتم سفارش"
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses", verbose_name="کاربر")
    title = models.CharField(max_length=50, verbose_name="عنوان آدرس")
    recipient_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=11, verbose_name="شماره تماس")
    province = models.CharField(max_length=100, verbose_name="استان")
    city = models.CharField(max_length=100, verbose_name="شهر")
    address = models.TextField(verbose_name="آدرس")
    postal_code = models.CharField(max_length=10, verbose_name="کد پستی")
    plaque = models.CharField(max_length=20, blank=True, verbose_name="پلاک")
    unit = models.CharField(max_length=20, blank=True, verbose_name="واحد")
    is_default = models.BooleanField(default=False, verbose_name="آدرس پیشفرض")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    update_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروز رسانی")
    
    class Meta:
        verbose_name = "آدرس"
        verbose_name_plural = "آدرس"
        ordering = ["-is_default","-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition= models.Q(is_default=True),
                name = "unique_default_address_per_user"
            )
        ]
        
    def __str__(self):
        return f"{self.title} - {self.recipient_name}"
    
