from django.core.exceptions import ValidationError
from cart.models import Cart
from orders.models import Address, OrderItem, Order, Status
from django.db import transaction
import uuid
from products.models import Product, ProductVariant


def generate_order_number():
    return uuid.uuid4().hex[:20]

def reserve_order_stock(order):
    """
    موجودی مورد نیاز سفارش را رزرو می کند
    این تابع  باید داخل transaction.atomic() استفاده شود.
    موجودی واقی کم نمی شود؛ فقط reserved_stock افزایش پیدا میکند
    """
    items = list(
        order.items.all().order_by(
            "product_id",
            "variant_id",
            "id",
        )
    )
    
    locked_inventory = {}
    required_quantities = {}
    
    for item in items:
        if item.product_id is None:
            raise ValidationError(
                f"محصول «{item.product_name}» دیگر موجود نیست"
            )
        
        if item.variant_id:
            key = ("variant", item.variant_id)
            if key not in locked_inventory:
                variant = (ProductVariant.objects.select_for_update().get(pk=item.variant_id))
                locked_inventory[key] = variant
            required_quantities[key] = (required_quantities.get(key,0) + item.quantity)
        else:
            key = ("product", item.product_id)
            if key not in locked_inventory:
                product = (Product.objects.select_for_update().get(pk=item.product_id))
                locked_inventory[key] = product
            required_quantities[key] = (
                required_quantities.get(key,0) +item.quantity 
            )
            
    for key, inventory in locked_inventory.items():
        required_quantity = required_quantities[key]
        available_stock = (
            inventory.stock - inventory.reserved_stock
        )
        
        if available_stock < required_quantity:
            if key[0] == "variant":
                raise ValidationError(
                    f"موجودی تنوع «{inventory}»"
                    f"برای این سفارش کافی نیست"
                )
            raise ValidationError(
                f"موجودی «{inventory.name}»"
                f"برای این سفارش کافی نیست"
            )
            
    for key, inventory in locked_inventory.items():
        required_quantity = required_quantities[key]
        inventory.reserved_stock += required_quantity
        inventory.save(
            update_fields = ["reserved_stock"]
        )

def release_order_stock(order):
    """
    رزرو موجودی سفارش را آزاد می کند
    این تابع باید داخل transaction.atomic اجرا شود.
    موجودی واقعی (stock) تغییر نمی کند؛
    ققط reserved_stock کاهش پیدا می کند.
    """
    items = list(
        order.items.all().order_by(
            "product_id",
            "variant_id",
            "id",
        )
    )
    
    locked_inventory = {}
    reserved_quantities = {}
    
    for item in items:
        if item.variant_id:
            key = ("variant", item.variant_id)
            if key not in locked_inventory:
                variant = (ProductVariant.objects.select_for_update().get(pk=item.variant_id))
                locked_inventory[key] = variant
            reserved_quantities[key] = (reserved_quantities.get(key,0) + item.quantity)
        
        else:
            key = ("product", item.product_id)
            if key not in locked_inventory:
                product = (Product.objects.select_for_update().get(pk=item.product_id))
                locked_inventory[key] = product
            reserved_quantities[key] = (reserved_quantities.get(key, 0) + item.quantity)
            
    for key, inventory in locked_inventory.items():
        quantity = reserved_quantities[key]
        if inventory.reserved_stock < quantity:
            raise ValidationError(
                "مقادر موجودی رزرو شده این سفارش معتبر نیست"
            )
        inventory.reserved_stock -= quantity
        inventory.save(
            update_fields=["reserved_stock"]
        )
        
def refresh_order_prices(order):
    items = OrderItem.objects.filter(order = order)
    total_amount = 0
    for item in items:
        if item.product is None:
            raise ValidationError(f"محصول «{item.product_name}» دیگر موجود نیست.")
        product = item.product
        
        if not product.is_active:
            raise ValidationError(f"محصول «{item.product_name}» دیگر فعال نیست.")
        
        if not product.is_available:
            raise ValidationError(f"محصول «{item.product_name}» قابل سفارش نیست.")
        
        if item.variant_id:
            if item.variant is None:
                raise ValidationError(f"محصول «{item.product_name}» قابل سفارش نیست.")
        
            variant = item.variant
            
            if variant.product_id != product.id:
                raise ValidationError(f"تنوع انتخاب شده برای محصول «{item.product_name}» معتبر نیست.")
            
            if not variant.is_active:
                raise ValidationError(f"تنوع محصول «{item.product_name}» فعال نیست.")
            
            price = variant.final_price
        else:
            price = product.final_price
            
        item.unit_price = price
        item.total_price = price * item.quantity
        item.save(update_fields=["unit_price","total_price"])
        
        total_amount += item.total_price
        
    order.total_amount = total_amount
    order.save(update_fields = ["total_amount", "update_at"])
    
    return order

