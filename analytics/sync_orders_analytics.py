from orders.models import Order, OrderItem
from .models import DimUser, DimProductBase, DimVariantOrder, DimDate, FactSales
from django.db import transaction
from django.db.models import Sum


def sync_orders_analytics():
    unsynced_orders = list(
        Order.objects.filter(is_synced_analytics=False, status="completed")
        .select_related('user')
        .prefetch_related('items__variant__product')
    )

    if not unsynced_orders:
        return {
            "DimDate": {"created": 0, "existing": 0},
            "DimUser": {"created": 0, "existing": 0},
            "DimProductBase": {"created": 0, "existing": 0},
            "DimVariantOrder": {"created": 0, "existing": 0},
            "FactSales": {"created": 0, "existing": 0},
        }

    report = {
        "DimDate": {"created": 0, "existing": 0},
        "DimUser": {"created": 0, "existing": 0},
        "DimProductBase": {"created": 0, "existing": 0},
        "DimVariantOrder": {"created": 0, "existing": 0},
        "FactSales": {"created": 0, "existing": 0},
    }

    with transaction.atomic():
        # ------------------- DimDate -------------------
        needed_dates = {o.updated_at.date() for o in unsynced_orders}
        existing_dates = {d.full_date: d for d in DimDate.objects.filter(full_date__in=needed_dates)}
        missing_dates = needed_dates - existing_dates.keys()
        if missing_dates:
            DimDate.objects.bulk_create([DimDate(full_date=d) for d in missing_dates], ignore_conflicts=True)
            report["DimDate"]["created"] = len(missing_dates)
            existing_dates.update({d.full_date: d for d in DimDate.objects.filter(full_date__in=missing_dates)})
        report["DimDate"]["existing"] = len(existing_dates) - report["DimDate"]["created"]

        # ------------------- DimUser -------------------
        needed_user_ids = {o.user.id for o in unsynced_orders}
        existing_users = {u.user_id: u for u in DimUser.objects.filter(user_id__in=needed_user_ids)}
        missing_user_ids = needed_user_ids - existing_users.keys()
        if missing_user_ids:
            users_to_create = [o.user for o in unsynced_orders if o.user.id in missing_user_ids]
            DimUser.objects.bulk_create([
                DimUser(
                    user_id=u.id,
                    username=u.username,
                    gender=u.gender,
                    city=u.city,
                    registration_date=u.registration_date,
                    age_range=u.age_range.name if u.age_range else None
                )
                for u in users_to_create
            ], ignore_conflicts=True)
            report["DimUser"]["created"] = len(users_to_create)
            existing_users.update({u.user_id: u for u in DimUser.objects.filter(user_id__in=missing_user_ids)})
        report["DimUser"]["existing"] = len(existing_users) - report["DimUser"]["created"]

        # ------------------- DimProductBase -------------------
        product_keys = set()
        products_to_create = []
        for o in unsynced_orders:
            for item in o.items.all():
                p = item.variant.product
                key = (p.id, p.is_exciting, p.free_shipping, p.has_gift, p.is_budget_friendly)
                if key not in product_keys:
                    products_to_create.append(DimProductBase(
                        product_id=p.id,
                        name=p.name,
                        rating=p.rating,
                        expire_date=p.expire_date,
                        is_available=p.is_available,
                        is_exciting=p.is_exciting,
                        free_shipping=p.free_shipping,
                        has_gift=p.has_gift,
                        is_budget_friendly=p.is_budget_friendly,
                        price=p.price,
                        brand=p.brand.name if p.brand else None,
                        category_level_1=p.category.name if p.category else None,
                        category_level_2=p.category.parent.name if p.category and p.category.parent else None,
                        category_level_3=p.category.parent.parent.name if p.category and p.category.parent and p.category.parent.parent else None,
                        created_at=p.created_at,
                        updated_at=p.updated_at
                    ))
                    product_keys.add(key)
        if products_to_create:
            DimProductBase.objects.bulk_create(products_to_create, ignore_conflicts=True)
            report["DimProductBase"]["created"] = len(products_to_create)
        report["DimProductBase"]["existing"] = len(product_keys) - report["DimProductBase"]["created"]

        # ------------------- DimVariantOrder -------------------
        variant_ids = [i.variant.id for o in unsynced_orders for i in o.items.all()]
        existing_variants = {v.variant_id: v for v in DimVariantOrder.objects.filter(variant_id__in=variant_ids)}

        variant_keys = set()
        variants_to_create = []
        for o in unsynced_orders:
            for item in o.items.all():
                v_obj = item.variant
                key = (v_obj.id, v_obj.sku, v_obj.product.id, v_obj.color, v_obj.size, item.quantity, item.unit_price, item.discount_percent)
                if key not in variant_keys:
                    if v_obj.id not in existing_variants:
                        total_price = item.quantity * item.unit_price
                        total_after_discount = total_price * (100 - item.discount_percent) // 100
                        variants_to_create.append(DimVariantOrder(
                            variant_id=v_obj.id,
                            variant_sku=v_obj.sku,
                            product_id=v_obj.product.id,
                            color=v_obj.color,
                            size=v_obj.size,
                            created_at=v_obj.created_at,
                            updated_at=v_obj.updated_at,
                            quantity=item.quantity,
                            unit_price=item.unit_price,
                            discount_percent=item.discount_percent,
                            total_price=total_price,
                            total_after_discount=total_after_discount
                        ))
                    variant_keys.add(key)
        if variants_to_create:
            DimVariantOrder.objects.bulk_create(variants_to_create, ignore_conflicts=True)
            existing_variants.update({v.variant_id: v for v in DimVariantOrder.objects.filter(variant_id__in=[v.variant_id for v in variants_to_create])})
            report["DimVariantOrder"]["created"] = len(variants_to_create)
        report["DimVariantOrder"]["existing"] = len(variant_keys) - report["DimVariantOrder"]["created"]

        # ------------------- FactSales -------------------
        fact_sales_created = 0
        for o in unsynced_orders:
            dim_date = existing_dates[o.updated_at.date()]
            dim_user = existing_users[o.user.id]

            variant_objs = [existing_variants[i.variant.id] for i in o.items.all()]
            total_price = sum(i.quantity * i.unit_price for i in o.items.all())
            total_price_after_discount = sum((i.quantity * i.unit_price * (100 - i.discount_percent)) // 100 for i in o.items.all())

            # Update DimVariantOrder totals
            for item in o.items.all():
                v = existing_variants[item.variant.id]
                updated_total_price = item.quantity * item.unit_price
                updated_total_after_discount = (updated_total_price * (100 - item.discount_percent)) // 100
                if v.total_price != updated_total_price or v.total_after_discount != updated_total_after_discount:
                    v.total_price = updated_total_price
                    v.total_after_discount = updated_total_after_discount
                    v.save(update_fields=['total_price', 'total_after_discount'])

            # Create FactSales **for every order** without skipping
            fact = FactSales.objects.create(
                date=dim_date,
                user=dim_user,
                total_price=total_price,
                total_price_after_discount=total_price_after_discount
            )
            fact.variants.add(*[v.id for v in variant_objs])
            fact_sales_created += 1

        report["FactSales"]["created"] = fact_sales_created

        # ------------------- Mark orders as synced -------------------
        Order.objects.filter(id__in=[o.id for o in unsynced_orders]).update(is_synced_analytics=True)

    return report


def verify_fact_sales_totals():
    total_fact_sales = FactSales.objects.aggregate(total=Sum('total_price_after_discount'))['total'] or 0
    total_order_items = OrderItem.objects.filter(order__status='completed').aggregate(total=Sum('total_after_discount'))['total'] or 0
    return total_fact_sales == total_order_items
