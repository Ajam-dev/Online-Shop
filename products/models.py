from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=50,verbose_name='نام دسته بندی')
    slug = models.SlugField(unique=True, verbose_name='اسلاگ')
    parent = models.ForeignKey("self",on_delete=models.CASCADE, null=True, blank=True, related_name="children", verbose_name="دسته بندی والد")
    image = models.ImageField(upload_to="categories/", blank=True, null=True, verbose_name="تصویر")
    description = models.TextField(blank=True,verbose_name="توضیحات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    create_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    update_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "دسته بندی"
        verbose_name_plural = "دسته بندی"
        
    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=50,verbose_name="نام ")
    slug = models.SlugField(unique=True, verbose_name="اسلاگ")
    logo = models.ImageField(upload_to="brands/", null=True, blank=True, verbose_name="لوگو")
    description = models.TextField(verbose_name="توضیحات",blank=True)
    is_active = models.BooleanField(verbose_name="فعال", default=True)
    create_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    update_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "برند"
        verbose_name_plural = "برند"
        ordering = ["name"]
        
    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category,on_delete=models.SET_NULL,null=True, blank=True, related_name="products", verbose_name="دسته بندی")
    brand = models.ForeignKey(Brand, on_delete= models.SET_NULL, null=True, blank=True, related_name="products", verbose_name="برند")
    name = models.CharField(max_length=120, verbose_name="نام محصول")
    slug = models.SlugField(max_length=180, unique=True, verbose_name="اسلاگ")
    sku = models.CharField(max_length=50, unique=True, verbose_name="کد محصول")
    short_description = models.CharField(max_length=250, verbose_name="توضیحات کوتاه")
    description = models.TextField(verbose_name="توضیحات کامل")
    price = models.PositiveBigIntegerField(validators=[MinValueValidator(0)] ,verbose_name="قیمت")
    discount_percent = models.PositiveSmallIntegerField(validators=[MinValueValidator(0),MaxValueValidator(100)], verbose_name="درصد تخفیف")
    stock = models.PositiveIntegerField(default=0, verbose_name="موجودی")
    reserved_stock = models.PositiveIntegerField(default=0, verbose_name="موجودی رزرو شده")
    min_order_quantity = models.PositiveIntegerField(default=1, verbose_name="حداقل تعداد سفارش")
    max_order_quantity = models.PositiveIntegerField(null=True, blank=True, verbose_name="حداکثر تعداد سفارش")
    is_active = models.BooleanField(default=True, verbose_name="در دسترس")
    is_available = models.BooleanField(default=True, verbose_name="قابل فروش")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    has_variant = models.BooleanField(default=False, verbose_name="دارای تنوع")
    
    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصول"
        ordering = ["-created_at"]
        
    def __str__(self):
        return self.name
    
    @property
    def final_price(self):
        return self.price * (100 - self.discount_percent) // 100
    
    @property
    def available_stock(self):
        return max(self.stock - self.reserved_stock, 0)
    
    @property
    def is_in_stock(self):
        return self.available_stock > 0
    
    
    def can_order_quantity(self, quantity=1):
        if quantity < self.min_order_quantity:
            return False
        if (
            self.max_order_quantity is not None
            and self.max_order_quantity > 0
            and quantity > self.max_order_quantity
        ):
            return False
        return True

    def can_order(self, quantity = 1):
        if not self.is_active or not self.is_available:
            return False
        
        if not self.can_order_quantity(quantity):
            return False
        
        if quantity > self.available_stock:
            return False
        return True
    
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images", verbose_name="محصول")
    image = models.ImageField(upload_to="products/gallery/", verbose_name="تصویر")
    alt_text = models.CharField(max_length=150, blank=True, verbose_name="متن جایگزین")
    is_main = models.BooleanField(default=False, verbose_name="تصویر اصلی")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصویر محصول"
        ordering = ["-is_main", "-created_at"]
        
    def __str__(self):
        return f"{self.product.name} - تصویر"
    
class Attribute(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام ویژگی")
    slug = models.SlugField(max_length=120, unique=True, verbose_name="اسلاگ")
    is_variant = models.BooleanField(default=False, verbose_name="ویژگی تنوع")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    
    class Meta:
        verbose_name = "ویژگی"
        verbose_name_plural = "ویژگی"
        ordering = ["name"]
        
    def __str__(self):
        return self.name

class AttributeValue(models.Model):
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name="values", verbose_name="ویژگی")
    value = models.CharField(max_length=100, verbose_name="مقدار")
    
    class Meta:
        verbose_name = "مقدار ویژگی"
        verbose_name_plural = "مقدار ویژگی"
        ordering = ["value"]
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "value"],
                name = "unique_attribute_value"
            )
        ]
    
    def __str__(self):
        return f"{self.attribute.name}: {self.value}"
    
