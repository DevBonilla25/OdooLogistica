from odoo import api, fields, models, tools


class FleetVehicleMaintenanceCostReport(models.Model):
    _name = "fleet.vehicle.maintenance.cost.report"
    _description = "Reporte unificado de costos de flota"
    _auto = False
    _rec_name = "component_name"
    _order = "request_date desc, order_id desc"

    request_date = fields.Datetime(string="Fecha", readonly=True)
    order_id = fields.Many2one(
        "fleet.vehicle.maintenance.order",
        string="Orden de mantenimiento",
        readonly=True,
    )
    vehicle_id = fields.Many2one("fleet.vehicle", string="Vehiculo", readonly=True)
    driver_id = fields.Many2one("res.partner", string="Conductor", readonly=True)
    system_id = fields.Many2one(
        "fleet.vehicle.system",
        string="Sistema afectado",
        readonly=True,
    )
    cost_type = fields.Selection(
        selection="_get_cost_types",
        string="Tipo de costo",
        readonly=True,
    )
    component_name = fields.Char(string="Concepto", readonly=True)
    product_id = fields.Many2one("product.product", string="Repuesto", readonly=True)
    technician_id = fields.Many2one(
        "res.partner",
        string="Tecnico / Proveedor",
        readonly=True,
    )
    quantity = fields.Float(string="Cantidad / Horas", readonly=True)
    cost = fields.Monetary(string="Costo", readonly=True, aggregator="sum")
    currency_id = fields.Many2one("res.currency", string="Moneda", readonly=True)
    company_id = fields.Many2one("res.company", string="Compania", readonly=True)
    state = fields.Selection(
        [
            ("reported", "Reportada"),
            ("diagnosis", "En diagnostico"),
            ("approval", "Pendiente de aprobacion"),
            ("approved", "Aprobada"),
            ("execution", "En ejecucion"),
            ("parts_pending", "Pendiente de repuestos"),
            ("finished", "Finalizada"),
            ("closed", "Cerrada"),
            ("cancelled", "Cancelada"),
        ],
        string="Estado de mantenimiento",
        readonly=True,
    )

    @api.model
    def _get_cost_types(self):
        standard_types = self.env["fleet.vehicle.cost.report"]._fields[
            "cost_type"
        ]._description_selection(self.env)
        return standard_types + [
            ("activity", "Actividad de mantenimiento"),
            ("part", "Repuesto"),
            ("labor", "Mano de obra"),
        ]

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH maintenance_cost_lines AS (
                    SELECT
                        activity.order_id,
                        'activity'::varchar AS cost_type,
                        activity.name AS component_name,
                        NULL::integer AS product_id,
                        NULL::integer AS technician_id,
                        1.0::numeric AS quantity,
                        activity.estimated_cost AS cost
                    FROM fleet_vehicle_maintenance_activity_line activity

                    UNION ALL

                    SELECT
                        part.order_id,
                        'part'::varchar AS cost_type,
                        part.name AS component_name,
                        part.product_id,
                        NULL::integer AS technician_id,
                        CASE
                            WHEN part.source = 'purchase' THEN part.purchase_qty
                            ELSE part.quantity
                        END AS quantity,
                        part.subtotal AS cost
                    FROM fleet_vehicle_maintenance_part_line part

                    UNION ALL

                    SELECT
                        labor.order_id,
                        'labor'::varchar AS cost_type,
                        labor.name AS component_name,
                        NULL::integer AS product_id,
                        labor.technician_id,
                        labor.hours AS quantity,
                        labor.subtotal AS cost
                    FROM fleet_vehicle_maintenance_labor_line labor
                ),
                system_counts AS (
                    SELECT
                        relation.order_id,
                        COUNT(*) AS system_count
                    FROM fleet_vehicle_maintenance_order_system_rel relation
                    GROUP BY relation.order_id
                ),
                unified_costs AS (
                    SELECT
                        standard_cost.date_start::timestamp AS request_date,
                        NULL::integer AS order_id,
                        standard_cost.vehicle_id,
                        standard_cost.driver_id,
                        NULL::integer AS system_id,
                        standard_cost.cost_type,
                        standard_cost.name AS component_name,
                        NULL::integer AS product_id,
                        NULL::integer AS technician_id,
                        1.0::numeric AS quantity,
                        standard_cost.cost,
                        company.currency_id,
                        standard_cost.company_id,
                        NULL::varchar AS state
                    FROM fleet_vehicle_cost_report standard_cost
                    JOIN res_company company
                        ON company.id = standard_cost.company_id

                    UNION ALL

                    SELECT
                        maintenance_order.request_date,
                        maintenance_order.id AS order_id,
                        maintenance_order.vehicle_id,
                        vehicle.driver_id,
                        relation.system_id,
                        cost_line.cost_type,
                        cost_line.component_name,
                        cost_line.product_id,
                        cost_line.technician_id,
                        cost_line.quantity,
                        COALESCE(cost_line.cost, 0.0)
                            / GREATEST(COALESCE(system_count.system_count, 1), 1) AS cost,
                        company.currency_id,
                        maintenance_order.company_id,
                        maintenance_order.state
                    FROM maintenance_cost_lines cost_line
                    JOIN fleet_vehicle_maintenance_order maintenance_order
                        ON maintenance_order.id = cost_line.order_id
                    JOIN fleet_vehicle vehicle
                        ON vehicle.id = maintenance_order.vehicle_id
                    JOIN res_company company
                        ON company.id = maintenance_order.company_id
                    LEFT JOIN fleet_vehicle_maintenance_order_system_rel relation
                        ON relation.order_id = maintenance_order.id
                    LEFT JOIN system_counts system_count
                        ON system_count.order_id = maintenance_order.id
                )
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY request_date, vehicle_id, cost_type, component_name
                    ) AS id,
                    request_date,
                    order_id,
                    vehicle_id,
                    driver_id,
                    system_id,
                    cost_type,
                    component_name,
                    product_id,
                    technician_id,
                    quantity,
                    cost,
                    currency_id,
                    company_id,
                    state
                FROM unified_costs
            )
            """
        )
