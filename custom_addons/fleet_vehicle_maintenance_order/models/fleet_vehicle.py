from odoo import fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    maintenance_order_ids = fields.One2many(
        "fleet.vehicle.maintenance.order",
        "vehicle_id",
        string="Ordenes de mantenimiento",
    )
    maintenance_order_count = fields.Integer(
        string="Ordenes de mantenimiento",
        compute="_compute_maintenance_order_count",
    )

    def _compute_maintenance_order_count(self):
        order_data = self.env["fleet.vehicle.maintenance.order"]._read_group(
            [("vehicle_id", "in", self.ids)],
            ["vehicle_id"],
            ["__count"],
        )
        mapped_data = {vehicle.id: count for vehicle, count in order_data}
        for vehicle in self:
            vehicle.maintenance_order_count = mapped_data.get(vehicle.id, 0)

    def action_open_maintenance_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "fleet_vehicle_maintenance_order.action_fleet_vehicle_maintenance_order"
        )
        action.update(
            {
                "domain": [("vehicle_id", "=", self.id)],
                "context": {
                    "default_vehicle_id": self.id,
                    "default_reporter_id": self.driver_id.id,
                },
            }
        )
        return action
