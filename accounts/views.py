from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from accounts.forms import LoginForm
from django.contrib import messages

# Create your views here.

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
                    login(request, user)
                    messages.success(request, "خوش آمدید")
                    return redirect("products:product_list")
                messages.error(request,"حساب کاربری شما فعال نیست.")
                return redirect("accounts:login")
            messages.error(request, "نام کاربری یا رمز عبور اشتباه است")
    return render(request, "accounts/login.html", {"form":form})