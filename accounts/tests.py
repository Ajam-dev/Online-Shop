from django.test import TestCase
from django.urls import reverse
from django.core import mail
from django.contrib.auth import get_user_model
from accounts.models import EmailVerificationOTP
from accounts.utils import verify_email_otp
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from accounts.utils import send_email_verification_otp
from accounts.models import EmailChangeRequest
from accounts.utils import send_email_change_otp, verify_email_change_otp
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from django.test import override_settings
from accounts.forms import EmailChangeForm

# Create your tests here.


User = get_user_model()

class RegisterationTests(TestCase):
    def test_register_page_status_code(self):
        response = self.client.get(reverse("accounts:register"))
        
        self.assertEqual(response.status_code, 200)
        
    def  test_successful_registeration(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username":"testuser",
                "email":"test@example.com",
                "password":"TestPassword123!",
                "confirm_password":"TestPassword123!"
            }
        ) 
        
        user = User.objects.get(username = "testuser")
        
        self.assertFalse(user.email_verified)
        
        self.assertEqual(len(mail.outbox),1)
        
        self.assertRedirects(response, reverse("accounts:verify_email"))
        
        
    def test_registeration_with_different_passwords(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username":"testuser2",
                "email":"test2@example.com",
                "password":"TestPassword123!Secure",
                "confirm_password":"DifferentPassword123!"
            }
        )
        
        self.assertFalse(User.objects.filter(username="testuser2").exists())
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(response.status_code, 200)
            
    def test_registeration_with_dublicate_email(self):
        User.objects.create_user(
            username="existinguser",
            email="dublicate@example.com",
            password="TestPassword123!Secure"
        )
        
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username":"newuser",
                "email":"dublicate@example.com",
                "password":"TestPassword123!Secure",
                "confirm_password":"TestPassword123!Secure",
            }
        )
        
        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(response.status_code, 200)
        
class EmailVerificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="verifyuser",
            email="verify@example.com",
            password="TestPassword123!Secure",
            email_verified = False,
        )
        
    def test_successful_email_verification(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username":"verifyuser2",
                "email":"verify2@example.com",
                "password":"TestPassword123!Secure",
                "confirm_password":"TestPassword123!Secure",
            }
        )
        
        user = User.objects.get(username="verifyuser2")
        
        otp = EmailVerificationOTP.objects.get(user=user, used_at__isnull=True)
        
        code = mail.outbox[0].body.split("کد تایید ایمیل شما:")[1].strip().split()[0]
        
        is_verified, message = verify_email_otp(user, code)
        
        self.assertTrue(is_verified)
        self.assertTrue(user.email_verified)
        otp.refresh_from_db()
        self.assertIsNotNone(otp.used_at)
        
    def test_wrong_email_verification_code(self):
        otp = EmailVerificationOTP.objects.create(
            user=self.user,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        is_verified, message = verify_email_otp(self.user, "654321")
        
        otp.refresh_from_db()
        self.assertFalse(is_verified)
        self.assertFalse(self.user.email_verified)
        self.assertEqual(otp.attempts, 1)
        self.assertIsNone(otp.used_at)
        self.assertIn("کد اشتباه است", message)
    
    def test_email_verification_lockout_after_five_attempts(self):
        otp = EmailVerificationOTP.objects.create(
            user=self.user,
            code_hash = make_password("123456"),
            expires_at = timezone.now() + timedelta(minutes=5)
        )
        
        for _ in range(5):
            is_verified, message = verify_email_otp(self.user, "654321")
            
        otp.refresh_from_db()
        
        self.assertFalse(is_verified)
        self.assertFalse(self.user.email_verified)
        self.assertEqual(otp.attempts, 5)
        self.assertIsNotNone(otp.used_at)
        self.assertIn("تعداد تلاش های مجاز تمام شده است", message)
        
    
    def test_expired_email_verification_code(self):
        otp = EmailVerificationOTP.objects.create(
            user=self.user,
            code_hash = make_password("123456"),
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        
        is_verified, message = verify_email_otp(self.user,"123456")
        
        otp.refresh_from_db()
        
        self.assertFalse(is_verified)
        self.assertFalse(self.user.email_verified)
        self.assertEqual(otp.attempts, 0)
        self.assertIsNone(otp.used_at)
        self.assertIn("کد تایید معتبر نیست یا منقضی شده است", message)

    def test_old_otp_invalid_after_resend(self):
        with patch(
            "accounts.utils.secrets.randbelow",
            side_effect=[111111, 222222]
        ):
            send_email_verification_otp(self.user)
            send_email_verification_otp(self.user)
            
        otps = list(EmailVerificationOTP.objects.filter(user=self.user).order_by("pk"))
        
        old_otp = otps[0]
        new_otp = otps[1]
        
        is_verified, message = verify_email_otp(self.user, "111111")
        
        new_otp.refresh_from_db()
        
        self.assertFalse(is_verified)
        self.assertFalse(self.user.email_verified)
        self.assertIsNotNone(old_otp.used_at)
        self.assertEqual(new_otp.attempts, 0)
        self.assertIn("کد معتبر نیست یا منقضی شده است", message)
        self.assertEqual(len(mail.outbox), 2)
        

class EmailChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="changeuser",
            email="old@example.com",
            password="TestPassword123!Secure",
            email_verified =True
        )
        
    @patch("accounts.utils.secrets.randbelow", return_value=123456)
    def test_successful_email_change_otp_sending(self, mock_randbelow):
        send_email_change_otp(self.user, "new@example.com")
        
        email_request = EmailChangeRequest.objects.get(user=self.user)
        
        self.assertEqual(email_request.new_email, "new@example.com")
        self.assertEqual(self.user.email, "old@example.com")
        self.assertEqual(len(mail.outbox),1)
        self.assertIn("123456", mail.outbox[0].body)
        self.assertIsNone(email_request.used_at)
        self.assertEqual(email_request.attempts, 0)
        
            
    @patch("accounts.utils.secrets.randbelow", return_value=123456)
    def test_successful_email_change_verification(self, mock_randbelow):
        send_email_change_otp(self.user, "new@example.com")
        
        is_verified, message = verify_email_change_otp(self.user, "123456")
        
        self.user.refresh_from_db()
        
        email_request = EmailChangeRequest.objects.get(user=self.user)
        
        self.assertTrue(is_verified)
        self.assertEqual(self.user.email, "new@example.com")
        self.assertIsNotNone(email_request.used_at)
        self.assertIn("با موفقیت تغییر کرد", message)
            
    @patch("accounts.utils.secrets.randbelow", return_value=123456)
    def test_wrong_email_change_code(self, mock_randbelow):
        send_email_change_otp(self.user, "new@email.com")
        
        is_verified, message = verify_email_change_otp(self.user, "654321")
        
        email_request = EmailChangeRequest.objects.get(user=self.user)
        
        self.user.refresh_from_db()
        email_request.refresh_from_db()
        
        self.assertFalse(is_verified)
        self.assertEqual(self.user.email, "old@example.com")
        self.assertEqual(email_request.attempts, 1)
        self.assertIsNone(email_request.used_at)
        self.assertIn("کد اشتباه است", message)
        
    @patch("accounts.utils.secrets.randbelow", return_value=123456)
    def test_email_change_lockout_after_five_attempts(self, mock_randbelow):
        send_email_change_otp(self.user,"new@example.com")
        
        for _ in range(5):
            is_verified, message = verify_email_change_otp(self.user, "654321")
            
        email_request = EmailChangeRequest.objects.get(user=self.user)
        
        self.user.refresh_from_db()
        email_request.refresh_from_db()
        
        self.assertFalse(is_verified)
        self.assertEqual(self.user.email, "old@example.com")
        self.assertEqual(email_request.attempts, 5)
        self.assertIsNotNone(email_request.used_at)
        self.assertIn("تعداد تلاش های مجاز تمام شده است", message)
        
    @patch("accounts.utils.secrets.randbelow", return_value=123456)
    def test_expired_email_change_code(self, mock_randbelow):
        send_email_change_otp(self.user, "new@example.com")
        
        email_request = EmailChangeRequest.objects.get(user=self.user)
        
        email_request.expires_at = timezone.now() - timedelta(minutes=1)
        email_request.save(update_fields=["expires_at"])
        
        is_verified, message = verify_email_change_otp(self.user, "123456")
        
        self.user.refresh_from_db()
        
        self.assertFalse(is_verified)
        self.assertEqual(self.user.email, "old@example.com")
        self.assertEqual(email_request.attempts, 0)
        self.assertIsNone(email_request.used_at)
        self.assertIn("کد تایید معتبر نیست یا منقضی شده است", message)
        
    def test_old_email_change_code_invalid_after_resend(self):
        with patch("accounts.utils.secrets.randbelow", side_effect=[111111,222222]):
            send_email_change_otp(self.user, "new@example.com")
            
            send_email_change_otp(self.user, "new@example.com")
            
            email_request = EmailChangeRequest.objects.get(user=self.user)
            
            is_verified, message = verify_email_change_otp(self.user, "111111")
            
            email_request.refresh_from_db()
            self.user.refresh_from_db()
            
            self.assertFalse(is_verified)
            self.assertEqual(self.user.email, "old@example.com")
            self.assertEqual(email_request.attempts, 0)
            self.assertIn("کد تایید معتبر نیست یا منقضی شده است", message)
            self.assertEqual(len(mail.outbox), 2)
    
    @patch("accounts.utils.secrets.randbelow", return_value=123456)        
    def test_change_rejects_email_used_by_another_user(self, mock_randbelow):
        User.objects.create_user(
            username="anotheruser",
            email="new@example.com",
            password="TestPassword123!Secure",
            email_verified=True
        )
        
        send_email_change_otp(self.user, "new@example.com")
        
        is_verified, message = verify_email_change_otp(self.user, "123456")
        
        self.user.refresh_from_db()
        
        email_request = EmailChangeRequest.objects.get(user=self.user)
        
        self.assertFalse(is_verified)
        self.assertEqual(self.user.email, "old@example.com")
        self.assertIsNotNone(email_request.used_at)
        self.assertIn("قبلا برای حساب دیگری ثبت شده است", message)
        
    @patch("accounts.utils.secrets.randbelow", side_effect = [111111,222222])
    @patch("accounts.utils.send_mail", side_effect=[1, Exception("SMTP error")])
    def test_failed_resend_password_previous_request(self, mock_send_mail, mock_randbelow):
        send_email_change_otp(self.user, "new@example.com")
        
        previous_request = EmailChangeRequest.objects.get(user=self.user)
        
        previous_code_hash = previous_request.code_hash
        previous_created_at = previous_request.created_at
        
        with self.assertRaises(Exception):        
            send_email_change_otp(self.user, "another@example.com")

        previous_request.refresh_from_db()
        
        self.assertEqual(previous_request.new_email,"new@example.com")
        self.assertEqual(previous_request.code_hash, previous_code_hash)
        self.assertEqual(previous_request.created_at, previous_created_at)
        self.assertIsNone(previous_request.used_at)
        self.assertEqual(previous_request.attempts, 0)
        self.assertEqual(len(mail.outbox), 0)
        
    def test_email_change_resend_cooldown(self):
        now = timezone.now()
        
        code_hash = make_password("123456")
        
        email_request = EmailChangeRequest.objects.create(
            user=self.user,
            new_email="new@example.com",
            code_hash=code_hash,
            created_at=now,
            expires_at = now + timedelta(minutes=5),
        )
        
        self.client.force_login(self.user)
        
        response = self.client.post(reverse("accounts:resend_email_change_otp"))
        
        email_request.refresh_from_db()
        
        self.assertRedirects(response, reverse("accounts:verify_email_change"))
        
        self.assertEqual(len(mail.outbox),0)
        self.assertEqual(email_request.code_hash, code_hash)
        self.assertIsNone(email_request.used_at)
        
    @patch("accounts.utils.secrets.randbelow", return_value=222222)
    def test_email_change_resend_after_cooldown(self, mock_randbelow):
        old_code_hash = make_password("111111")
        
        EmailChangeRequest.objects.create(
            user=self.user,
            new_email="new@example.com",
            code_hash=old_code_hash,
            created_at=timezone.now() - timedelta(seconds=61),
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        
        self.client.force_login(self.user)
        
        response = self.client.post(reverse("accounts:resend_email_change_otp"))
        
        email_request = EmailChangeRequest.objects.get(user=self.user)
        
        self.assertRedirects(response, reverse("accounts:verify_email_change"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(email_request.new_email, "new@example.com")
        self.assertEqual(email_request.attempts, 0)
        self.assertIsNone(email_request.used_at)
        self.assertTrue(check_password("111111", email_request.previous_code_hashes[0]))
        self.assertTrue(check_password("222222", email_request.code_hash))
        
class ProfileAccessTests(TestCase):
    
    def test_profile_pages_require_login(self):
        urls = [
            reverse("accounts:profile"),
            reverse("accounts:profile_edit"),
            reverse("accounts:email_change"),
            reverse("accounts:verify_email_change"),
        ]
        
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response,f"{reverse("accounts:login")}?next={url}")
                
    def test_logged_in_user_can_view_profile(self):
        User=get_user_model()
        user = User.objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password="TestPassword123!Secure",
            first_name = "علی",
            last_name = "رضایی",
            email_verified = True,
        )
        
        self.client.force_login(user)
        
        response = self.client.get(reverse("accounts:profile"))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"], user)
        self.assertTemplateUsed(response, "accounts/profile.html")
        
    def test_logged_in_user_can_edit_profile(self):
        User = get_user_model()
        
        user = User.objects.create_user(
            username="edituser",
            email="edit@example.com",
            password="TestPassword123!Secure",
            email_verified=True,
        )
        
        self.client.force_login(user)
        
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "first_name": "علی",
                "last_name": "رضایی",
                "phone_number": "09123456789",
                "birth_date": "1300-02-21",
                "gender": "m",
            }
        )
        
        user.refresh_from_db()
        
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertEqual(user.first_name, "علی")
        self.assertEqual(user.last_name, "رضایی")
        self.assertEqual(user.phone_number, "09123456789")
        self.assertEqual(user.gender, "m")
        
    def test_profile_rejects_image_larger_than_5mb(self):
        User=get_user_model()
        
        user=User.objects.create_user(
            username="imageuser",
            email="image@example.com",
            password="TestPassword123!Secure",
            email_verified=True,
        )
        
        self.client.force_login(user)

        image =Image.effect_noise((3500, 3500), 100).convert("RGB")
        
        image_buffer = BytesIO()
        image.save(image_buffer, format="JPEG", quantity=100)
        image_content = image_buffer.getvalue()
        
        self.assertGreater(len(image_content), 5 * 1024 * 1024)
        
        large_image = SimpleUploadedFile("large.jpg", image_content, content_type="image/jpeg")

        response = self.client.post(
                reverse("accounts:profile_edit"),
                {
                    "first_name":"علی",
                    "lastname":"رضایی",
                    "phone_number":"09123456789",
                    "gender": "m",
                    "profile_picture": large_image
                }
            )
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn("حجم تصویر نباید بیشتر از 5 مگابایت باشد", response.context["form"].errors["profile_picture"],)
        
    def test_profile_rejects_invalid_image_extension(self):
        User = get_user_model()

        user = User.objects.create_user(
            username="invalidimageuser",
            email="invalidimage@example.com",
            password="TestPassword123!Secure",
            email_verified=True,
        )

        self.client.force_login(user)

        invalid_file = SimpleUploadedFile(
            "document.pdf",
            b"%PDF-1.4 test content",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "first_name": "علی",
                "last_name": "رضایی",
                "phone_number": "09123456789",
                "gender": "m",
                "profile_picture": invalid_file,
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn(
            "profile_picture",
            response.context["form"].errors,
        )

class LoginTests(TestCase):
    def setUp(self):
        User= get_user_model()
        self.user = User.objects.create_user(
            username="loginuser",
            email="login@example.com",
            password="TestPassword123!Secure",
            email_verified = True,
        )
        
    def test_user_can_login_with_valid_credentials(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "loginuser",
                "password": "TestPassword123!Secure",
            }
        )
        
        self.assertRedirects(response, reverse("products:product_list"))
        self.assertTrue(self.client.session.get("_auth_user_id"))
        
    def test_user_cannot_login_with_wrong_password(self):
        response = self.client.post(
                reverse("accounts:login"),
                {
                    "username": "loginuser",
                    "password": "WrongPassword123!"
                }
            )
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.session.get("_auth_user_id"))
        self.assertIn("نام کاربری یا رمز عبور اشتباه است", [str(message) for message in response.wsgi_request._messages])
        
        
    def test_unverified_user_cannot_login(self):
        User=get_user_model()
        
        user= User.objects.create_user(
            username="unverifieduser",
            email="unverified@example.com",
            password="TestPassword123!Secure",
            email_verified=False
        )
        
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username":"unverifieduser",
                "password":"TestPassword123!Secure",
            }
        )
        
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertFalse(self.client.session.get("_auth_user_id"))
        self.assertIn("ابتدا ایمیل خود را تایید کنید.", [str(message) for message in response.wsgi_request._messages])
        
    
    def test_user_can_logout(self):
        self.client.force_login(self.user)
        
        response = self.client.post(reverse("accounts:logout"))
        
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        

