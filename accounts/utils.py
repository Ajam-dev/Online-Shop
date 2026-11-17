import secrets
from  datetime import timedelta
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail  import send_mail
from django.utils import timezone
from accounts.models import EmailVerificationOTP, EmailChangeRequest, MyUser
from django.contrib.auth.hashers import check_password
from django.db import transaction

def send_email_verification_otp(user):
    now= timezone.now()
    code = f"{secrets.randbelow(1000000):06d}"

    with transaction.atomic():
        EmailVerificationOTP.objects.filter(
            user=user,
            used_at__isnull=True
        ).update(used_at=now)

        otp = EmailVerificationOTP.objects.create(
            user=user,
            code_hash=make_password(code),
            expires_at=now + timedelta(minutes=5)
        )    
    
    try:
        sent_count = send_mail(
            subject="تایید ایمیل فروشگاه آنلاین",
            message=f"""
                سلام {user.username} عزیز،
                کد تایید ایمیل شما:
                {code}
                این کد تا5 دقیقه اعتبار دارد.
                اگر درخواست ثبت نام نداده اید، این پیام رانادیده بگیرید
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        if sent_count != 1:
            raise RuntimeError("ارسال ایمیل با موفقیت انجام نشد")
    except Exception:
        otp.used_at = timezone.now()
        otp.save(update_fields=["used_at"])
        raise
    
    with transaction.atomic():
        EmailVerificationOTP.objects.filter(user=user, used_at__isnull=True).exclude(pk=otp.pk).update(used_at=now)    
    
def verify_email_otp(user, code):
    
    now = timezone.now()
    
    with transaction.atomic():
        otp = EmailVerificationOTP.objects.filter(
            user=user,
            used_at__isnull=True,
            expires_at__gt=now,
            attempts__lt=5
        ).first()
        
        if not otp:
            return False, "کد تایید معتبر نیست یا منقضی شده است."
        
        previous_otps = EmailVerificationOTP.objects.filter(
            user=user,
            used_at__isnull=False,
            created_at__gte=now - timedelta(minutes=5)
        ).exclude(pk=otp.pk).order_by("created_at")[:5]
        
        for previous_otp in previous_otps:
            if check_password(code,previous_otp.code_hash):
                return False, "کد معتبر نیست یا منقضی شده است."
        
        if not check_password(code,otp.code_hash):
            otp.attempts += 1
            
            if otp.attempts >= 5:
                otp.used_at = now
                otp.save(update_fields=["attempts","used_at"])
                
                return False, "تعداد تلاش های مجاز تمام شده است. کد جدید درخواست کنید"
            
            otp.save(update_fields=["attempts"])

            remaining = 5 - otp.attempts
            
            return False, f"کد اشتباه است. {remaining} فرصت دیگر دارید."
        
        otp.used_at = now
        otp.save(update_fields=["used_at"])
        
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        
        return True, "ایمیل شما با موفقیت تایید شد."

def send_email_change_otp(user, new_email):
    now = timezone.now()
    
    code = f"{secrets.randbelow(1000000):06d}"
    
    code_hash = make_password(code)
    
    existing_request = EmailChangeRequest.objects.filter(user=user).first()
    
    previous_code_hashers = []
    
    if existing_request:
        previous_code_hashers = list(existing_request.previous_code_hashes or [])
        
        if existing_request.code_hash:
            previous_code_hashers.append(existing_request.code_hash)
            
    previous_code_hashers = previous_code_hashers[-5:]
    
    try: 
        sent_count = send_mail(
            subject="تغییر ایمیل فروشگاه آنلاین",
            message=f"""
                سلام {user.username} عزیز، 
                درخواست تایید ایمیل حساب کاربری شما ثبت شده است.
                
                کد تایید:
                {code}
                
                این کد تا 5 دقیقه اعتبار دارد
                اگر شما درخواست تایید ایمیل نداده اید این پیام را نادیده بگیرید.
            """,
            from_email = settings.DEFAULT_FROM_EMAIL,
            recipient_list=[new_email],
            fail_silently = False
            
        )
        
        if sent_count != 1:
            raise RuntimeError("ارسال ایمیل با موفقیت انجام نشد")
        
    except:
        raise
    
    EmailChangeRequest.objects.update_or_create(
        user=user,
        defaults={
            "new_email": new_email,
            "code_hash": code_hash,
            "previous_code_hashes": previous_code_hashers,
            "created_at": now,
            "expires_at": now + timedelta(minutes=5),
            "attempts": 0,
            "used_at": None,
        }
    )
    
def verify_email_change_otp(user, code):
    now = timezone.now()
    
    with transaction.atomic():
        email_request = EmailChangeRequest.objects.select_for_update().filter(
            user=user,
            used_at__isnull=True,
            expires_at__gt=now,
            attempts__lt=5
        ).first()
        
        if not email_request:
            return False, "کد تایید معتبر نیست یا منقضی شده است."
        
        for previous_hash in email_request.previous_code_hashes:
            if check_password(code, previous_hash):
                return False, "کد تایید معتبر نیست یا منقضی شده است."
        
        if not check_password(code, email_request.code_hash):
            email_request.attempts += 1
            
            if email_request.attempts >= 5:
                email_request.used_at = now
                email_request.save(update_fields=["attempts","used_at"])
                
                return False, "تعداد تلاش های مجاز تمام شده است. درخواست جدید ثبت کنید."
            
            email_request.save(update_fields=["attempts"])
            
            remaining = 5 - email_request.attempts
            
            return False, f"کد اشتباه است. {remaining} فرصت دیگر دارید."
        
        if MyUser.objects.filter(email__iexact=email_request.new_email).exclude(pk=user.pk).exists():
            email_request.used_at = now
            email_request.save(update_fields=["used_at"])
            
            return False, "این ایمیل قبلا برای حساب دیگری ثبت شده است."
        
        user.email = email_request.new_email
        user.save(update_fields =["email"])
        
        email_request.used_at = now
        email_request.save(update_fields=["used_at"])
        
    return True, "ایمیل حساب کاربری شما با موفقیت تغییر کرد."