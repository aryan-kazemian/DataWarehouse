import jdatetime
from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator, MaxValueValidator
from products.models import Variant
from analytics.models import  DimVariantOrder, DimDate, FactSales
from .constants import ORDER_STATUS_CHOICES



class Order(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="orders"
    )
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, null=True)
    is_synced_analytics = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "Order"
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def save(self, *args, **kwargs):
        if getattr(self, "skip_analytics", False):
            return super().save(*args, **kwargs)

        try:
            FactSale = FactSales.objects.get(order_id=self.pk)
        except FactSales.DoesNotExist:
            FactSale = None

        if FactSale:
            FactSale.status = self.status

            if FactSale.date is None:
                try:
                    dim_date = DimDate.objects.get(full_date=self.created_at.date())
                except DimDate.DoesNotExist:
                    j = jdatetime.date.fromgregorian(date=self.created_at.date())
                    dim_date = DimDate.objects.create(
                        full_date=self.created_at.date(),
                        jalali_date=f"{j.year}-{j.month:02d}-{j.day:02d}",
                        day_of_week=j.strftime("%A"),
                        month_name=j.strftime("%B"),
                        quarter=(1 if j.month <= 3 else 2 if j.month <= 6 else 3 if j.month <= 9 else 4),
                        is_holiday=(j.weekday() == 6)
                    )
                FactSale.date = dim_date

            FactSale.variants.clear()

            variant_ids = [item.variant.id for item in self.items.select_related('variant', 'variant__product')]
            existing_variants = DimVariantOrder.objects.filter(variant_id__in=variant_ids)
            variant_map = {v.variant_id: v for v in existing_variants}

            for item in self.items.all():
                dim_variant = variant_map.get(item.variant.id)

                if not dim_variant:
                    total_price = item.unit_price * item.quantity
                    total_after_discount = total_price * (100 - item.discount_percent) // 100

                    dim_variant = DimVariantOrder.objects.create(
                        variant_id=item.variant.id,
                        variant_sku=item.variant.sku,
                        product_id=item.variant.product.id,
                        color=item.variant.color,
                        size=item.variant.size,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        discount_percent=item.discount_percent,
                        total_price=total_price,
                        total_after_discount=total_after_discount,
                    )
                    variant_map[item.variant.id] = dim_variant

                FactSale.variants.add(dim_variant)

            FactSale.save()
        else:
            self.is_synced_analytics = False

        super().save(*args, **kwargs)




    def __str__(self):
        return f"Order #{self.id} by {self.user}"

    @property
    def total_after_discount(self):
        return self.items.aggregate(total=Sum('total_after_discount'))['total'] or 0

    @property
    def total_amount(self):
        return self.items.aggregate(total=Sum('total_price'))['total'] or 0



class OrderItem(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="items"
    )
    variant = models.ForeignKey(
        Variant,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.PositiveIntegerField(help_text="Price of one unit", editable=False)
    discount_percent = models.PositiveSmallIntegerField(default=0, help_text="0-100%",validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ])
    total_price = models.PositiveIntegerField(editable=False)
    total_after_discount = models.PositiveIntegerField(editable=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "OrderItem"
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def save(self, *args, **kwargs):
        if self.variant:
            self.unit_price = getattr(self.variant.product, 'price', 0)
        else:
            self.unit_price = 0

        self.total_price = self.unit_price * self.quantity
        self.total_after_discount = int(self.total_price * (100 - self.discount_percent) / 100)

        super().save(*args, **kwargs)


    def __str__(self):
        variant_name = self.variant.__str__() if self.variant else "No Variant"
        return f"{variant_name} x {self.quantity} in Order #{self.order.id}"