class PasswordResetTests(TestCase):
    def setUp(self):
        User=get_user_model()
        self.user=User.objects.create_user(
            username="resetuser",
            email="reset@example.com",
            password="TestPassword123!Secure",
            email_verified=True,
        )
        
    def test_verified_user_can_request_password_reset(self):
        response = self.client.post(reverse("accounts:password_reset"), {"username":"resetuser"},)
        
        self.assertRedirects(response, reverse("accounts:password_reset_done"),)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset@example.com", mail.outbox[0].to)
        
    def test_unknown_username_not_send_email(self):
        response = self.client.post(reverse("accounts:password_reset"), {"username":"unknown"})
        
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)
        
    def test_unverified_user_cannot_request_password_reset(self):
        User= get_user_model()
        User.objects.create_user(
            username="unverifiedreset",
            email="unverified.reset@example.com",
            password="TestPassword123!",
            email_verified=False,
        )
        
        response = self.client.post(reverse("accounts:password_reset"), {"username": "unverifiedreset"})
        
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_user_can_reset_password_with_valid_link(self):
        self.client.post(reverse("accounts:password_reset"), {"username":"resetuser"},)
        
        email_body = mail.outbox[0].body
        
        reset_url = next(
            line.strip()
            for line in email_body.splitlines()
            if "/accounts/reset/" in line
        )
        
        response = self.client.get(reset_url)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/reset/", response.url)
        
    def test_user_can_reset_password_with_valid_link(self):
        self.client.post(
            reverse("accounts:password_reset"),
            {"username": "resetuser"}
        )
        
        email_body = mail.outbox[0].body
        
        reset_url = next(
            line.strip()
            for line in email_body.splitlines()
            if "/accounts/reset/" in line
        )
        
        response = self.client.get(reset_url)
        
        self.assertEqual(response.status_code, 302)
        
        reset_url = response.url
        
        response = self.client.post(
            reset_url,
            {
                "new_password1": "NewPassword123!Secure",
                "new_password2": "NewPassword123!Secure"
            },
        )
        
        self.assertEqual(response.status_code, 302)
        
        self.user.refresh_from_db()
        
        self.assertTrue(self.user.check_password("NewPassword123!Secure"))
        self.assertFalse(self.user.check_password("TestPassword123!Secure"))
        
    def test_password_reset_link_cannot_be_used_twice(self):
        self.client.post(reverse("accounts:password_reset"), {"username":"resetuser"})
        
        email_body = mail.outbox[0].body
        
        reset_url = next(
            line.strip()
            for line in email_body.splitlines()
            if "/accounts/reset/" in line
        )
        
        response = self.client.get(reset_url)
        
        self.assertEqual(response.status_code, 302)
        
        reset_url = response.url
        
        self.client.post(
            reset_url,
            {
                "new_password1": "NewPassword123!Secure",
                "new_password2": "NewPassword123!Secure",
            },
        )
        
        self.assertEqual(
            response.status_code,
            302,
            msg=(
                response.context["form"].errors.as_text()
                if response.context and response.context.get("form")
                else response.content.decode()
            ),
        )
        
        self.user.refresh_from_db()
        
        response = self.client.get(reset_url)
        
        self.assertEqual(response.status_code, 200)
        
        self.assertNotContains(
                response,
                "name=\"new_password\"",
                html=False
            )
        
        self.assertFalse(self.user.check_password("TestPassword123!Secure"))
        
        self.user.refresh_from_db()
        
        self.assertTrue(self.user.check_password("NewPassword123!Secure"))
    
    
    @override_settings(PASSWORD_RESET_TIMEOUT=1)
    def test_password_reset_link_expires(self):
        self.client.post(reverse("accounts:password_reset"), {"username":"resetuser"})
        
        email_body = mail.outbox[0].body
        
        reset_url = next(
            line.strip()
            for line in email_body.splitlines()
            if "/accounts/reset/" in line
        )
        
        response = self.client.get(reset_url)
        
        self.assertEqual(response.status_code, 302)
        
        reset_url = response.url
        
        import time
        time.sleep(2)
        
        response = self.client.get(reset_url)
        
        self.assertEqual(response.status_code, 200)
        
        self.assertNotContains(
            response,
            'name="new_password1"',
            html=False,
        )
        
