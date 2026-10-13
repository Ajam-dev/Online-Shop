from django.urls import path
from orders import views

app_name ="orders"

urlpatterns = [
    path("checkout/", views.checkout_view,name = "checkout"),
    path("cancel/<int:order_id>/", views.cancel_order_view, name = "cancel_order"),
    path("my-orders/",views.order_history_view, name="history"),
    path("my-orders/<int:order_id>/", views.order_detail_view, name = "detail"),
    path('my-orders/<int:order_id>/redirect', views.reorder_view, name = "reorder"),
]