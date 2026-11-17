from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from accounts.forms import LoginForm, RegisterForm, PasswordChangeForm, EmailVerificationForm, ProfileForm, EmailChangeForm, EmailChangeVerificationForm
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from accounts.utils import send_email_verification_otp, verify_email_otp, send_email_change_otp, verify_email_change_otp
from accounts.models import MyUser, EmailVerificationOTP, EmailChangeRequest
from django.utils import timezone
from django.contrib.auth.views import PasswordResetConfirmView
from django.conf import settings
from django.core.mail import send_mail
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.views import PasswordResetView
import logging


# Create your views here.

logger = logging.getLogger(__name__)

def login_view(request):
    form = LoginForm()
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username = username, password = password)
            if user:
                if user.is_active:
                    if not user.email_verified:
                        messages.error(request,"ابتدا ایمیل خود را تایید کنید.")
                        return redirect("accounts:login")
                    login(request, user)
                    messages.success(request, "خوش آمدید")
                    return redirect("products:product_list")
                messages.error(request,"حساب کاربری شما فعال نیست.")
                return redirect("accounts:login")
            messages.error(request, "نام کاربری یا رمز عبور اشتباه است")
    return render(request, "accounts/login.html", {"form":form})

def register_view(request):
    form = RegisterForm()
    
    if request.method == "POST":
        form = RegisterForm(request.POST)
        
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.email_verified = False
            user.save()
            
            request.session["pending_email_verification_user_id"] = user.id
            
            try:
                send_email_verification_otp(user)
                messages.success(request,"کد تایید به ایمیل شما ارسال شد")
                
            except Exception:
                logger.exception("Registeration email verification OTP sending failed")
                messages.error(request, "ارسال ایمیل با مشکل مواجه شد. لطفا کمی بعد دوباره تلاش کنید.")
            
            return redirect("accounts:verify_email")
    return render(request, "accounts/register.html", {"form":form})

@require_POST
def logout_view(request):
    logout(request)
    messages.success(request,"با موفقیت از حساب کاربری خارج شدید")
    return redirect("accounts:login")

@login_required(login_url="accounts:login")
def password_change_view(request):
    form = PasswordChangeForm(user=request.user)
    if request.method == "POST":
        form = PasswordChangeForm(
            user=request.user,
            data=request.POST
        )
        
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            messages.success(request,"گذرواژه شما باموفقیت تغییر کرد")
            return redirect("products:product_list")
    return render(request,"accounts/password_change.html",{"form":form})

def verify_email_view(request):
    user_id = request.session.get("pending_email_verification_user_id")
    
    if not user_id:
        messages.error(request,"درخواست تایید ایمیل معتبر نیست.")
        return redirect("accounts:register")
    
    user = MyUser.objects.filter(id=user_id, email_verified = False).first()
    
    if not user:
        request.session.pop("pending_email_verification_user_id", None)
        messages.error(request, "حساب کاربری مورد نظر پیدا نشد.")
        return redirect("accounts:register")
    
    form = EmailVerificationForm()
    
    if request.method == "POST":
        form = EmailVerificationForm(request.POST)
        
        if form.is_valid():
            code = form.cleaned_data["code"]
            is_verified, message = verify_email_otp(user,code)
            
            if is_verified:
                request.session.pop("pending_email_verification_user_id", None)
                login(request, user)
                messages.success(request, message)
                return redirect("products:product_list")

            messages.error(request, message)
    return render(request, "accounts/verify_email.html",{"form":form})

@require_POST
def resend_verification_otp_view(request):
    user_id = request.session.get("pending_email_verification_user_id")
    
    if not user_id:
        messages.error(request, "درخواست تایید ایمیل معتبر نیست.")
        return redirect("accounts:register")
    
    user = MyUser.objects.filter(id=user_id, email_verified = False).first()
    
    if not user:
        request.session.pop("pending_email_verification_user_id", None)
        messages.error(request, "حساب کاربری مورد نظر یافت نشد.")
        return redirect("accounts:register")
    
    last_otp = EmailVerificationOTP.objects.filter(user=user).first()
    
    if last_otp:
        elapsed_time = timezone.now() - last_otp.created_at
        
        if elapsed_time.total_seconds() < 60:
            remaining_time = 60 - int(elapsed_time.total_seconds())
            messages.error(request, f"برای دریاف کد جدید باید {remaining_time} ثانیه صبر کنید.")
            
            return redirect("accounts:verify_email")
    try:   
        send_email_verification_otp(user)
        messages.success(request,"کد تایید جدید به ایمیل شما ارسال شد.")
    except Exception:
        messages.error(request,"ارسال ایمیل با مشکل مواجه شد لطفا کمی بعد دوباره تلاش کنید")
    
    return redirect("accounts:verify_email")

