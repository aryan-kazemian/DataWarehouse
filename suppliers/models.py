from django.db import models
from .constants import PURCHASE_INVOICE_STATUS_CHOICES
from django.apps import apps

class Supplier(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "Supplier"
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"

    def __str__(self):
        return self.name

class PurchaseInvoice(models.Model):
    title = models.CharField(max_length=100, null=True)
    Supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=PURCHASE_INVOICE_STATUS_CHOICES,
        default="pending"
    )
    delivery_date = models.DateField(null=True, blank=True)
    delivery_time = models.TimeField(null=True, blank=True)

    class Meta:
        db_table = "PurchaseInvoice"
        verbose_name = "Purchase Invoice"
        verbose_name_plural = "Purchase Invoices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice #{self.pk} - {self.created_at.date()}"

    def update_total_price(self):
        total = sum(item.total_price for item in self.items.all())
        self.total_price = total
        self.save(update_fields=["total_price"])

    def save(self, *args, **kwargs):
        VariantInvoiceQuantity = apps.get_model("products", "VariantInvoiceQuantity")

        is_new = self._state.adding
        super().save(*args, **kwargs)

        if self.status == "done":
            items = self.items.select_related("product_variant").all()
            viq_objs = []
            existing_viqs = set(
                VariantInvoiceQuantity.objects.filter(invoice=self)
                .values_list("variant_id", flat=True)
            )
            for item in items:
                if item.product_variant and item.product_variant.id not in existing_viqs:
                    viq_objs.append(
                        VariantInvoiceQuantity(
                            variant=item.product_variant,
                            invoice=self,
                            quantity=item.quantity
                        )
                    )
            if viq_objs:
                VariantInvoiceQuantity.objects.bulk_create(viq_objs, ignore_conflicts=True)

        total = sum(item.total_price for item in self.items.all())
        if total != self.total_price:
            super().save(update_fields=["total_price"])

class PurchaseItem(models.Model):
    invoice = models.ForeignKey(
        "suppliers.PurchaseInvoice",
        on_delete=models.CASCADE,
        related_name="items"
    )
    product_variant = models.ForeignKey(
        "products.Variant",
        on_delete=models.PROTECT,
        null=True
    )
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        db_table = "PurchaseItem"
        verbose_name = "Purchase Item"
        verbose_name_plural = "Purchase Items"

    def __str__(self):
        return f"{self.product_variant.product.name} x {self.quantity}" if self.product_variant else f"Item #{self.id}"

    def save(self, *args, **kwargs):
        if self.product_variant:
            self.total_price = self.product_variant.product.price * self.quantity
        else:
            self.total_price = 0
        super().save(*args, **kwargs)
