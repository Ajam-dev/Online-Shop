from django import forms
from accounts.models import MyUser
from django.core.validators import FileExtensionValidator

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100, label="نام کاربری")
    password = forms.CharField(max_length=30, label = "گذرواژه")
    
    