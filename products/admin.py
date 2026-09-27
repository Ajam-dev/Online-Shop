from django.contrib import admin
from products.models import Category, Product, Brand, ProductImage, ProductFavorite, ProductReview, ProductVariant, Attribute, AttributeValue, VariantAttribute

# Register your models here.

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Brand)
admin.site.register(ProductImage)
admin.site.register(ProductVariant)
admin.site.register(ProductFavorite)
admin.site.register(ProductReview)
admin.site.register(AttributeValue)
admin.site.register(Attribute)
admin.site.register(VariantAttribute)
