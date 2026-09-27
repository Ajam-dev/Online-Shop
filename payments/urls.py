from django.urls import path
from payments.views import test_gateway, test_payment_result

app_name = "payments"

urlpatterns = [
    path("test-gateway/<int:payment_id>/",test_gateway,name="test_gateway"),
    path("test-gateway/<int:payment_id>/<str:result>/", test_payment_result, name="test_payment_result")    
]
