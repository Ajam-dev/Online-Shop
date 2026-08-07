from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class GenderOption(models.TextChoices):
    male = ('m','مرد')
    female = ('f','زن')
    none = ('n','نمیخواهم مشخص کنم')
    
class RoleChoices(models.TextChoices):
    staff_user = ('su','کارمند پشتیبان')
    admin_user = ('au','کارمند محصولات')
    manager_user = ('mu','مدیر')
    general_user = ('gu','کاربر عادی')


class MyUser(AbstractUser):
    phone_number = models.CharField(max_length=11,null=True,blank=True,verbose_name='شماره تلفن')
    birth_date = models.DateField('تاریخ تولد',null=True,blank=True)
    gender = models.CharField(max_length=10,choices=GenderOption.choices, null=True, blank=True, verbose_name='جنسیت')
    profile_picture = models.ImageField(verbose_name='عکس پروفایل', upload_to='profile_pictures', default='profile_pictures/default.jpg',blank=True)
    
    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربر'
        
    def __str__(self):
        return f"{self.username}"

    
