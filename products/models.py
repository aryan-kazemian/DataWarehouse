from django.db import models
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey
from django.core.exceptions import ValidationError
from suppliers.models import Supplier


class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, null=True)

    class Meta:
        db_table = "Brand"
        ordering = ["name"]
        verbose_name = "Brand"
        verbose_name_plural = "Brands"

    def save(self, *args, **kwargs):
        if not self.slug or (self.pk and Brand.objects.get(pk=self.pk).name != self.name):
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Brand.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)


    def __str__(self):
        return self.name

class Category(MPTTModel):
    name = models.CharField(max_length=255, unique=True)
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        db_table = "Category"
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def clean(self):
        level = 1
        parent = self.parent

        while parent:
            level += 1
            if level > 3:
                raise ValidationError({
                    "parent": "Category hierarchy cannot exceed 3 levels."
                })
            parent = parent.parent

    def save(self, *args, **kwargs):
        if not self.slug or (self.pk and Category.objects.get(pk=self.pk).name != self.name):
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(
        default=1,
        help_text="Product rating from 1 to 5"
    )
    expire_date = models.DateField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    is_exciting = models.BooleanField(default=False)
    free_shipping = models.BooleanField(default=False)
    has_gift = models.BooleanField(default=False)
    is_budget_friendly = models.BooleanField(default=False)
    price = models.PositiveIntegerField()
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        related_name="products"
    )
    category = TreeForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Product"
        ordering = ["-created_at"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name

class Variant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants"
    )
    sku = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "Variant"

    class Meta:
        db_table = "Variant"
        ordering = ["-created_at"]
        verbose_name = "Variant"
        verbose_name_plural = "Variants"

    def __str__(self):
        return f"{self.product.name} - {self.sku}"

class VariantInvoiceQuantity(models.Model):
    variant = models.ForeignKey(
        "Variant", 
        on_delete=models.CASCADE, 
        related_name="variant_invoice_quantities"
    )
    invoice = models.ForeignKey(
        "suppliers.PurchaseInvoice",
        on_delete=models.CASCADE,
        related_name="variant_quantities"
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "VariantInvoiceQuantity"
        verbose_name = "Variant Invoice Quantity"
        verbose_name_plural = "Variant Invoice Quantities"
        unique_together = ("variant", "invoice")

    def __str__(self):
        return f"{self.variant.sku} x {self.quantity} for Invoice #{self.invoice.id}"