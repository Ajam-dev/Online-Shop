from django.shortcuts import render, get_object_or_404
from products.models import Product

# Create your views here.

def product_list(request):
    products = Product.objects.filter(
        is_active = True,
        is_available = True,
    ).select_related(
        "category",
        "brand",
    )
    
    return render(request, "products/product_list.html",{"products":products})

def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category","brand").prefetch_related("images"),
        slug=slug,is_active = True,
        is_available = True
        )
    
    return render(request, "products/product_detail.html",{"product":product, "images":product.images.all()})
