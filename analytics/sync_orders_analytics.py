from collections import defaultdict

# Django
from django.db import transaction
from django.db.models import Sum

# Third-party
import jdatetime

# App models
from orders.models import Order, OrderItem
from .models import (
    DimUser,
    DimProductBase,
    DimVariantOrder,
    DimDate,
    FactSales,
    FactAnalytics,
)

def sync_orders_analytics():
    unsynced_orders = list(
        Order.objects.filter(is_synced_analytics=False)
        .select_related('user')
        .prefetch_related('items__variant__product__brand__supplier', 'items__variant__product__category__parent__parent')
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
        # ----------------------
        # DimDate
        # ----------------------
        needed_dates = {o.created_at.date() for o in unsynced_orders}
        existing_dates = {d.full_date: d for d in DimDate.objects.filter(full_date__in=needed_dates)}
        missing_dates = needed_dates - existing_dates.keys()
        if missing_dates:
            new_dates = []
            for g_date in missing_dates:
                j = jdatetime.date.fromgregorian(date=g_date)
                new_dates.append(DimDate(
                    full_date=g_date,
                    jalali_date=f"{j.year}-{j.month:02d}-{j.day:02d}",
                    day_of_week=j.strftime("%A"),
                    month_name=j.strftime("%B"),
                    quarter=(1 if j.month <= 3 else 2 if j.month <= 6 else 3 if j.month <= 9 else 4),
                    is_holiday=(j.weekday() == 6)
                ))
            DimDate.objects.bulk_create(new_dates, ignore_conflicts=True)
            report["DimDate"]["created"] = len(missing_dates)
            existing_dates.update({d.full_date: d for d in DimDate.objects.filter(full_date__in=missing_dates)})
        report["DimDate"]["existing"] = len(existing_dates) - report["DimDate"]["created"]

        # ----------------------
        # DimUser
        # ----------------------
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

        # ----------------------
        # DimProductBase
        # ----------------------
        product_keys = set()
        products_to_create = []

        for o in unsynced_orders:
            for item in o.items.all():
                p = item.variant.product
                key = (p.id, p.is_exciting, p.free_shipping, p.has_gift, p.is_budget_friendly)
                if key not in product_keys:
                    supplier_name = p.brand.supplier.name if p.brand and p.brand.supplier else None
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
                        supplier=supplier_name,
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

        # ----------------------
        # DimVariantOrder
        # ----------------------
        variant_ids = [i.variant.id for o in unsynced_orders for i in o.items.all()]
        existing_variants = {v.variant_id: v for v in DimVariantOrder.objects.filter(variant_id__in=variant_ids)}
        variant_keys = set()
        variants_to_create = []
        variants_to_update = []

        for o in unsynced_orders:
            for item in o.items.all():
                v_obj = item.variant
                key = (v_obj.id, v_obj.sku, v_obj.product.id, v_obj.color, v_obj.size, item.quantity, item.unit_price, item.discount_percent)
                if key not in variant_keys:
                    total_price = item.quantity * item.unit_price
                    total_after_discount = total_price * (100 - item.discount_percent) // 100
                    if v_obj.id in existing_variants:
                        ev = existing_variants[v_obj.id]
                        if ev.total_price != total_price or ev.total_after_discount != total_after_discount:
                            ev.total_price = total_price
                            ev.total_after_discount = total_after_discount
                            variants_to_update.append(ev)
                    else:
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
        if variants_to_update:
            DimVariantOrder.objects.bulk_update(variants_to_update, ['total_price', 'total_after_discount'])
        report["DimVariantOrder"]["existing"] = len(variant_keys) - report["DimVariantOrder"]["created"]

        # ----------------------
        # FactSales
        # ----------------------
        facts_to_create = []
        m2m_relations = []

        for o in unsynced_orders:
            dim_date = existing_dates[o.created_at.date()]
            dim_user = existing_users[o.user.id]
            variant_objs = [existing_variants[i.variant.id] for i in o.items.all()]
            total_price = sum(i.quantity * i.unit_price for i in o.items.all())
            total_price_after_discount = sum((i.quantity * i.unit_price * (100 - i.discount_percent)) // 100 for i in o.items.all())

            fact = FactSales(
                order_id=o.id,
                status=o.status,
                date=dim_date,
                user=dim_user,
                total_price=total_price,
                total_price_after_discount=total_price_after_discount
            )
            facts_to_create.append(fact)
            for v in variant_objs:
                m2m_relations.append((o.id, v.id))

        created_facts = FactSales.objects.bulk_create(facts_to_create)

        m2m_objects = [
            FactSales.variants.through(factsales_id=f.id, dimvariantorder_id=v_id)
            for f in created_facts
            for order_id, v_id in m2m_relations if f.order_id == order_id
        ]
        if m2m_objects:
            FactSales.variants.through.objects.bulk_create(m2m_objects, ignore_conflicts=True)

        report["FactSales"]["created"] = len(created_facts)
        report["FactSales"]["existing"] = 0

        # Mark orders as synced
        Order.objects.filter(id__in=[o.id for o in unsynced_orders]).update(is_synced_analytics=True)

    return report

def verify_fact_sales_totals():
    total_fact_sales = FactSales.objects.aggregate(total=Sum('total_price_after_discount'))['total'] or 0
    total_order_items = OrderItem.objects.aggregate(total=Sum('total_after_discount'))['total'] or 0
    return total_fact_sales == total_order_items

def simple_analysis():
    try:
        sales = (
            FactSales.objects
            .filter(exclude_from_analytics=False)
            .select_related('date')
        )


        analytics_by_date = defaultdict(lambda: {
            "total_order_quantity": 0,
            "initial_order_quantity": 0,
            "process_order_quantity": 0,
            "sent_order_quantity": 0,
            "done_order_quantity": 0,
            "cancel_order_quantity": 0,
            "rejected_order_quantity": 0,
            "date": None,
            "sale_ids": []
        })

        for sale in sales:
            date_obj = sale.date
            status = sale.status.lower() if sale.status else "unknown"
            total_price_after_discount = sale.total_price_after_discount or 0

            entry = analytics_by_date[date_obj.id]
            entry["date"] = date_obj
            entry["total_order_quantity"] += total_price_after_discount

            if status == "initial":
                entry["initial_order_quantity"] += total_price_after_discount
            elif status == "process":
                entry["process_order_quantity"] += total_price_after_discount
            elif status == "sent":
                entry["sent_order_quantity"] += total_price_after_discount
            elif status == "done":
                entry["done_order_quantity"] += total_price_after_discount
            elif status == "cancel":
                entry["cancel_order_quantity"] += total_price_after_discount
            elif status == "rejected":
                entry["rejected_order_quantity"] += total_price_after_discount

            entry["sale_ids"].append(sale.id)

        with transaction.atomic():
            for data in analytics_by_date.values():

                fa, created = FactAnalytics.objects.get_or_create(
                    date=data["date"]
                )

                fa.total_order_quantity += data["total_order_quantity"]
                fa.initial_order_quantity += data["initial_order_quantity"]
                fa.process_order_quantity += data["process_order_quantity"]
                fa.sent_order_quantity += data["sent_order_quantity"]
                fa.done_order_quantity += data["done_order_quantity"]
                fa.cancel_order_quantity += data["cancel_order_quantity"]
                fa.rejected_order_quantity += data["rejected_order_quantity"]

                fa.save()

                FactSales.objects.filter(
                    id__in=data["sale_ids"]
                ).update(exclude_from_analytics=True)

        return

    except Exception as e:
        raise e

