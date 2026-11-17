from django.shortcuts import render, get_object_or_404
from products.models import Product, ProductVariant

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
    
    variants = list(ProductVariant.objects.filter(product=product, is_active=True,).prefetch_related("variant_attributes__attribute_value__attribute").order_by("id"))
    
    product_attributes = (product.product_attributes.filter(attribute__is_active=True,).select_related("attribute").prefetch_related("attribute__values"))
    
    variants_data = []
    used_value_ids = {}
    
    for variant in variants:
        variant_attributes = {}
        for item in variant.variant_attributes.all():
            attribute_id = item.attribute_value.attribute_id
            value_id = item.attribute_value_id
            variant_attributes[str(attribute_id)] = value_id
            used_value_ids.setdefault(attribute_id, set()).add(value_id)
            
        variants_data.append({
            "id":variant.id,
            "sku":variant.sku,
            "price":variant.effective_price,
            "discount_percent":variant.effective_discount_percent,
            "final_price": variant.final_price,
            "available_stock": variant.available_stock,
            "is_in_stock": variant.is_in_stock,
            "attributes": variant_attributes,
            "image":(variant.image.url if variant.image else None),
            "attributes":variant_attributes,
        })
        
    product_attributes_data = []
    
    for product_attribute in product_attributes:
        attribute = product_attribute.attribute
        value_ids = used_value_ids.get(attribute.id, set())
        if not value_ids:
            continue
        
        values = list(attribute.values.filter(id__in=value_ids,).order_by("id"))
        
        product_attributes_data.append({"attribute": attribute, "values":values,})
            
    return render(request, "products/product_detail.html",{"product":product, "images":product.images.all(), "variants":variants, "product_attributes":product_attributes_data, "variants_data":variants_data},)

