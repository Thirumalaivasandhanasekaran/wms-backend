from decimal import Decimal

from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.inventory.models import StockMovement
from apps.masters import models as m
from apps.reports.services import REPORTS
from apps.sales.models import Payment, Sale


class WMSFlowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("init_wms", username="admin", password="Str0ng-Pass-123")
        call_command("init_wms", demo=True)
        cls.cashier_role = Role.objects.get(name="Cashier")

    def setUp(self):
        self.login("admin", "Str0ng-Pass-123")

    def login(self, username, password):
        res = self.client.post("/api/auth/login/", {"username": username, "password": password}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    def make_variant(self, opening=0, price="500.00"):
        product = self.client.post("/api/products/", {
            "product_code": "TS", "name": "Men T-Shirt", "category": m.Category.objects.first().id,
            "unit": m.Unit.objects.get(name="Piece").id, "minimum_stock": 3}, format="json")
        self.assertEqual(product.status_code, 201, product.content)
        res = self.client.post("/api/variants/", {
            "product": product.data["id"], "size": m.Size.objects.get(name="M").id, "colour": m.Colour.objects.get(name="Black").id,
            "purchase_price": "300.00", "selling_price": price, "opening_stock": opening,
            "warehouse": m.Warehouse.objects.first().id}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        return res.data

    def stock(self, variant_id):
        return m.ProductVariant.objects.get(pk=variant_id).current_stock

    def test_login_returns_user_and_permissions(self):
        data = self.login("admin", "Str0ng-Pass-123")
        self.assertTrue(data["user"]["full_access"])
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

    def test_variant_autogenerates_sku_and_unique_barcode(self):
        v = self.make_variant()
        self.assertEqual(v["sku"], "TS-M-BLACK")
        self.assertEqual(len(v["barcode"]), 13)
        found = self.client.get("/api/variants/by-barcode/", {"code": v["barcode"]})
        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.data["id"], v["id"])
        self.assertEqual(self.client.get("/api/variants/by-barcode/", {"code": "nope"}).status_code, 404)

    def test_critical_stock_flow(self):
        v = self.make_variant(opening=0)
        vid, wh = v["id"], m.Warehouse.objects.first().id
        sup = m.Supplier.objects.first().id

        r = self.client.post("/api/stock-in/", {"supplier": sup, "warehouse": wh, "items": [{"variant": vid, "quantity": 10, "purchase_price": "310.00"}]}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(r.data["document_no"].startswith("SI-"))
        self.assertEqual(self.stock(vid), 10)

        r = self.client.post("/api/stock-adjustments/", {"warehouse": wh, "adjustment_type": "INCREASE", "reason": "Found", "items": [{"variant": vid, "quantity": 5}]}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.stock(vid), 15)

        r = self.client.post("/api/stock-adjustments/", {"warehouse": wh, "adjustment_type": "DECREASE", "reason": "Damaged", "items": [{"variant": vid, "quantity": 3}]}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.stock(vid), 12)

        sale = self.client.post("/api/sales/", {"items": [{"variant": vid, "quantity": 2}], "payments": [{"method": "CASH", "amount": "1000.00"}]}, format="json")
        self.assertEqual(sale.status_code, 201, sale.content)
        self.assertEqual(self.stock(vid), 10)
        self.assertTrue(sale.data["invoice_no"].startswith("INV-"))
        self.assertEqual(Payment.objects.filter(sale_id=sale.data["id"]).count(), 1)

        item_id = sale.data["items"][0]["id"]
        ret = self.client.post("/api/sales-returns/", {"sale": sale.data["id"], "reason": "Wrong size", "refund_method": "CASH", "items": [{"sale_item": item_id, "quantity": 1}]}, format="json")
        self.assertEqual(ret.status_code, 201, ret.content)
        self.assertEqual(self.stock(vid), 11)
        self.assertEqual(Decimal(ret.data["refund_total"]), Decimal("500.00"))

        r = self.client.post("/api/stock-out/", {"warehouse": wh, "reason": "DAMAGED", "items": [{"variant": vid, "quantity": 20}]}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Insufficient stock", str(r.data))
        self.assertEqual(self.stock(vid), 11)

        types = list(StockMovement.objects.filter(variant_id=vid).order_by("id").values_list("movement_type", flat=True))
        self.assertEqual(types, ["STOCK_IN", "ADJUSTMENT_IN", "ADJUSTMENT_OUT", "SALE", "SALE_RETURN"])

    def test_return_cannot_exceed_sold_quantity(self):
        v = self.make_variant(opening=5)
        sale = self.client.post("/api/sales/", {"items": [{"variant": v["id"], "quantity": 2}], "payments": [{"method": "UPI", "amount": "1000.00"}]}, format="json").data
        body = {"sale": sale["id"], "reason": "x", "refund_method": "CASH", "items": [{"sale_item": sale["items"][0]["id"], "quantity": 3}]}
        self.assertEqual(self.client.post("/api/sales-returns/", body, format="json").status_code, 400)
        self.assertEqual(self.stock(v["id"]), 3)

    def test_sale_rejects_insufficient_stock_and_rolls_back(self):
        a, b = self.make_variant(opening=5), None
        p2 = self.client.post("/api/products/", {"product_code": "JN", "name": "Jeans", "category": m.Category.objects.first().id, "unit": m.Unit.objects.first().id}, format="json").data
        b = self.client.post("/api/variants/", {"product": p2["id"], "selling_price": "800.00", "opening_stock": 1}, format="json").data
        body = {"items": [{"variant": a["id"], "quantity": 2}, {"variant": b["id"], "quantity": 6}], "payments": [{"method": "CASH", "amount": "5800.00"}]}
        r = self.client.post("/api/sales/", body, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Insufficient stock", str(r.data))
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(self.stock(a["id"]), 5)  # first line's reduction was rolled back
        self.assertEqual(StockMovement.objects.filter(movement_type="SALE").count(), 0)

    def test_payment_must_match_total_and_server_price_is_used(self):
        v = self.make_variant(opening=5, price="500.00")
        r = self.client.post("/api/sales/", {"items": [{"variant": v["id"], "quantity": 1, "unit_price": "1.00"}], "payments": [{"method": "CASH", "amount": "1.00"}]}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.stock(v["id"]), 5)

    def test_tax_and_discount(self):
        self.client.put("/api/settings/invoice/", {"tax_percent": "10.00"}, format="json")
        v = self.make_variant(opening=5, price="500.00")
        r = self.client.post("/api/sales/", {"items": [{"variant": v["id"], "quantity": 2, "discount": "100.00"}], "payments": [{"method": "CARD", "amount": "990.00"}]}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Decimal(r.data["grand_total"]), Decimal("990.00"))
        self.assertEqual(Decimal(r.data["tax_total"]), Decimal("90.00"))

    def test_stock_out_and_negative_adjustment_blocked(self):
        v = self.make_variant(opening=2)
        wh = m.Warehouse.objects.first().id
        r = self.client.post("/api/stock-adjustments/", {"warehouse": wh, "adjustment_type": "DECREASE", "reason": "x", "items": [{"variant": v["id"], "quantity": 3}]}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/stock-out/", {"warehouse": wh, "reason": "LOST", "items": [{"variant": v["id"], "quantity": 2}]}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.stock(v["id"]), 0)

    def test_stock_documents_are_append_only(self):
        self.assertEqual(self.client.delete("/api/stock-in/1/").status_code, 405)
        self.assertEqual(self.client.put("/api/sales/1/", {}, format="json").status_code, 405)

    def test_cashier_permissions_enforced(self):
        User.objects.create_user("cash", password="Cashier-Pass-1", role=self.cashier_role)
        self.login("cash", "Cashier-Pass-1")
        self.assertEqual(self.client.get("/api/warehouses/").status_code, 200)
        denied = self.client.post("/api/warehouses/", {"name": "X"}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(self.client.get("/api/users/").status_code, 403)
        self.assertEqual(self.client.post("/api/stock-in/", {}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/warehouses/export/").status_code, 403)
        self.assertEqual(self.client.get("/api/settings/public/").status_code, 200)
        self.assertEqual(self.client.get("/api/settings/backup/").status_code, 403)

    def test_unauthenticated_blocked(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/warehouses/").status_code, 401)

    def test_master_crud_search_filter_pagination_export(self):
        for i in range(7):
            r = self.client.post("/api/warehouses/", {"name": f"WH {i}", "location": "Salem" if i % 2 else "Chennai"}, format="json")
            self.assertEqual(r.status_code, 201)
        res = self.client.get("/api/warehouses/")
        self.assertEqual(len(res.data["results"]), 5)
        self.assertEqual(res.data["count"], 8)  # 7 + demo warehouse
        self.assertEqual(self.client.get("/api/warehouses/", {"search": "salem"}).data["count"], 3)
        self.assertEqual(self.client.get("/api/warehouses/", {"status": "INACTIVE"}).data["count"], 0)
        self.assertEqual(len(self.client.get("/api/warehouses/", {"page_size": 20}).data["results"]), 8)
        csv_res = self.client.get("/api/warehouses/export/", {"search": "salem"})
        self.assertEqual(csv_res.status_code, 200)
        self.assertEqual(len(csv_res.content.decode().strip().splitlines()), 4)
        wid = res.data["results"][0]["id"]
        self.assertEqual(self.client.patch(f"/api/warehouses/{wid}/", {"status": "INACTIVE"}, format="json").status_code, 200)

    def test_location_hierarchy_validated(self):
        wh2 = self.client.post("/api/warehouses/", {"name": "Other"}, format="json").data["id"]
        zone = m.Zone.objects.first()
        r = self.client.post("/api/racks/", {"warehouse": wh2, "zone": zone.id, "name": "R", "code": "R9"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_delete_in_use_is_blocked_with_message(self):
        self.make_variant()
        r = self.client.delete(f"/api/categories/{m.Category.objects.first().id}/")
        self.assertEqual(r.status_code, 409)
        self.assertIn("in use", r.data["detail"])

    def test_duplicate_variant_and_barcode_rejected(self):
        v = self.make_variant()
        dup = self.client.post("/api/variants/", {"product": v["product"], "size": v["size"], "colour": v["colour"]}, format="json")
        self.assertEqual(dup.status_code, 400)

    def test_stock_status_rules(self):
        v = self.make_variant(opening=0)
        self.assertEqual(self.client.get("/api/variants/", {"stock_status": "OUT"}).data["count"], 1)
        wh = m.Warehouse.objects.first().id
        self.client.post("/api/stock-adjustments/", {"warehouse": wh, "adjustment_type": "INCREASE", "reason": "x", "items": [{"variant": v["id"], "quantity": 3}]}, format="json")
        self.assertEqual(self.client.get("/api/variants/", {"stock_status": "LOW"}).data["count"], 1)  # min stock is 3
        self.client.post("/api/stock-adjustments/", {"warehouse": wh, "adjustment_type": "INCREASE", "reason": "x", "items": [{"variant": v["id"], "quantity": 1}]}, format="json")
        self.assertEqual(self.client.get("/api/variants/", {"stock_status": "IN"}).data["count"], 1)

    def test_all_reports_and_dashboard(self):
        v = self.make_variant(opening=10)
        sale = self.client.post("/api/sales/", {"items": [{"variant": v["id"], "quantity": 2}], "payments": [{"method": "CASH", "amount": "1000.00"}]}, format="json").data
        self.client.post("/api/sales-returns/", {"sale": sale["id"], "reason": "r", "refund_method": "CASH", "items": [{"sale_item": sale["items"][0]["id"], "quantity": 1}]}, format="json")
        for name in REPORTS:
            res = self.client.get(f"/api/reports/{name}/")
            self.assertEqual(res.status_code, 200, f"{name}: {res.content[:300]}")
            self.assertIn("columns", res.data)
            csv_res = self.client.get(f"/api/reports/{name}/", {"export": "csv"})
            self.assertEqual(csv_res.status_code, 200, name)
        profit = self.client.get("/api/reports/profit/").data["summary"]
        # sold 2 (1000), returned 1 (500) -> net 500; cost 300 -> profit 200
        self.assertEqual(Decimal(str(profit["gross_profit"])), Decimal("200.00"))
        pay = self.client.get("/api/reports/payments/").data["results"][0]
        self.assertEqual((pay["method"], pay["invoice_count"]), ("CASH", 1))
        cards = self.client.get("/api/reports/dashboard/").data["cards"]
        self.assertEqual(cards["todays_orders"], 1)
        self.assertEqual(cards["todays_sales"], 2)
        self.assertEqual(Decimal(str(cards["todays_revenue"])), Decimal("1000.00"))
        self.assertEqual(cards["total_current_stock"], 9)
        self.assertEqual(Decimal(str(cards["todays_profit"])), Decimal("200.00"))
        self.assertEqual(self.client.get("/api/reports/unknown/").status_code, 404)
        filtered = self.client.get("/api/reports/current-stock/", {"status": "OUT"})
        self.assertEqual(filtered.data["count"], 0)

    def test_roles_permissions_and_users_api(self):
        roles = self.client.get("/api/roles/").data["results"]
        self.assertEqual({r["name"] for r in roles}, {"Admin / Owner", "Cashier", "Stock Staff"})
        perms = self.client.get("/api/permissions/").data
        self.assertEqual(len(perms["modules"]), 25)
        cashier = next(r for r in roles if r["name"] == "Cashier")
        view_ids = [p["id"] for p in perms["permissions"] if p["action"] == "VIEW"]
        self.assertEqual(self.client.put(f"/api/roles/{cashier['id']}/permissions/", {"permission_ids": view_ids}, format="json").status_code, 200)
        u = self.client.post("/api/users/", {"username": "stock1", "password": "Stock-Pass-123", "role": cashier["id"], "full_name": "S One"}, format="json")
        self.assertEqual(u.status_code, 201, u.content)
        self.assertNotIn("password", u.data)
        self.assertEqual(self.client.post("/api/users/", {"username": "nopass"}, format="json").status_code, 400)
        admin_role = next(r for r in roles if r["full_access"])
        self.assertEqual(self.client.delete(f"/api/roles/{admin_role['id']}/").status_code, 400)

    def test_settings_and_backup(self):
        self.assertEqual(self.client.put("/api/settings/business/", {"shop_name": "Kumar Stores", "gstin": "33AAAAA0000A1Z5"}, format="json").data["shop_name"], "Kumar Stores")
        self.assertEqual(self.client.put("/api/settings/hardware/", {"thermal_printer_enabled": True}, format="json").status_code, 200)
        self.assertTrue(self.client.get("/api/settings/public/").data["hardware"]["thermal_printer_enabled"])
        res = self.client.get("/api/settings/backup/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("attachment", res["Content-Disposition"])
