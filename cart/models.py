from django.db import models
from django.conf import settings
from products.models import Product, ProductVariant

# Create your models here.

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart", verbose_name="کاربر")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    update_at = models.DateTimeField(auto_now = True, verbose_name="آخرین بروز رسانی")
    
    class Meta:
        verbose_name = "سبد خرید"
        verbose_name_plural = "سبد خرید"
        
    def __str__(self):
        return f"سبد خرید {self.user}"
    
class CartItem(models.Model):
    cart = models.ForeignKey(Cart,on_delete=models.CASCADE, related_name="items", verbose_name="سبد خرید")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items", verbose_name="محصول")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items", verbose_name="تنوع محصول")
    quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")
    create_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    update_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروز رسانی")
    
    class Meta:
        verbose_name = "آیتم سبد خرید"
        verbose_name_plural = "آیتم سبد خرید"
        
    def __str__(self):
        return f"{self.product} x  {self.quantity}"
    
