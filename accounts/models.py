from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import RegexValidator

# Create your models here.

class GenderOption(models.TextChoices):
    male = ('m','مرد')
    female = ('f','زن')
    none = ('n','نمیخواهم مشخص کنم')
    

class MyUser(AbstractUser):
    phone_number = models.CharField(max_length=11,null=True,blank=True,verbose_name='شماره تلفن', validators=[RegexValidator(regex=r"^09\d{9}$", message="شماره موبایل باید با 09 شروع شود و دقیقا 11 رقم باشد")])
    birth_date = models.DateField('تاریخ تولد',null=True,blank=True)
    gender = models.CharField(max_length=10,choices=GenderOption.choices, null=True, blank=True, verbose_name='جنسیت')
    profile_picture = models.ImageField(verbose_name='عکس پروفایل', upload_to='profile_pictures', default='profile_pictures/default.jpg',blank=True)
    email = models.EmailField(unique=True, verbose_name="ایمیل")
    email_verified = models.BooleanField(default=False,verbose_name="ایمیل تایید شده")
    
    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربر'
        
    def __str__(self):
        return f"{self.username}"


class EmailVerificationOTP(models.Model):
    user = models.ForeignKey(MyUser,on_delete=models.CASCADE, related_name="email_verification_codes", verbose_name="کاربر")
    code_hash = models.CharField(max_length=128, verbose_name="هش کد تایید")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    expires_at = models.DateTimeField(verbose_name="زمان انقضا")
    attempts = models.PositiveSmallIntegerField(default=0, verbose_name="تعداد تلاش های ناموفق")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان استفاده")
    
    class Meta:
        verbose_name = "کد تایید ایمیل"
        verbose_name_plural = "کد تایید ایمیل"
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"کد تایید ایمیل برای  {self.user.username}"
    

class EmailChangeRequest(models.Model):
    user=models.OneToOneField(MyUser,on_delete=models.CASCADE, related_name = "email_change_request", verbose_name="کاربر")
    new_email = models.EmailField(verbose_name="ایمیل جدید")
    code_hash = models.CharField(max_length=128, verbose_name="هش کد تایید")
    previous_code_hashes = models.JSONField(default=list, blank=True, verbose_name="هش کد های قبلی")
    created_at = models.DateTimeField(verbose_name="زمان ایجاد")
    expires_at = models.DateTimeField(verbose_name="زمان انقضا")
    attempts = models.PositiveSmallIntegerField(default=0, verbose_name="تعداد تلاش های ناموفق")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان استفاده")
    
    class Meta:
        verbose_name = "درخواست تغییر ایمیل"
        verbose_name_plural = "درخواست  تغییر ایمیل "
        
    def __str__(self):
        return f"درخواست تغییر ایمیل {self.user.username}"