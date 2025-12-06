from django.core.management.base import BaseCommand
from faker import Faker
import random
from suppliers.models import Supplier
from products.models import Brand

fake = Faker()

class Command(BaseCommand):
    help = "Creates 20 suppliers and assigns them randomly to brands"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting supplier creation..."))

        suppliers = []
        for i in range(20):
            supplier_name = fake.unique.company()
            supplier, _ = Supplier.objects.get_or_create(name=supplier_name)
            suppliers.append(supplier)
            self.stdout.write(f"Created Supplier: {supplier.name}")

        brands = list(Brand.objects.all())

        for brand in brands:
            supplier = random.choice(suppliers)
            brand.supplier = supplier
            brand.save()
            self.stdout.write(f"Assigned Brand: {brand.name} to Supplier: {supplier.name}")

        self.stdout.write(self.style.SUCCESS("Supplier creation and assignment completed!"))
