from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FleetFuelServiceMigrationWizard(models.TransientModel):
    _name = "fleet.fuel.service.migration.wizard"
    _description = "Migrar servicios historicos de combustible"

    service_type_id = fields.Many2one(
        "fleet.service.type",
        string="Tipo de servicio",
        required=True,
        domain=[("category", "=", "service")],
        default=lambda self: self.env["fleet.service.type"].search(
            [("name", "=ilike", "Combustible"), ("category", "=", "service")],
            limit=1,
        ),
    )
    pending_count = fields.Integer(
        string="Servicios pendientes",
        compute="_compute_pending_count",
    )

    def _candidate_services(self):
        self.ensure_one()
        if not self.service_type_id:
            return self.env["fleet.vehicle.log.services"]
        fuel_logs = self.env["fleet.vehicle.log.fuel"].with_context(
            active_test=False
        ).search(
            [
                "|",
                ("legacy_service_id", "!=", False),
                ("service_id", "!=", False),
            ]
        )
        migrated_ids = set(fuel_logs.mapped("legacy_service_id").ids)
        migrated_ids.update(fuel_logs.mapped("service_id").ids)
        domain = [
            ("service_type_id", "=", self.service_type_id.id),
            ("active", "=", True),
        ]
        if migrated_ids:
            domain.append(("id", "not in", migrated_ids))
        return self.env["fleet.vehicle.log.services"].search(domain)

    @api.depends("service_type_id")
    def _compute_pending_count(self):
        for wizard in self:
            wizard.pending_count = len(wizard._candidate_services())

    def action_migrate(self):
        self.ensure_one()
        if not self.env.user.has_group("fleet.fleet_group_manager"):
            raise UserError(_("Solo un responsable de Flota puede migrar servicios."))
        services = self._candidate_services()
        if not services:
            raise UserError(_("No existen servicios pendientes para este tipo."))

        fuel_logs = self.env["fleet.vehicle.log.fuel"]
        created_logs = fuel_logs
        for service in services:
            values = {
                "vehicle_id": service.vehicle_id.id,
                "date": service.date,
                "service_type_id": service.service_type_id.id,
                "vendor_id": service.vendor_id.id,
                "inv_ref": service.inv_ref,
                "description": service.description,
                "notes": service.notes,
                "legacy_service_id": service.id,
                "legacy_total_cost": service.amount,
                "amount": 0.0,
                "approval_state": "draft",
                "state": "todo",
            }
            if service.odometer > 0:
                values["odometer"] = service.odometer
            created_logs |= fuel_logs.create(values)

        action = self.env["ir.actions.actions"]._for_xml_id(
            "fleet_vehicle_log_fuel.fleet_vehicle_log_fuel_action"
        )
        action["domain"] = [("id", "in", created_logs.ids)]
        action["context"] = {"search_default_migration_pending": 1}
        return action
