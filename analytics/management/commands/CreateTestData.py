from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import AgeRange, User
from products.models import Brand, Category, Product, Variant
from orders.models import Order, OrderItem
from orders.constants import ORDER_STATUS_CHOICES
from suppliers.models import Supplier, PurchaseInvoice, PurchaseItem
from faker import Faker
import random
from datetime import timedelta

fake = Faker()

def random_date_last_year():
    today = timezone.now()
    days_back = random.randint(0, 365)
    return today - timedelta(days=days_back)

class Command(BaseCommand):
    help = "Creates full test data including suppliers, invoices, and orders with realistic statuses"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting test data generation..."))

        # ---- AGE RANGES ----
        age_ranges = []
        age_ranges_data = [
            ("0-18", 0, 18),
            ("19-25", 19, 25),
            ("26-35", 26, 35),
            ("36-50", 36, 50),
            ("51+", 51, 100),
        ]
        for name, min_age, max_age in age_ranges_data:
            ar, _ = AgeRange.objects.get_or_create(name=name, min_age=min_age, max_age=max_age)
            age_ranges.append(ar)
            self.stdout.write(f"Created AgeRange: {ar.name}")

        # ---- USERS ----
        users = []
        for i in range(500):
            user = User.objects.create_user(
                username=fake.unique.user_name(),
                email=fake.unique.email(),
                password="123456",
                city=fake.city(),
                gender=random.choice(["male", "female", "other"]),
                age_range=random.choice(age_ranges),
                registration_date=random_date_last_year()
            )
            users.append(user)
            self.stdout.write(f"Created User: {user.username}")

        # ---- BRANDS ----
        brands = []
        for i in range(50):
            brand, _ = Brand.objects.get_or_create(name=fake.unique.company())
            brands.append(brand)
            self.stdout.write(f"Created Brand: {brand.name}")

        # ---- SUPPLIERS ----
        suppliers = []
        for i in range(20):
            supplier_name = fake.unique.company()
            supplier, _ = Supplier.objects.get_or_create(name=supplier_name)
            suppliers.append(supplier)
            self.stdout.write(f"Created Supplier: {supplier.name}")

        # ---- ASSIGN BRANDS TO SUPPLIERS ----
        for brand in brands:
            supplier = random.choice(suppliers)
            brand.supplier = supplier
            brand.save()
            self.stdout.write(f"Assigned Brand: {brand.name} to Supplier: {supplier.name}")

        # ---- CATEGORIES ----
        parents = []
        for i in range(6):
            parent, _ = Category.objects.get_or_create(name=fake.unique.word())
            parents.append(parent)
            self.stdout.write(f"Created Parent Category: {parent.name}")

        subcategories = []
        for parent in parents:
            for _ in range(30):
                subcat, _ = Category.objects.get_or_create(name=fake.unique.word(), parent=parent)
                subcategories.append(subcat)
                self.stdout.write(f"Created Subcategory: {subcat.name} under Parent: {parent.name}")

        # ---- PRODUCTS ----
        products = []
        for i in range(500):
            product = Product.objects.create(
                name=fake.unique.word(),
                description=fake.text(max_nb_chars=200),
                price=random.randint(100, 5000),
                rating=random.randint(1, 5),
                brand=random.choice(brands),
                category=random.choice(subcategories),
                created_at=random_date_last_year(),
                updated_at=random_date_last_year()
            )
            products.append(product)
            self.stdout.write(f"Created Product: {product.name} | Brand: {product.brand.name} | Category: {product.category.name}")

        # ---- VARIANTS ----
        variants = []
        colors = ["Red", "Blue", "Green", "Black", "White", "Yellow"]
        sizes = ["S", "M", "L", "XL"]
        sku_counter = 1
        for product in products:
            for _ in range(4):  # 4 variants per product
                variant = Variant.objects.create(
                    product=product,
                    sku=f"SKU{sku_counter}",
                    color=random.choice(colors),
                    size=random.choice(sizes),
                    created_at=random_date_last_year(),
                    updated_at=random_date_last_year()
                )
                sku_counter += 1
                variants.append(variant)
                self.stdout.write(f"Created Variant: {variant.sku} | Product: {product.name} | Color: {variant.color} | Size: {variant.size}")

        # ---- PURCHASE INVOICES (Split variants per supplier by brand) ----
        self.stdout.write(self.style.WARNING("Creating PurchaseInvoices for suppliers with only their brands' variants..."))
        for supplier in suppliers:
            invoice = PurchaseInvoice.objects.create(
                title=f"Invoice for {supplier.name}",
                Supplier=supplier,
                status="done",  # So stock is available
                delivery_date=random_date_last_year().date(),
                delivery_time=random_date_last_year().time()
            )
            # Only variants of products whose brand belongs to this supplier
            supplier_variants = [v for v in variants if v.product.brand and v.product.brand.supplier == supplier]
            for variant in supplier_variants:
                quantity = random.randint(50, 100)
                PurchaseItem.objects.create(
                    invoice=invoice,
                    product_variant=variant,
                    quantity=quantity
                )
            invoice.update_total_price()
            self.stdout.write(f"Created PurchaseInvoice #{invoice.pk} for Supplier {supplier.name} with {len(supplier_variants)} variants")

        # ---- ORDERS ----
        orders = []
        for i in range(5000):
            user = random.choice(users)
            created_at = random_date_last_year()
            order = Order.objects.create(
                user=user,
                status="initial",  # All orders start as initial
                created_at=created_at,
                updated_at=created_at
            )
            orders.append(order)
            self.stdout.write(f"Created Order: {order.id} | User: {user.username} | Status: initial | Date: {created_at.date()}")

            # ---- ORDER ITEMS ----
            order_items_count = random.randint(1, 5)
            for _ in range(order_items_count):
                variant = random.choice(variants)
                quantity = random.randint(1, 5)
                discount = random.randint(0, 20)
                oi = OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=quantity,
                    discount_percent=discount,
                    created_at=random_date_last_year(),
                    updated_at=random_date_last_year()
                )
                self.stdout.write(f"  Created OrderItem: {oi.id} | Order: {order.id} | Variant: {variant.sku} | Qty: {quantity} | Discount: {discount}%")

        # ---- UPDATE ORDER STATUSES ----
        self.stdout.write(self.style.WARNING("Updating order statuses..."))
        random.shuffle(orders)
        total_orders = len(orders)
        done_count = int(total_orders * 0.9)  # 90% done
        cancel_count = total_orders - done_count  # remaining 10% cancel/rejected

        # Set 90% to done
        for order in orders[:done_count]:
            order.status = "done"
            order.save(update_fields=["status"])
        # Set remaining 10% to either cancel or rejected
        for order in orders[done_count:]:
            order.status = random.choice(["cancel", "rejected"])
            order.save(update_fields=["status"])

        self.stdout.write(self.style.SUCCESS("All test data generation completed!"))