@login_required
def profile_view(request):
    return render(request,"accounts/profile.html",{"user":request.user})


@login_required
def profile_edit_view(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            form.save()
            messages.success(request,"اطلاعات پروفایل شما با موفقیت بروز رسانی شد.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)
    
    return render(request,"accounts/profile_edit.html", {"form":form})

@login_required
def email_change_view(request):
    if not request.user.email_verified:
        messages.error(request,"ابتدا باید ایمیل فعلی خود را تایید کنید.")
        return redirect("accounts:profile")
    
    if request.method == "POST":
        form = EmailChangeForm(request.POST, user=request.user)
        
        if form.is_valid():
            new_email = form.cleaned_data["new_email"]
            
            last_request = EmailChangeRequest.objects.filter(user=request.user).first()
            if (
                last_request
                and last_request.used_at is None
                and (timezone.now() - last_request.created_at).total_seconds() < 60
            ):
                messages.error(request, "برای ثبت درخواست جدید باید 60 ثانیه صبر کنید")
                return redirect("accounts:email_change")
            
            try:
                send_email_change_otp(request.user, new_email)
                messages.success(request,"کد تایید به ایمیل جدید شما ارسال شد.")
                return redirect("accounts:verify_email_change")
            
            except Exception as error:
                logger.exception("Email change OTP sending failed")
                messages.error(request,"ارسال ایمیل با مشکل مواجه شد لطفا کمی بعد دوباره تلاش کنید.")
    else:
        form = EmailChangeForm(user=request.user)
        
    return render(request, "accounts/email_change.html",{"form":form})

@login_required
def verify_email_change_view(request):
    email_request = EmailChangeRequest.objects.filter(user=request.user, used_at__isnull = True).first()
    
    if not email_request:
        messages.error(request, "درخواست فعال تغییر ایمیلی پیدا نشد.")
        return redirect("accounts:email_change")
    
    if request.method == "POST":
        form = EmailChangeVerificationForm(request.POST)
        
        if form.is_valid():
            old_email = request.user.email
            code = form.cleaned_data["code"]
            
            is_verified, message = verify_email_change_otp(request.user, code)
            
            if is_verified:
                
                messages.success(request, message)
                try:
                    send_count = send_mail(
                        subject="اطلاع رسانی تغییر ایمیل حساب کاربری",
                        message=(
                            "ایمیل حساب کاربری شما با موفقیت تغییر کرد.\n\n"
                            f"ایمیل جدید: {request.user.email}\n\n"
                            "اگر شما این تغییر را انجام نداده اید،"
                            "هرچه سریع تر با پشتیبانی تماس بگیرید"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[old_email],
                        fail_silently=False
                    )
                    if send_count != 1:
                        raise RuntimeError("ارسال ایمیل اطلاع رسانی ناموفق بود.")
                    
                except Exception:
                    logger.exception("Email change notification email sending failed")
                    
                return redirect("accounts:profile")
            messages.error(request, message)
    else:
        form = EmailChangeVerificationForm()
        
    return render(request,"accounts/verify_email_change.html",{"form":form, "email_request":email_request})

@login_required
@require_POST
def resend_email_change_otp_view(request):
    email_request = EmailChangeRequest.objects.filter(user=request.user, used_at__isnull = True).first()
    if not email_request:
        messages.error(request, "درخواست تایید ایمیلی پیدا نشد")
        return redirect("accounts:email_change")
    
    last_request = email_request
    
    elapsed_time = (timezone.now() - last_request.created_at).total_seconds()
    
    if elapsed_time < 60:
        remaining_time = 60 - int(elapsed_time)
        messages.error(request, f"برای دریاف کد  جدید باید {remaining_time} ثانیه صبر کنید.")
        return redirect("accounts:verify_email_change")
    
    try:
        send_email_change_otp(request.user, last_request.new_email)
        messages.success(request, "کد تایید جدید به ایمیل شما ارسال شد")
        
    except Exception as error:
        logger.exception("Resending email change OTP failed")
        messages.error(request, "ارسال ایمیل بامشکل مواجه شد لطفا کمی بعد دوباره تلاش کنید.")
        
    return redirect("accounts:verify_email_change")

class CustomPasswordResetView(PasswordResetView):
    @method_decorator(ratelimit(key="ip", rate="5/15m", method="POST", block=False))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        if getattr(self.request, "limited", False):
            return redirect(self.get_success_url())
        return super().form_valid(form)
    

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        try:
            send_mail(
                subject="تغییر گذرواژه حساب کاربری.",
                message=(
                    "گذرواژه حساب شما با موفقیت تغییر کرد.\n"
                    "اگر شما این تغییر را انجام نداده اید، "
                    "هرچه سریع تر با پشتیبانی تماس بگیرید"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.user.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Password reset notificaion email sending failed")
        
        return response