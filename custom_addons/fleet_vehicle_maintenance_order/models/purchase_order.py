from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    fleet_maintenance_order_id = fields.Many2one(
        "fleet.vehicle.maintenance.order",
        string="Orden de mantenimiento",
        index=True,
        ondelete="set null",
    )
    fleet_vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehiculo",
        related="fleet_maintenance_order_id.vehicle_id",
        store=True,
        readonly=True,
    )

    def action_open_fleet_maintenance_order(self):
        self.ensure_one()
        if not self.fleet_maintenance_order_id:
            return False
        return {
            "name": "Orden de mantenimiento",
            "type": "ir.actions.act_window",
            "res_model": "fleet.vehicle.maintenance.order",
            "view_mode": "form",
            "res_id": self.fleet_maintenance_order_id.id,
        }


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    fleet_maintenance_part_line_id = fields.Many2one(
        "fleet.vehicle.maintenance.part.line",
        string="Linea de repuesto",
        index=True,
        ondelete="set null",
    )
    fleet_maintenance_order_id = fields.Many2one(
        "fleet.vehicle.maintenance.order",
        string="Orden de mantenimiento",
        related="fleet_maintenance_part_line_id.order_id",
        store=True,
        readonly=True,
    )
    fleet_vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehiculo",
        related="fleet_maintenance_part_line_id.order_id.vehicle_id",
        store=True,
        readonly=True,
    )
