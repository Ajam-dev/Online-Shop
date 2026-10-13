from django.urls import path
from products import views

app_name = "products"

urlpatterns = [
    path("",views.product_list, name ="product_list"),
    path("<slug:slug>/", views.product_detail, name="product_detail"),
]
