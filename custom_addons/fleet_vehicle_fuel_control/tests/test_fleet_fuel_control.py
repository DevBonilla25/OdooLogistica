from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFleetFuelControl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "model_id": cls.env["fleet.vehicle.model"].search([], limit=1).id,
                "license_plate": "FUEL-TEST",
            }
        )
        cls.fleet_user = cls.env["res.users"].create(
            {
                "name": "Fuel Test User",
                "login": "fuel_test_user",
                "group_ids": [(6, 0, [cls.env.ref("fleet.fleet_group_user").id])],
            }
        )
        cls.vehicle.driver_id = cls.fleet_user.partner_id

    def _create_log(self, **values):
        data = {
            "vehicle_id": self.vehicle.id,
            "date": "2026-01-01",
            "gallons": 10.0,
            "price_per_gallon": 2.5,
            "current_odometer": 1000.0,
        }
        data.update(values)
        return self.env["fleet.vehicle.log.fuel"].create(data)

    def test_metrics_and_compatibility_fields(self):
        log = self._create_log()
        self.assertEqual(log.liter, 10.0)
        self.assertEqual(log.price_per_liter, 2.5)
        self.assertEqual(log.fuel_subtotal, 25.0)
        self.assertEqual(log.fuel_tax_amount, 3.75)
        self.assertEqual(log.amount, 28.75)
        self.assertEqual(log.fuel_total_cost, 28.75)
        self.assertEqual(log.distance_km, 0.0)
        self.assertEqual(log.km_per_gallon, 0.0)
        self.assertEqual(log.cost_per_km, 0.0)

    def test_decimal_precision_and_monetary_rounding(self):
        log = self._create_log(
            gallons=10.123,
            price_per_gallon=2.456789,
        )

        self.assertEqual(log.gallons, 10.123)
        self.assertEqual(log.price_per_gallon, 2.456789)
        self.assertEqual(log.fuel_subtotal, 24.87)
        self.assertEqual(log.fuel_tax_amount, 3.73)
        self.assertEqual(log.fuel_total_cost, 28.60)
        self.assertEqual(log.amount, 28.60)
    def test_onchange_updates_costs_before_saving(self):
        log = self.env["fleet.vehicle.log.fuel"].new(
            {
                "vehicle_id": self.vehicle.id,
                "gallons": 8.0,
                "price_per_gallon": 3.0,
                "current_odometer": 1000.0,
            }
        )
        log._onchange_gallon_values()

        self.assertEqual(log.fuel_subtotal, 24.0)
        self.assertEqual(log.fuel_tax_amount, 3.6)
        self.assertEqual(log.fuel_total_cost, 27.6)
        self.assertEqual(log.amount, 27.6)
    def test_selecting_vehicle_keeps_costs_in_form(self):
        fuel_form = Form(self.env["fleet.vehicle.log.fuel"])
        fuel_form.gallons = 8.0
        fuel_form.price_per_gallon = 3.0
        self.assertEqual(fuel_form.fuel_total_cost, 27.6)

        fuel_form.vehicle_id = self.vehicle

        self.assertEqual(fuel_form.gallons, 8.0)
        self.assertEqual(fuel_form.price_per_gallon, 3.0)
        self.assertEqual(fuel_form.fuel_subtotal, 24.0)
        self.assertEqual(fuel_form.fuel_tax_amount, 3.6)
        self.assertEqual(fuel_form.fuel_total_cost, 27.6)
    def test_previous_odometer_from_approved_log(self):
        previous = self._create_log()
        previous.action_submit_review()
        previous.action_approve()
        current = self._create_log(
            date="2026-02-01",
            current_odometer=1250.0,
        )
        self.assertEqual(current.previous_odometer, 1000.0)
        self.assertEqual(current.distance_km, 250.0)

    def test_approval_keeps_same_day_logs_in_creation_order(self):
        previous = self._create_log(current_odometer=1000.0)
        previous.action_submit_review()
        previous.action_approve()
        current = self._create_log(current_odometer=1010.0)
        current.action_submit_review()
        current.action_approve()

        self.assertEqual(previous.previous_odometer, 0.0)
        self.assertEqual(current.previous_odometer, 1000.0)
        self.assertEqual(current.distance_km, 10.0)
        self.assertEqual(current.cost_per_km, 2.875)

    def test_validation_and_approval_security(self):
        with self.assertRaises(ValidationError):
            self._create_log(gallons=0.0)

        log = self._create_log()
        user_log = log.with_user(self.fleet_user)
        user_log.action_submit_review()
        self.assertEqual(log.approval_state, "pending_review")
        with self.assertRaises(AccessError):
            user_log.action_approve()
        with self.assertRaises(AccessError):
            user_log.write({"gallons": 12.0})

    def test_migrate_service_without_duplicating_cost(self):
        service_type = self.env["fleet.service.type"].create(
            {"name": "Legacy Fuel Test", "category": "service"}
        )
        service = self.env["fleet.vehicle.log.services"].create(
            {
                "vehicle_id": self.vehicle.id,
                "service_type_id": service_type.id,
                "date": "2025-12-01",
                "amount": 115.0,
                "odometer": 900.0,
                "state": "done",
            }
        )
        wizard = self.env["fleet.fuel.service.migration.wizard"].create(
            {"service_type_id": service_type.id}
        )
        self.assertEqual(wizard.pending_count, 1)
        wizard.action_migrate()

        log = self.env["fleet.vehicle.log.fuel"].search(
            [("legacy_service_id", "=", service.id)]
        )
        self.assertEqual(len(log), 1)
        self.assertTrue(service.active)
        self.assertEqual(log.approval_state, "draft")
        self.assertEqual(log.amount, 0.0)
        self.assertEqual(log.legacy_total_cost, 115.0)
        self.assertEqual(log.fuel_total_cost, 115.0)
        self.assertTrue(log.migration_pending)
        second_wizard = self.env["fleet.fuel.service.migration.wizard"].create(
            {"service_type_id": service_type.id}
        )
        self.assertEqual(second_wizard.pending_count, 0)

        with self.assertRaises(ValidationError):
            log.action_submit_review()

        log.write({"gallons": 10.0, "price_per_gallon": 10.0})
        self.assertEqual(log.amount, 0.0)
        self.assertEqual(log.fuel_total_cost, 115.0)
        log.action_submit_review()
        log.action_approve()

        self.assertFalse(service.active)
        self.assertEqual(log.amount, 115.0)
        self.assertFalse(log.migration_pending)
        service_count = self.env["fleet.vehicle.log.services"].with_context(
            active_test=False
        ).search_count([])
        log.button_running()
        log.button_done()
        self.assertEqual(log.service_id, service)
        self.assertEqual(service.amount, 115.0)
        self.assertFalse(service.active)
        self.assertEqual(
            self.env["fleet.vehicle.log.services"].with_context(
                active_test=False
            ).search_count([]),
            service_count,
        )

    def test_migration_excludes_service_already_created_by_fuel_log(self):
        service_type = self.env["fleet.service.type"].create(
            {"name": "Linked Fuel Test", "category": "service"}
        )
        log = self._create_log(service_type_id=service_type.id)
        log.action_submit_review()
        log.action_approve()
        log.button_running()
        log.button_done()

        wizard = self.env["fleet.fuel.service.migration.wizard"].create(
            {"service_type_id": service_type.id}
        )

        self.assertTrue(log.service_id)
        self.assertEqual(wizard.pending_count, 0)
        self.assertNotIn(log.service_id, wizard._candidate_services())
    def test_deleting_migrated_draft_restores_service(self):
        service_type = self.env["fleet.service.type"].create(
            {"name": "Legacy Fuel Delete Test", "category": "service"}
        )
        service = self.env["fleet.vehicle.log.services"].create(
            {
                "vehicle_id": self.vehicle.id,
                "service_type_id": service_type.id,
                "date": "2025-11-01",
                "amount": 50.0,
                "odometer": 800.0,
            }
        )
        wizard = self.env["fleet.fuel.service.migration.wizard"].create(
            {"service_type_id": service_type.id}
        )
        wizard.action_migrate()
        log = self.env["fleet.vehicle.log.fuel"].search(
            [("legacy_service_id", "=", service.id)]
        )
        log.unlink()
        self.assertTrue(service.active)
    def test_operational_flow_requires_approval(self):
        log = self._create_log()
        with self.assertRaises(UserError):
            log.button_running()
        log.action_submit_review()
        log.action_approve()
        log.button_running()
        self.assertEqual(log.state, "running")
        log.button_done()
        self.assertEqual(log.state, "done")
        self.assertTrue(log.service_id)
        self.assertEqual(log.service_id.amount, log.fuel_total_cost)
