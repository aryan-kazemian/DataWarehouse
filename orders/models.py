import jdatetime

from django.db import models
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from products.models import Variant, VariantInvoiceQuantity
from analytics.models import DimVariantOrder, DimDate, FactSales
from .constants import ORDER_STATUS_CHOICES


ACTIVE_STATUSES = ["initial", "process", "sent", "done"]
CANCEL_STATUSES = ["cancel", "rejected"]


class Order(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="orders"
    )
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, null=True)
    is_synced_analytics = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Order"
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def clean(self):
        old_status = None
        if self.pk:
            old_status = Order.objects.filter(pk=self.pk).values_list("status", flat=True).first()

    def save(self, *args, **kwargs):
        old_status = None
        if self.pk:
            old_status = Order.objects.filter(pk=self.pk).values_list("status", flat=True).first()

        super().save(*args, **kwargs)

        for item in self.items.select_related("variant").all():
            if not item.variant:
                continue

            if old_status in ACTIVE_STATUSES and self.status in CANCEL_STATUSES:
                for oiviq in item.variant_invoice_quantities.all():
                    viq = oiviq.variant_invoice_quantity
                    viq.quantity += oiviq.deducted_quantity
                    viq.save(update_fields=["quantity"])
                item.variant_invoice_quantities.all().delete()

            elif old_status in CANCEL_STATUSES and self.status in ACTIVE_STATUSES:
                remaining_qty = item.quantity
                total_available = VariantInvoiceQuantity.objects.filter(variant=item.variant).aggregate(
                    total=Sum("quantity")
                )["total"] or 0
                if total_available < item.quantity:
                    raise ValidationError(
                        f"Not enough stock for variant {item.variant.sku}: available {total_available}, requested {item.quantity}"
                    )
                item.variant_invoice_quantities.all().delete()
                viqs = VariantInvoiceQuantity.objects.filter(variant=item.variant).order_by("id")
                for viq in viqs:
                    if remaining_qty <= 0:
                        break
                    deducted = min(viq.quantity, remaining_qty)
                    viq.quantity -= deducted
                    viq.save(update_fields=["quantity"])
                    OrderItemVariantInvoiceQuantity.objects.create(
                        order_item=item,
                        variant_invoice_quantity=viq,
                        deducted_quantity=deducted
                    )
                    remaining_qty -= deducted

        if getattr(self, "skip_analytics", False):
            return

        try:
            fact_sale = FactSales.objects.get(order_id=self.pk)
        except FactSales.DoesNotExist:
            fact_sale = None

        if fact_sale:
            fact_sale.status = self.status
            if fact_sale.date is None:
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
                fact_sale.date = dim_date

            fact_sale.variants.clear()
            for item in self.items.select_related("variant").all():
                if not item.variant:
                    continue
                dim_variant, created = DimVariantOrder.objects.get_or_create(
                    variant_id=item.variant.id,
                    defaults={
                        "variant_sku": item.variant.sku,
                        "product_id": item.variant.product.id,
                        "color": item.variant.color,
                        "size": item.variant.size,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "discount_percent": item.discount_percent,
                        "total_price": item.total_price,
                        "total_after_discount": item.total_after_discount,
                    }
                )
                fact_sale.variants.add(dim_variant)
            fact_sale.save()
        else:
            self.is_synced_analytics = False

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
    unit_price = models.PositiveIntegerField(editable=False)
    discount_percent = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    total_price = models.PositiveIntegerField(editable=False)
    total_after_discount = models.PositiveIntegerField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "OrderItem"
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def clean(self):
        if not self.variant:
            return

        old_quantity = 0
        if self.pk:
            old_quantity = OrderItem.objects.filter(pk=self.pk).values_list("quantity", flat=True).first() or 0

        total_available = VariantInvoiceQuantity.objects.filter(variant=self.variant).aggregate(
            total=Sum("quantity")
        )["total"] or 0
        total_available += old_quantity

        if total_available < self.quantity:
            raise ValidationError(
                f"Not enough stock for variant {self.variant.sku}: available {total_available}, requested {self.quantity}."
            )

    def save(self, *args, **kwargs):
        now = timezone.now()
        self.created_at = self.created_at or now
        self.updated_at = now

        self.unit_price = getattr(self.variant.product, 'price', 0) if self.variant else 0
        self.total_price = self.unit_price * self.quantity
        self.total_after_discount = int(self.total_price * (100 - self.discount_percent) / 100)

        old_variant_id = None
        old_quantity = None
        had_deductions = False
        if self.pk:
            old = OrderItem.objects.filter(pk=self.pk).values("variant_id", "quantity").first()
            if old:
                old_variant_id = old.get("variant_id")
                old_quantity = old.get("quantity")
            had_deductions = OrderItemVariantInvoiceQuantity.objects.filter(order_item_id=self.pk).exists()

        super().save(*args, **kwargs)

        if had_deductions and (old_variant_id != (self.variant.id if self.variant else None) or old_quantity != self.quantity):
            for oiviq in OrderItemVariantInvoiceQuantity.objects.filter(order_item=self):
                viq = oiviq.variant_invoice_quantity
                viq.quantity += oiviq.deducted_quantity
                viq.save(update_fields=["quantity"])
            OrderItemVariantInvoiceQuantity.objects.filter(order_item=self).delete()

        if self.variant and self.order.status in ACTIVE_STATUSES:
            remaining_qty = self.quantity
            viqs = VariantInvoiceQuantity.objects.filter(variant=self.variant).order_by("id")
            for viq in viqs:
                if remaining_qty <= 0:
                    break
                deducted = min(viq.quantity, remaining_qty)
                if deducted <= 0:
                    continue
                viq.quantity -= deducted
                viq.save(update_fields=["quantity"])
                OrderItemVariantInvoiceQuantity.objects.create(
                    order_item=self,
                    variant_invoice_quantity=viq,
                    deducted_quantity=deducted
                )
                remaining_qty -= deducted

    def __str__(self):
        variant_name = str(self.variant) if self.variant else "No Variant"
        return f"{variant_name} x {self.quantity} in Order #{self.order.id}"


class OrderItemVariantInvoiceQuantity(models.Model):
    order_item = models.ForeignKey(
        "OrderItem",
        on_delete=models.CASCADE,
        related_name="variant_invoice_quantities"
    )
    variant_invoice_quantity = models.ForeignKey(
        VariantInvoiceQuantity,
        on_delete=models.CASCADE,
        related_name="+"
    )
    deducted_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "OrderItemVariantInvoiceQuantity"
        verbose_name = "Order Item Variant Invoice Quantity"
        verbose_name_plural = "Order Item Variant Invoice Quantities"

    def __str__(self):
        return f"{self.order_item} deducted {self.deducted_quantity} from {self.variant_invoice_quantity}"
