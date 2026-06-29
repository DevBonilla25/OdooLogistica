from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    fleet_maintenance_order_id = fields.Many2one(
        "fleet.vehicle.maintenance.order",
        string="Orden de mantenimiento",
        index=True,
        ondelete="set null",
    )
    fleet_maintenance_part_line_id = fields.Many2one(
        "fleet.vehicle.maintenance.part.line",
        string="Linea de repuesto",
        index=True,
        ondelete="set null",
    )
    fleet_vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehiculo",
        index=True,
        ondelete="set null",
    )