def checkout (user, address):
    
    if address is None:
        raise ValidationError("لطفا یک آدرس برای سفارش انتخاب کنید")

    if address.user_id != user.id:
        raise ValidationError("این آدرس متعلق به شما نیست.")
    
    try:
        cart = Cart.objects.prefetch_related(
            "items__product",
            "items__variant"
        ).get(user=user)
        
    except Cart.DoesNotExist:
        raise ValidationError("سبد خرید شما وجود ندارد")

    if not cart.items.exists():
        raise ValidationError("سبد خرید خالی است.")

    total_amount = 0
    
    for item in cart.items.all():
        product = item.product
        variant = item.variant
        
        if not product.is_active:
            raise ValidationError(
                f"محصول «{product.name}» در حال حاضر فعال نیست."
            )
            
        if not product.is_available:
            raise ValidationError(
                f"محصول «{product.name}» در حال حاضر قابل سفارش نیست"
            )
            
            
        if variant is not None and variant.product_id != product.id:
            raise ValidationError(
                f"تنوع انتخاب شده برای محصول «{product.name}» معتبر نیست"
            )
            
        if item.quantity < product.min_order_quantity:
            raise ValidationError(
                f"حداقل تعداد سفارش برای محصول «{product.name}»"
                f"{product.min_order_quantity} عدد است."
            )
            
        if product.max_order_quantity and item.quantity > product.max_order_quantity:
            raise ValidationError(
                f"حداکثر تعداد سفارش برای محصول «{product.name}»"
                f"{product.max_order_quantity}"
            )

        if variant is not None and not variant.is_active:
            raise ValidationError(
                f"تنوع انتخاب شده برای محصول «{product.name}» در حال حاضر فعال نیست"
            )
            
        available_stock = (
            variant.available_stock if variant is not None else product.available_stock
        )
        
        if available_stock <= 0:
            raise ValidationError(
                f"موجودی محصول «{product.name}» کافی نیست"
            )
        
        if item.quantity > available_stock:
            raise ValidationError(
                f"موجودی محصول «{product.name}» برای تعداد درخواستی کافی نیست"
            )

        unit_price = (
            variant.final_price if variant is not None else product.final_price
        )
        
        total_price = unit_price * item.quantity
        total_amount += total_price
        
    with transaction.atomic():
        order = Order.objects.create(
            user = user,
            order_number = generate_order_number(),
            status = Status.PENDING_PAYMENT,
            recipient_name = address.recipient_name,
            phone_number = address.phone_number,
            province = address.province,
            city = address.city,
            address = address.address,
            postal_code = address.postal_code,
            plaque = address.plaque,
            unit = address.unit,
            
            total_amount = total_amount,
            
        )
        
        for item in cart.items.all():
            product = item.product
            variant = item.variant 
            
            unit_price = (
                variant.final_price if variant is not None else product.final_price
            )
            
            total_price = unit_price * item.quantity
            
            OrderItem.objects.create(
                order=order,
                product = product,
                variant = variant,
                
                product_name = product.name,
                sku = variant.sku if variant is not None else "",
                
                quantity = item.quantity,
                unit_price = unit_price,
                total_price = total_price,
            )
        
        from payments.services import create_payment
        payment = create_payment(order)    
    return order, payment
        
def finalize_order(order):
    """
    رزرو موجودی سفارش را به فروش قطعی تبدیل می کند 
    در این مرحله :
    - stock کاهش پیدا می کند
    - reserved_stock کاهش پیدا می کند
    - سبد خرید خالی می شود
    - سفارش COMPLETED می شود
    این تابع باید داخل transaction.atomic() اجرا شود.
    """
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        
        if order.status == Status.COMPLETED:
            return order
        
        if order.status != Status.PAID:
            raise ValidationError(
                "این سفارش قابل نهایی سازی نیست"
            )
        
        items = list(
            order.items.all().order_by(
                "product_id",
                "variant_id",
                "id",
            )
        )
        
        locked_inventory = {}
        required_quantities = {}
            
        for item in items:
            if item.product_id is None:
                raise ValidationError(
                    f"محصول «{item.product_name}» دیگر موجود نیست"
                )
            if item.variant_id:
                key = ("variant", item.variant_id)
                if key not in locked_inventory:                    
                    variant = (
                        ProductVariant.objects.select_for_update().get(pk=item.variant_id)
                    )
                    locked_inventory[key] = variant
                required_quantities[key] = (required_quantities.get(key,0) + item.quantity)
            
            else:
                key = ("product", item.product_id)
                if key not in locked_inventory:
                    product = (Product.objects.select_for_update().get(pk=item.product_id))
                    locked_inventory[key] = product
                required_quantities[key] = (required_quantities.get(key,0) + item.quantity)
            
        for key, inventory in locked_inventory.items():
            required_quantity = required_quantities[key]
            
            if inventory.reserved_stock < required_quantity:
                raise ValidationError(
                    "موجودی رزرو شده این سفارش کافی نیست."
                )
            
            if inventory.stock < required_quantity:
                if key[0] == "variant":
                    raise ValidationError(
                        f"موجودی تنوع «{inventory}» کافی نیست "
                    )
                raise ValidationError(
                    f"موجودی «{inventory.name}» کافی نیست"
                )
                
        for key, inventory in locked_inventory.items():
            required_quantity = required_quantities[key]
            inventory.stock -= required_quantity
            inventory.reserved_stock -= required_quantity
            inventory.save(
                update_fields = ["stock","reserved_stock"]
            )
        
                 
        cart = Cart.objects.filter(user_id = order.user_id).first()
        if cart:
            cart.items.all().delete()
            
        order.status = Status.COMPLETED
        order.save(update_fields=["status","update_at"])
        
    return order