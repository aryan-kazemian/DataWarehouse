from django.db import models
from django.utils import timezone
from django.db.models import Sum
from django.core.validators import MinValueValidator, MaxValueValidator
from products.models import Variant, Product
from accounts.models import User
from analytics.models import DimUser, DimProductBase, DimVariantOrder, DimDate, FactSales


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("canceled", "Canceled"),
    ]

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="orders"
    )
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="pending")
    is_synced_analytics = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Order"
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "order_item"
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def save(self, *args, **kwargs):
        if self.variant:
            self.unit_price = self.variant.product.price
        else:
            self.unit_price = 0

        self.total_price = self.unit_price * self.quantity
        self.total_after_discount = int(self.total_price * (100 - self.discount_percent) / 100)

        super().save(*args, **kwargs)

    def __str__(self):
        variant_name = self.variant.__str__() if self.variant else "No Variant"
        return f"{variant_name} x {self.quantity} in Order #{self.order.id}"