class PasswordChangeTests(TestCase):
    def setUp(self):
        User=get_user_model()
        self.user = User.objects.create_user(
            username="changeuser",
            email="change@example.com",
            password="OldPassword123!Secure",
            email_verified = True,
        )
        
    def test_user_can_change_password(self):
        self.client.force_login(self.user)
        
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "OldPassword123!Secure",
                "new_password1": "NewPassword123!Secure",
                "new_password2": "NewPassword123!Secure", 
            },
        )
        
        self.assertRedirects(response, reverse("products:product_list"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!Secure"))
        self.assertFalse(self.user.check_password("OldPassword123!Secure"))
        
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        
    def test_wrong_old_password_is_rejected(self):
        self.client.force_login(self.user)
        
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password":"WrongPassword123!",
                "new_password1": "NewPassword123!Secure",
                "new_password2": "NewPassword123!Secure",
            },
        )
        
        self.assertEqual(response.status_code, 200)
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword123!Secure"))
    
    def test_password_change_requires_login(self):
        response = self.client.get(reverse("accounts:password_change"))
        
        self.assertRedirects(response, f"{reverse("accounts:login")}?next={reverse("accounts:password_change")}",)
        
        
class PasswordResetNotificationTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="notificationuser",
            email="notification@example.com",
            password="OldPassword123!Secure",
            email_verified=True,
        )

    def get_valid_reset_url(self):
        self.client.post(
            reverse("accounts:password_reset"),
            {"username": "notificationuser"},
        )

        email_body = mail.outbox[0].body

        reset_url = next(
            line.strip()
            for line in email_body.splitlines()
            if "/accounts/reset/" in line
        )

        response = self.client.get(reset_url)
        self.assertEqual(response.status_code, 302)

        return response.url

    def test_notification_email_is_sent_after_password_reset(self):
        reset_url = self.get_valid_reset_url()

        response = self.client.post(
            reset_url,
            {
                "new_password1": "NewPassword123!Secure",
                "new_password2": "NewPassword123!Secure",
            },
        )

        self.assertRedirects(
            response,
            reverse("accounts:password_reset_complete"),
        )

        self.assertEqual(len(mail.outbox), 2)

        notification_email = mail.outbox[1]

        self.assertEqual(
            notification_email.to,
            ["notification@example.com"],
        )
        self.assertIn(
            "تغییر گذرواژه",
            notification_email.subject,
        )

    @patch("accounts.views.send_mail", side_effect=Exception("SMTP Error"))
    def test_password_reset_succeeds_if_notification_email_fails(self, mock_send_mail):
        reset_url = self.get_valid_reset_url()

        response = self.client.post(
            reset_url,
            {
                "new_password1": "NewPassword123!Secure",
                "new_password2": "NewPassword123!Secure",
            },
        )

        self.assertRedirects(
            response,
            reverse("accounts:password_reset_complete"),
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password("NewPassword123!Secure")
        )

        mock_send_mail.assert_called_once()
        

