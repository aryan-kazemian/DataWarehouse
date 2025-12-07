from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from orders.models import OrderItem
from .models import FactSales

@receiver(post_save, sender=OrderItem)
@receiver(post_delete, sender=OrderItem)
def update_factsales_totals_on_item_change(sender, instance, **kwargs):
    order = instance.order
    if not order:
        return
    try:
        fact = FactSales.objects.get(order_id=order.id)
    except FactSales.DoesNotExist:
        return
    totals = order.items.aggregate(
        total_price=Sum('total_price'),
        total_after_discount=Sum('total_after_discount')
    )
    total_price = totals['total_price'] or 0
    total_after_discount = totals['total_after_discount'] or 0
    fact.total_price = total_price
    fact.total_price_after_discount = total_after_discount
    fact.save(update_fields=['total_price', 'total_price_after_discount'])
