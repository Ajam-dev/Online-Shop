from django.shortcuts import get_object_or_404 ,render, redirect
from payments.models import Payment
from payments.services import verify_payment
from django.contrib import messages

# Create your views here.

def test_gateway(request, payment_id):
    payment = get_object_or_404(Payment,id = payment_id)
    return render(request,"payments/test_gateway.html",{"payment":payment})

def test_payment_result(request, payment_id, result):
    if request.method != "POST":
        return redirect("payment:test_gateway", payment_id=payment_id)
    
    payment = get_object_or_404(Payment, id=payment_id)
    success = result == "success"
    
    try:
        verify_payment(payment=payment,success=success)
    
    except Exception as e:
        messages.error(request, str(e))
        
        return redirect("payments:test_gateway", payment_id=payment_id)

    if success:
        return render(request, "payments/payment_success.html",{"payment":payment})
        