class EmailChangePasswordTests(TestCase):
    
    def setUp(self):
        User= get_user_model()
        
        self.user = User.objects.create_user(
            username="emailchangeuser",
            email="old@example.com",
            password="OldPassword123!Secure",
            email_verified=True,
        )
        
    def test_email_change_form_accepts_correct_password(self):
        form= EmailChangeForm(
            data={
                "current_password": "OldPassword123!Secure",
                "new_email": "new@example.com",
            },
            user=self.user
        )
        
        self.assertTrue(form.is_valid(), form.errors)
        
    def test_email_change_form_rejects_wrong_password(self):
        form = EmailChangeForm(
            data={
                "current_password":"WrongPassword123!Secure",
                "new_email":"new@example.com",
            },
            user=self.user,
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn("current_password", form.errors)
        
        
class EmailChangeViewPasswordTests(TestCase):
    
    def setUp(self):
        User=get_user_model()
        
        self.user = User.objects.create_user(
            username="emailchangeviewuser",
            email="old@example.com",
            password="OldPassword123!Secure",
            email_verified=True,
        )
        
        self.client.force_login(self.user)
        
    def test_email_change_rejects_wrong_current_password(self):
        response = self.client.post(
            reverse("accounts:email_change"),
            {
                "current_password": "WrongPassword123!Secure",
                "new_email": "new@example.com",
            },
        )
        
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response,"گذرواژه فعلی اشتباه است")
        
        self.assertFalse(EmailChangeRequest.objects.filter(user=self.user).exists())
        self.assertEqual(len(mail.outbox), 0)
        
    @patch("accounts.views.send_email_change_otp")
    def test_email_change_accepts_correct_current_password(self, mock_send_otp):

        self.assertFalse(
            EmailChangeRequest.objects.filter(user=self.user).exists()
        )

        response = self.client.post(
            reverse("accounts:email_change"),
            {
                "current_password": "OldPassword123!Secure",
                "new_email": "new@example.com",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            response.url,
            reverse("accounts:verify_email_change"),
        )

        mock_send_otp.assert_called_once_with(
            self.user,
            "new@example.com",
        )
        
class EmailChangeNotificationTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="notificationemailuser",
            email="old@example.com",
            password="OldPassword123!Secure",
            email_verified=True,
        )

        self.client.force_login(self.user)
        
        now = timezone.now()
        
        self.email_request = EmailChangeRequest.objects.create(
            user=self.user,
            new_email="new@example.com",
            code_hash=make_password("123456"),
            created_at=now,
            expires_at = now + timedelta(minutes=5),
            attempts = 0,
        )

    def change_email_successfully(self, user, code):
        user.email = "new@example.com"
        user.save(update_fields=["email"])

        return True, "ایمیل حساب کاربری شما با موفقیت تغییر کرد."

    @patch("accounts.views.verify_email_change_otp")
    @patch("accounts.views.send_mail")
    def test_notification_is_sent_to_old_email(
        self,
        mock_send_mail,
        mock_verify,
    ):
        mock_verify.side_effect = self.change_email_successfully

        response = self.client.post(
            reverse("accounts:verify_email_change"),
            {"code": "123456"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:profile"))

        mock_send_mail.assert_called_once()

        args, kwargs = mock_send_mail.call_args
        
        recipients = kwargs.get("recipient_list")
        if recipients is None:
            recipients = args[3]

        message = kwargs.get("message")
        if message is None:
            message = args[1]

        self.assertEqual(recipients, ["old@example.com"])
        self.assertIn("new@example.com", message)

    @patch(
        "accounts.views.verify_email_change_otp",
        return_value=(False, "کد تایید نامعتبر است."),
    )
    @patch("accounts.views.send_mail")
    def test_notification_is_not_sent_when_verification_fails(
        self,
        mock_send_mail,
        mock_verify,
    ):
        response = self.client.post(
            reverse("accounts:verify_email_change"),
            {"code": "123456"},
        )

        self.assertEqual(response.status_code, 200)
        mock_send_mail.assert_not_called()

    @patch("accounts.views.verify_email_change_otp")
    @patch(
        "accounts.views.send_mail",
        side_effect=Exception("SMTP Error"),
    )
    def test_email_change_succeeds_if_notification_fails(
        self,
        mock_send_mail,
        mock_verify,
    ):
        mock_verify.side_effect = self.change_email_successfully

        response = self.client.post(
            reverse("accounts:verify_email_change"),
            {"code": "123456"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:profile"))

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "new@example.com",
        )