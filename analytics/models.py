from django.db import models
from orders.constants import ORDER_STATUS_CHOICES

# DIMENSIONS TABLES

class DimDate(models.Model):
    full_date = models.DateField(unique=True)
    jalali_date = models.CharField(max_length=10, null=True, blank=True)
    day_of_week = models.CharField(max_length=10, null=True, blank=True)
    month_name = models.CharField(max_length=20, null=True, blank=True)
    quarter = models.PositiveSmallIntegerField(null=True, blank=True)
    is_holiday = models.BooleanField(default=False, blank=True)

    class Meta:
        db_table = "DimDate"


    def __str__(self):
        return str(self.full_date)

class DimUser(models.Model):
    user_id = models.IntegerField(unique=True)
    username = models.CharField(max_length=150)
    gender = models.CharField(max_length=10, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    registration_date = models.DateField()
    age_range = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "DimUser"

    def __str__(self):
        return self.username

class DimProductBase(models.Model):
    product_id = models.IntegerField()
    name = models.CharField(max_length=255)
    rating = models.PositiveSmallIntegerField(default=1)
    expire_date = models.DateField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    is_exciting = models.BooleanField(default=False)
    free_shipping = models.BooleanField(default=False)
    has_gift = models.BooleanField(default=False)
    is_budget_friendly = models.BooleanField(default=False)
    price = models.PositiveIntegerField()
    brand = models.CharField(max_length=255)
    supplier = models.CharField(max_length=255, blank=True, null=True)
    category_level_1 = models.CharField(max_length=255, blank=True, null=True)
    category_level_2 = models.CharField(max_length=255, blank=True, null=True)
    category_level_3 = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "DimProductBase"

    def __str__(self):
        return self.name
    
class DimVariantOrder(models.Model):
    variant_id = models.IntegerField()
    variant_sku = models.CharField(max_length=100, unique=True)
    product_id = models.IntegerField()
    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.PositiveIntegerField(help_text="Price of one unit")
    discount_percent = models.PositiveSmallIntegerField(default=0, help_text="0-100%")
    total_price = models.PositiveIntegerField(editable=False, null=True)
    total_after_discount = models.PositiveIntegerField(editable=False, null=True)

    class Meta:
        db_table = "DimVariantOrder"

    def __str__(self):
        return f"{self.variant_sku}"

# FACT TABLES

class FactSales(models.Model):
    order_id = models.IntegerField(null=True)
    date = models.ForeignKey(DimDate, on_delete=models.PROTECT)
    variants = models.ManyToManyField(DimVariantOrder)
    user = models.ForeignKey(DimUser, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, null=True)
    total_price = models.PositiveIntegerField(null=True)
    total_price_after_discount = models.PositiveIntegerField(null=True)
    exclude_from_analytics = models.BooleanField(default=False)


    class Meta:
        db_table = "FactSales"

    def __str__(self):
        return f"Order: Date:{self.date} - User:{self.user}"
    
    def save(self, *args, **kwargs):
        if self.exclude_from_analytics:
            is_update = self.pk is not None

            old_total = 0
            old_status = None
            old_date_id = None

            if is_update:
                old = FactSales.objects.get(pk=self.pk)
                old_total = old.total_price_after_discount or 0
                old_status = (old.status or "").lower()
                old_date_id = old.date_id

                try:
                    fa_old = FactAnalytics.objects.get(date_id=old_date_id)
                    fa_old.total_order_quantity -= old_total

                    if old_status == "initial":
                        fa_old.initial_order_quantity -= old_total
                    elif old_status == "process":
                        fa_old.process_order_quantity -= old_total
                    elif old_status == "sent":
                        fa_old.sent_order_quantity -= old_total
                    elif old_status == "done":
                        fa_old.done_order_quantity -= old_total
                    elif old_status == "cancel":
                        fa_old.cancel_order_quantity -= old_total
                    elif old_status == "rejected":
                        fa_old.rejected_order_quantity -= old_total

                    self.exclude_from_analytics = False
                    fa_old.save()
                except FactAnalytics.DoesNotExist:
                    pass

        super().save(*args, **kwargs)

class FactAnalytics(models.Model):
    date = models.ForeignKey(DimDate, on_delete=models.PROTECT)
    total_order_quantity = models.IntegerField(default=0)
    initial_order_quantity = models.IntegerField(default=0)
    process_order_quantity = models.IntegerField(default=0)
    sent_order_quantity = models.IntegerField(default=0)
    done_order_quantity = models.IntegerField(default=0)
    cancel_order_quantity = models.IntegerField(default=0)
    rejected_order_quantity = models.IntegerField(default=0)

    class Meta:
        db_table = "FactAnalytics"

    def __str__(self):
        return f"Analytics for {self.date.full_date} (Total: {self.total_order_quantity})"
    