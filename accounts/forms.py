from django import forms
from accounts.models import MyUser
from django.core.validators import FileExtensionValidator
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.contrib.auth import get_user_model

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100, label="نام کاربری")
    password = forms.CharField(max_length=128, label = "گذرواژه")
    
class RegisterForm(forms.ModelForm):
    password = forms.CharField(label = "گذرواژه", widget=forms.PasswordInput())
    confirm_password = forms.CharField(label="تکرار گذرواژه", widget=forms.PasswordInput())
    
    class Meta:
        model = MyUser
        fields = ["username", "email"]
        labels = {
            "username":"نام کاربری",
            "email":"ایمیل",
        }
        error_messages = {"email":{"unique":"این ایمیل قبلا برای یک حساب کاربری ثبت شده است."}}
    
    def clean_username(self):
        username = self.cleaned_data["username"]
        
        if MyUser.objects.filter(username = username).exists():
            raise forms.ValidationError("این نام کاربری قبلا انتخاب شده است.")
        
        return username
    
    def clean(self):
        cleaned_data = super().clean()
        
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password","گذروازه و تکرار آن یکسان نیستند.")
            
        return cleaned_data
    
    def clean_password(self):
        password = self.cleaned_data["password"]
        
        user = self.instance
        user.username = self.cleaned_data.get("username","")
        user.email = self.cleaned_data.get("email","")
        
        try:
            validate_password(password, user=user)
        except forms.ValidationError as error:
            self.add_error("password", error)
            
        return password
    

class PasswordResetUsernameForm(PasswordResetForm):
    email = forms.EmailField(required=False, widget=forms.HiddenInput())
    username = forms.CharField(max_length=150, label="نام کاربری", widget=forms.TextInput(attrs={"placeholder":"نام کاربری خودرا وارد کنید"}))
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        user_model = get_user_model()
        
        try:
            user = user_model._default_manager.get(username=username)
        except user_model.DoesNotExist:
            self.user = None
            cleaned_data["email"] = ""
            return cleaned_data
            
        self.user = user
        cleaned_data["email"] = user.email or ""
        
        return cleaned_data
    
    def get_users(self,email):
        user = getattr(self, "user", None)
        
        if (
            user 
            and user.email 
            and user.is_active
            and user.email_verified 
            and user.has_usable_password()
        ):
            return iter([user])
        return iter([])
    
class EmailVerificationForm(forms.Form):
    code = forms.CharField(max_length=6, min_length=6, label="کد تایید ایمیل", widget=forms.TextInput(attrs={"placeholder":"کد شش رقمی را وارد کنید", "autocomplete":"one-time-code", "inputmode":"numeric"}))
    
    def clean_code(self):
        code = self.cleaned_data["code"]
        
        if not code.isdigit():
            raise forms.ValidationError("کد تایید باید فقط شامل اعداد باشد")
        return code
    
    
class ProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(required=False, validators=[FileExtensionValidator(allowed_extensions=["jpg","jpeg","png","webp"])], label="تصویر پروفایل")
    
    class Meta:
        model = MyUser
        fields = [
            "first_name","last_name","phone_number","birth_date","gender","profile_picture"
        ]
        labels = {
            "first_name":"نام",
            "last_name":"نام خانوادگی",
            "phone_number":"شماره تلفن",
            "birth_date":"تاریخ تولد",
            "gender":"جنسیت",
            "profile_picture":"تصویر پروفایل",
        }
        
        widgets = {
            "birth_date": forms.DateInput(attrs={"type":"date"}),
        }
        
    def clean_profile_picture(self):
        image = self.cleaned_data.get("profile_picture")
        
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("حجم تصویر نباید بیشتر از 5 مگابایت باشد")
        
        return image
    
class EmailChangeForm(forms.Form):
    current_password = forms.CharField(label="کذرواژه فعلی", widget=forms.PasswordInput(attrs={"placeholder":"گذرواژه فعلی خود را وارد کنید", "autocomplete":"current-password"}))
    
    new_email = forms.EmailField(label="ایمیل جدید", max_length=254, widget=forms.EmailInput(attrs={"placeholder":"ایمیل جدید خود را وارد کنید", "autocomplete":"email"}))
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
    def clean_current_password(self):
        password = self.cleaned_data["current_password"]
        
        if not self.user.check_password(password):
            raise forms.ValidationError("گذرواژه فعلی اشتباه است")
        
        return password
        
    def clean_new_email(self):
        new_email = self.cleaned_data["new_email"].strip().lower()
        
        if MyUser.objects.filter(email__iexact=new_email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("این ایمیل قبلا برای حساب کاربری دیگری ثبت شده است.")
        
        if new_email.lower() == self.user.email.lower():
            raise forms.ValidationError("ایمیل جدید با ایمیل فعلی شما یکسان است.")
        
        return new_email
    

class EmailChangeVerificationForm(forms.Form):
    code = forms.CharField(max_length=6, min_length=6, label="کد تایید ایمیل", widget=forms.TextInput(attrs={"placeholder":"کد تایید شش رقمی را وارد کنید","autocomplete":"one-time-code","inputmode":"numeric"}))
    
    def clean_code(self):
        code=self.cleaned_data["code"]
        
        if not code.isdigit():
            raise forms.ValidationError("کد تایید باید فقط شامل اعداد باشد.")
        
        return code