class ProductAttribute(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_attributes", verbose_name="محصول")
    attribute = models.ForeignKey(Attribute,on_delete=models.PROTECT, related_name="products", verbose_name="ویژگی" )
    position = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب نمایش")
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product","attribute"],
                name ="unique_product_attribute"
                ),
            ]
        ordering = ["position","id"]
        verbose_name = "ویژگی محصول "
        verbose_name_plural = "ویژگی محصول"
        
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.attribute_id and not self.attribute.is_variant:
            raise ValidationError({"attribute":("این ویژگی باید بعنوان ویژگی تنوع علامت گذاری شده باشد.")})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args,**kwargs)
        
    def __str__(self):
        return f"{self.product.name} - {self.attribute.name}"
    
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants", verbose_name="محصول")
    sku = models.CharField(max_length=50, unique=True, verbose_name="کد کالا")
    image = models.ImageField(upload_to="products/variants/",null=True, blank=True, verbose_name="تصویر تنوع")
    price = models.PositiveBigIntegerField(null=True, blank=True, verbose_name="قیمت")
    discount_percent = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)],verbose_name="درصد تخفیف")
    stock = models.PositiveIntegerField(default=0, verbose_name="موجودی")
    reserved_stock = models.PositiveIntegerField(default=0,verbose_name="موجودی رزرو شده")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    update_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروز رسانی")
    
    class Meta:
        verbose_name = "تنوع محصول"
        verbose_name_plural = "تنوع محصول"
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"{self.product.name} - {self.sku}"
    
    @property
    def effective_price(self):
        if self.price is None:
            return self.product.price
        return self.price
    
    @property
    def effective_discount_percent(self):
        if self.price is None:
            return self.product.discount_percent
        return self.discount_percent
    
    @property
    def final_price(self):
        return (self.effective_price * (100 - self.effective_discount_percent) // 100)
    
    @property
    def available_stock(self):
        return max(self.stock - self.reserved_stock, 0)
    
    @property
    def is_in_stock(self):
        return self.available_stock > 0
    
    def can_order(self, quantity=1):
        if not self.is_active:
            return False
        
        if not self.product.is_active or not self.product.is_available:
            return False
        
        if not self.product.can_order_quantity(quantity):
            return False
        
        if quantity > self.available_stock:
            return False
        
        return True
    
    def validate_variant_attributes(self):
        from django.core.exceptions import ValidationError
        
        if not self.pk:
            raise ValidationError("ابتدا باید تنوع محصول ذخیره شود.")
        
        required_attributes = set(self.product.product_attributes.values_list("attribute_id",flat=True))
        selectd_attributes = list(self.variant_attributes.select_related("attribute_value__attribute").values_list("attribute_value__attribute_id","attribute_value_id",))

        selected_attribute_ids = [attribute_id for attribute_id, value_id in selectd_attributes] 
        
        if len(selected_attribute_ids) != len(set(selected_attribute_ids)):
            raise ValidationError("برای هر ویژگی یک مقدار می توان انتخاب کرد.")
        
        selected_attribute_set = set(selected_attribute_ids)
        
        invalid_attribute = selected_attribute_set - required_attributes
        if invalid_attribute:
            raise ValidationError("این تنوع دارای ویژگی هایی است که برای محصول تعریف نشده اند.")
        
        missing_attributes = required_attributes - selected_attribute_set
        if missing_attributes:
            raise ValidationError("باید برای تمام ویژگی های تنوع محصول یک مقدار انتخاب شود.")

class VariantAttribute(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="variant_attributes", verbose_name="تنوع محصول ")
    attribute_value = models.ForeignKey(AttributeValue, on_delete=models.CASCADE, related_name="variant_attributes", verbose_name="مقدار ویژگی ها")
    
    class Meta:
        verbose_name = "ویژگی تنوع محصول"
        verbose_name_plural = "ویژگی تنوع محصول"
        
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "attribute_value"],
                name = "unique_vatiant_attribute"
            )
        ]
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.variant_id or not self.attribute_value_id:
            return
        
        variant = self.variant
        attribute_value = self.attribute_value
        select_attribute = attribute_value.attribute
        
        if not ProductAttribute.objects.filter(product_id = variant.product_id, attribute_id =select_attribute.id).exists():
            raise ValidationError({"attribute_value":"این ویژگی برای محصول مورد نظر تعریف نشده است."})
        
        duplicate_attribute = VariantAttribute.objects.filter(variant_id = variant.id, attribute_value__attribute_id = select_attribute.id).exclude(pk=self.pk)
        
        if duplicate_attribute.exists():
            raise ValidationError({"attribute_value": ("برای این ویژدگی قبلا مقداری در این تنوع ثبت شده است.")})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args,**kwargs)
        
    def __str__(self):
        return f"{self.variant} - {self.attribute_value}"

class ProductReview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="product_reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews", verbose_name="محصول")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)], verbose_name="امتیاز")
    comment = models.TextField(blank=True, verbose_name="متن نظر")
    is_approved = models.BooleanField(default=False, verbose_name="تایید شده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    update_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروز رسانی")
    
    class Meta:
        verbose_name = "نظر محصول"
        verbose_name_plural = " نظر محصول"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields = ["user", "product"],
                name = "unique_user_product_review"
            )
        ]
        
    def __str__(self):
        return f"{self.user} - {self.product} - {self.rating}"
    
class ProductFavorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_products", verbose_name="کاربر")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorited_by", verbose_name="محصول")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        verbose_name = "علاقه مندی"
        verbose_name_plural = "علاقه مندی"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user","product"],
                name = "unique_user_product_favorite"
            )
        ]
    
    def __str__(self):
        return f"{self.user} - {self.product}"
        

