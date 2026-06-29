from collections import defaultdict

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class FleetVehicleSystem(models.Model):
    _name = "fleet.vehicle.system"
    _description = "Sistema vehicular"
    _order = "sequence, name"

    name = fields.Char(string="Nombre", required=True, translate=True)
    code = fields.Char(string="Codigo", required=True)
    sequence = fields.Integer(string="Secuencia", default=10)
    active = fields.Boolean(string="Activo", default=True)

    _sql_constraints = [
        ("code_unique", "unique(code)", "El codigo del sistema vehicular debe ser unico."),
    ]


class FleetVehicleMaintenanceOrder(models.Model):
    _name = "fleet.vehicle.maintenance.order"
    _description = "Orden de mantenimiento vehicular"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "request_date desc, id desc"

    name = fields.Char(
        string="Orden",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Nuevo"),
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehiculo",
        required=True,
        tracking=True,
        index=True,
    )
    reporter_id = fields.Many2one(
        "res.partner",
        string="Chofer / Reportante",
        tracking=True,
        help="Persona que reporto la novedad. Puede ser el chofer asignado u otro contacto.",
    )
    responsible_id = fields.Many2one(
        "res.users",
        string="Responsable",
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compania",
        related="vehicle_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        related="company_id.currency_id",
        readonly=True,
    )
    request_date = fields.Datetime(
        string="Fecha de reporte",
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    diagnosis_date = fields.Datetime(string="Fecha de diagnostico", tracking=True)
    approval_date = fields.Datetime(string="Fecha de aprobacion", tracking=True)
    start_date = fields.Datetime(string="Inicio de ejecucion", tracking=True)
    finish_date = fields.Datetime(string="Fecha de finalizacion", tracking=True)
    close_date = fields.Datetime(string="Fecha de cierre", tracking=True)
    odometer = fields.Float(string="Odometro", tracking=True)
    problem_description = fields.Text(string="Problema reportado", required=True, tracking=True)
    diagnosis = fields.Text(string="Diagnostico", tracking=True)
    observations = fields.Text(string="Observaciones")
    system_ids = fields.Many2many(
        "fleet.vehicle.system",
        "fleet_vehicle_maintenance_order_system_rel",
        "order_id",
        "system_id",
        string="Sistemas afectados",
        tracking=True,
    )
    activity_line_ids = fields.One2many(
        "fleet.vehicle.maintenance.activity.line",
        "order_id",
        string="Actividades",
        copy=True,
    )
    part_line_ids = fields.One2many(
        "fleet.vehicle.maintenance.part.line",
        "order_id",
        string="Repuestos requeridos",
        copy=True,
    )
    labor_line_ids = fields.One2many(
        "fleet.vehicle.maintenance.labor.line",
        "order_id",
        string="Mano de obra",
        copy=True,
    )
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
        string="Estado",
        default="reported",
        required=True,
        tracking=True,
        copy=False,
    )
    activity_cost = fields.Monetary(
        string="Costo de actividades",
        compute="_compute_costs",
        store=True,
    )
    parts_cost = fields.Monetary(
        string="Costo de repuestos",
        compute="_compute_costs",
        store=True,
    )
    labor_cost = fields.Monetary(
        string="Costo de mano de obra",
        compute="_compute_costs",
        store=True,
    )
    total_cost = fields.Monetary(
        string="Costo total",
        compute="_compute_costs",
        store=True,
    )
    consumed_parts_cost = fields.Monetary(
        string="Costo consumido de bodega",
        compute="_compute_costs",
        store=True,
    )
    stock_move_ids = fields.One2many(
        "stock.move",
        "fleet_maintenance_order_id",
        string="Movimientos de inventario",
        readonly=True,
    )
    stock_move_count = fields.Integer(
        string="Movimientos de inventario",
        compute="_compute_stock_move_count",
    )
    purchase_order_ids = fields.One2many(
        "purchase.order",
        "fleet_maintenance_order_id",
        string="Compras",
        readonly=True,
    )
    purchase_order_count = fields.Integer(
        string="Compras",
        compute="_compute_purchase_order_count",
    )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = sequence.next_by_code("fleet.vehicle.maintenance.order") or _("Nuevo")
        return super().create(vals_list)

    @api.onchange("vehicle_id")
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.reporter_id = self.vehicle_id.driver_id
            self.odometer = self.vehicle_id.odometer

    @api.depends(
        "activity_line_ids.estimated_cost",
        "part_line_ids.subtotal",
        "part_line_ids.consumed_cost",
        "labor_line_ids.subtotal",
    )
    def _compute_costs(self):
        for order in self:
            order.activity_cost = sum(order.activity_line_ids.mapped("estimated_cost"))
            order.parts_cost = sum(order.part_line_ids.mapped("subtotal"))
            order.consumed_parts_cost = sum(order.part_line_ids.mapped("consumed_cost"))
            order.labor_cost = sum(order.labor_line_ids.mapped("subtotal"))
            order.total_cost = order.activity_cost + order.parts_cost + order.labor_cost

    def _compute_stock_move_count(self):
        move_data = self.env["stock.move"]._read_group(
            [("fleet_maintenance_order_id", "in", self.ids)],
            ["fleet_maintenance_order_id"],
            ["__count"],
        )
        mapped_data = {order.id: count for order, count in move_data}
        for order in self:
            order.stock_move_count = mapped_data.get(order.id, 0)

    def _compute_purchase_order_count(self):
        purchase_data = self.env["purchase.order"]._read_group(
            [("fleet_maintenance_order_id", "in", self.ids)],
            ["fleet_maintenance_order_id"],
            ["__count"],
        )
        mapped_data = {order.id: count for order, count in purchase_data}
        for order in self:
            order.purchase_order_count = mapped_data.get(order.id, 0)

    def _set_state(self, state):
        self.write({"state": state})

    def action_to_diagnosis(self):
        self._set_state("diagnosis")

    def action_to_approval(self):
        for order in self:
            if not order.diagnosis:
                raise UserError(_("Agregue un diagnostico antes de solicitar aprobacion."))
        self.write({"state": "approval", "diagnosis_date": fields.Datetime.now()})

    def action_approve(self):
        self.write({"state": "approved", "approval_date": fields.Datetime.now()})

    def action_start_execution(self):
        self.write({"state": "execution", "start_date": fields.Datetime.now()})

    def action_parts_pending(self):
        self._set_state("parts_pending")

    def action_finish(self):
        self.write({"state": "finished", "finish_date": fields.Datetime.now()})

    def action_close(self):
        self.write({"state": "closed", "close_date": fields.Datetime.now()})

    def action_cancel(self):
        self._set_state("cancelled")

    def action_reset_to_reported(self):
        self._set_state("reported")

    def action_open_stock_moves(self):
        self.ensure_one()
        return {
            "name": _("Movimientos de inventario"),
            "type": "ir.actions.act_window",
            "res_model": "stock.move",
            "view_mode": "list,form",
            "domain": [("fleet_maintenance_order_id", "=", self.id)],
            "context": {"default_fleet_maintenance_order_id": self.id},
        }

    def action_open_purchase_orders(self):
        self.ensure_one()
        return {
            "name": _("Compras de repuestos"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("fleet_maintenance_order_id", "=", self.id)],
            "context": {"default_fleet_maintenance_order_id": self.id},
        }

    def action_consume_stock_parts(self):
        for order in self:
            order._consume_stock_parts()

    def action_create_parts_rfq(self):
        for order in self:
            order._create_parts_rfq()

    def _consume_stock_parts(self):
        self.ensure_one()
        if self.state not in ("approved", "execution", "parts_pending"):
            raise UserError(_("Solo puede consumir repuestos cuando la orden esta aprobada o en ejecucion."))

        lines = self.part_line_ids.filtered(lambda line: line.consume_from_stock and not line.stock_move_id)
        if not lines:
            raise UserError(_("No hay repuestos pendientes para consumir desde bodega."))

        created_moves = self.env["stock.move"]
        for line in lines:
            created_moves |= line._create_stock_consumption_move()

        body_lines = "".join(
            "<li>%s: %s %s</li>"
            % (
                move.product_id.display_name,
                move.product_uom_qty,
                move.product_uom.display_name,
            )
            for move in created_moves
        )
        self.message_post(
            body=Markup("<p>%s</p><ul>%s</ul>")
            % (_("Repuestos consumidos desde bodega:"), Markup(body_lines))
        )

    def _create_parts_rfq(self):
        self.ensure_one()
        if self.state not in ("approval", "approved", "execution", "parts_pending"):
            raise UserError(
                _("Solo puede crear RFQ desde pendiente de aprobacion, aprobada, en ejecucion o pendiente de repuestos.")
            )

        lines = self.part_line_ids.filtered(lambda line: line.source == "purchase" and not line.purchase_order_line_id)
        if not lines:
            raise UserError(_("No hay repuestos por comprar pendientes de RFQ."))

        for line in lines:
            if not line.product_id:
                raise UserError(_("Seleccione un producto para comprar el repuesto %s.") % line.name)
            if line.purchase_qty <= 0:
                raise UserError(_("La cantidad a comprar debe ser mayor que cero para %s.") % line.name)
            if not line.suggested_vendor_id:
                raise UserError(_("Seleccione un proveedor sugerido para %s.") % line.name)

        lines_by_vendor = defaultdict(lambda: self.env["fleet.vehicle.maintenance.part.line"])
        for line in lines:
            lines_by_vendor[line.suggested_vendor_id] |= line

        created_orders = self.env["purchase.order"]
        for vendor, vendor_lines in lines_by_vendor.items():
            purchase_order = self.env["purchase.order"].create({
                "partner_id": vendor.id,
                "origin": self.name,
                "company_id": self.company_id.id,
                "fleet_maintenance_order_id": self.id,
            })
            for line in vendor_lines:
                purchase_line = self.env["purchase.order.line"].create({
                    "order_id": purchase_order.id,
                    "product_id": line.product_id.id,
                    "name": line.name or line.product_id.display_name,
                    "product_qty": line.purchase_qty,
                    "product_uom_id": line.purchase_uom_id.id or line.product_id.uom_id.id,
                    "price_unit": line.estimated_purchase_price,
                    "date_planned": fields.Datetime.now(),
                    "fleet_maintenance_part_line_id": line.id,
                })
                line.write({
                    "purchase_order_id": purchase_order.id,
                    "purchase_order_line_id": purchase_line.id,
                })
            created_orders |= purchase_order

        body_lines = "".join(
            "<li>%s - %s</li>" % (order.name, order.partner_id.display_name)
            for order in created_orders
        )
        self.message_post(
            body=Markup("<p>%s</p><ul>%s</ul>")
            % (_("RFQ de repuestos creadas:"), Markup(body_lines))
        )


class FleetVehicleMaintenanceActivityLine(models.Model):
    _name = "fleet.vehicle.maintenance.activity.line"
    _description = "Linea de actividad de mantenimiento vehicular"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)
    order_id = fields.Many2one(
        "fleet.vehicle.maintenance.order",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="Actividad", required=True)
    description = fields.Text(string="Descripcion")
    estimated_cost = fields.Monetary(string="Costo estimado")
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)
    state = fields.Selection(related="order_id.state", readonly=True)


class FleetVehicleMaintenancePartLine(models.Model):
    _name = "fleet.vehicle.maintenance.part.line"
    _description = "Linea de repuesto de mantenimiento vehicular"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)
    order_id = fields.Many2one(
        "fleet.vehicle.maintenance.order",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        domain="[('type', '!=', 'service')]",
    )
    name = fields.Char(string="Descripcion", required=True)
    quantity = fields.Float(string="Cantidad", default=1.0, required=True)
    uom_id = fields.Many2one("uom.uom", string="Unidad de medida")
    source = fields.Selection(
        [
            ("stock", "Desde inventario"),
            ("purchase", "Por comprar"),
            ("unknown", "Por definir"),
        ],
        string="Origen",
        default="unknown",
        required=True,
    )
    consume_from_stock = fields.Boolean(string="Sale de bodega")
    source_location_id = fields.Many2one(
        "stock.location",
        string="Ubicacion origen",
        domain="[('usage', '=', 'internal')]",
    )
    available_qty = fields.Float(
        string="Disponible",
        compute="_compute_available_qty",
    )
    stock_move_id = fields.Many2one(
        "stock.move",
        string="Movimiento de inventario",
        readonly=True,
        copy=False,
    )
    consumed_cost = fields.Monetary(
        string="Costo consumido",
        readonly=True,
        copy=False,
    )
    consumed = fields.Boolean(
        string="Consumido",
        compute="_compute_consumed",
        store=True,
    )
    suggested_vendor_id = fields.Many2one(
        "res.partner",
        string="Proveedor sugerido",
        domain="[('supplier_rank', '>', 0)]",
    )
    purchase_qty = fields.Float(string="Cantidad a comprar", default=1.0)
    purchase_uom_id = fields.Many2one("uom.uom", string="Unidad de compra")
    estimated_purchase_price = fields.Monetary(string="Precio estimado de compra")
    purchase_state = fields.Selection(
        [
            ("no_purchase_required", "No requiere compra"),
            ("pending_purchase", "Pendiente de compra"),
            ("rfq_created", "RFQ creada"),
            ("purchase_confirmed", "Compra confirmada"),
            ("received", "Recibido"),
            ("cancelled", "Cancelado"),
        ],
        string="Estado de compra",
        compute="_compute_purchase_state",
        store=True,
    )
    purchase_order_id = fields.Many2one(
        "purchase.order",
        string="RFQ / Compra",
        readonly=True,
        copy=False,
    )
    purchase_order_line_id = fields.Many2one(
        "purchase.order.line",
        string="Linea de compra",
        readonly=True,
        copy=False,
    )
    price_unit = fields.Monetary(string="Costo unitario")
    subtotal = fields.Monetary(string="Subtotal", compute="_compute_subtotal", store=True)
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)
    state = fields.Selection(related="order_id.state", readonly=True)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.display_name
                line.uom_id = line.product_id.uom_id
                line.price_unit = line.product_id.standard_price
                if line.source == "unknown":
                    line.source = "stock"
                line.purchase_uom_id = line.product_id.uom_id
                line.purchase_qty = line.quantity
                seller = line.product_id.seller_ids[:1]
                if seller:
                    line.suggested_vendor_id = seller.partner_id
                    line.estimated_purchase_price = seller.price_discounted or seller.price
                else:
                    line.estimated_purchase_price = line.product_id.standard_price

    @api.onchange("source")
    def _onchange_source(self):
        for line in self:
            if line.source == "purchase":
                line.consume_from_stock = False
                line.purchase_qty = line.quantity
                line.purchase_uom_id = line.uom_id or line.product_id.uom_id
                if line.product_id and not line.estimated_purchase_price:
                    line.estimated_purchase_price = line.product_id.standard_price
                line.price_unit = line.estimated_purchase_price

    @api.onchange("consume_from_stock")
    def _onchange_consume_from_stock(self):
        for line in self:
            if line.consume_from_stock:
                line.source = "stock"

    @api.depends(
        "source",
        "purchase_order_line_id",
        "purchase_order_line_id.state",
        "purchase_order_line_id.qty_received",
        "purchase_order_line_id.product_qty",
    )
    def _compute_purchase_state(self):
        for line in self:
            purchase_line = line.purchase_order_line_id
            if line.source != "purchase":
                line.purchase_state = "no_purchase_required"
            elif not purchase_line:
                line.purchase_state = "pending_purchase"
            elif purchase_line.state == "cancel":
                line.purchase_state = "cancelled"
            elif purchase_line.state == "purchase" and purchase_line.qty_received >= purchase_line.product_qty:
                line.purchase_state = "received"
            elif purchase_line.state == "purchase":
                line.purchase_state = "purchase_confirmed"
            else:
                line.purchase_state = "rfq_created"

    @api.depends("stock_move_id", "stock_move_id.state")
    def _compute_consumed(self):
        for line in self:
            line.consumed = line.stock_move_id.state == "done"

    @api.onchange("estimated_purchase_price")
    def _onchange_estimated_purchase_price(self):
        for line in self:
            if line.source == "purchase":
                line.price_unit = line.estimated_purchase_price

    @api.depends("quantity", "price_unit", "source", "purchase_qty", "estimated_purchase_price")
    def _compute_subtotal(self):
        for line in self:
            if line.source == "purchase":
                line.subtotal = line.purchase_qty * line.estimated_purchase_price
            else:
                line.subtotal = line.quantity * line.price_unit

    @api.depends("product_id", "source_location_id")
    def _compute_available_qty(self):
        Quant = self.env["stock.quant"]
        for line in self:
            if line.product_id and line.source_location_id:
                line.available_qty = Quant._get_available_quantity(line.product_id, line.source_location_id)
            else:
                line.available_qty = 0.0

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("La cantidad del repuesto debe ser mayor que cero."))

    def _get_source_location(self):
        self.ensure_one()
        if self.source_location_id:
            return self.source_location_id
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.order_id.company_id.id)],
            limit=1,
        )
        if warehouse:
            return warehouse.lot_stock_id
        return self.env.ref("stock.stock_location_stock", raise_if_not_found=False)

    def _create_stock_consumption_move(self):
        self.ensure_one()
        if self.stock_move_id:
            raise UserError(_("El repuesto %s ya fue consumido.") % self.name)
        if not self.product_id:
            raise UserError(_("Seleccione un producto para consumir el repuesto %s.") % self.name)
        if self.product_id.type == "service":
            raise UserError(_("No se pueden consumir servicios desde bodega: %s.") % self.product_id.display_name)
        if self.product_id.tracking != "none":
            raise UserError(
                _("El producto %s requiere lote/serie. Ese caso se implementara en una fase posterior.")
                % self.product_id.display_name
            )

        source_location = self._get_source_location()
        if not source_location:
            raise UserError(_("No se encontro una ubicacion de bodega para consumir repuestos."))

        product_qty = self.uom_id._compute_quantity(self.quantity, self.product_id.uom_id) if self.uom_id else self.quantity
        available_qty = self.env["stock.quant"]._get_available_quantity(self.product_id, source_location)
        if self.product_id.uom_id.compare(available_qty, product_qty) < 0:
            raise UserError(
                _("Stock insuficiente para %(product)s. Disponible: %(available)s, requerido: %(required)s.")
                % {
                    "product": self.product_id.display_name,
                    "available": available_qty,
                    "required": product_qty,
                }
            )

        inventory_location = self.product_id.with_company(self.order_id.company_id).property_stock_inventory
        if not inventory_location:
            inventory_location_id = self.env["ir.default"]._get_model_defaults("product.template").get("property_stock_inventory")
            inventory_location = self.env["stock.location"].browse(inventory_location_id)
        if not inventory_location:
            raise UserError(_("No se encontro ubicacion de consumo/perdida de inventario."))

        unit_cost = self.product_id.standard_price
        move = self.env["stock.move"].create({
            "product_id": self.product_id.id,
            "description_picking": "%s - %s" % (self.order_id.name, self.name),
            "product_uom_qty": self.quantity,
            "product_uom": self.uom_id.id or self.product_id.uom_id.id,
            "location_id": source_location.id,
            "location_dest_id": inventory_location.id,
            "origin": self.order_id.name,
            "price_unit": unit_cost,
            "company_id": self.order_id.company_id.id,
            "fleet_maintenance_order_id": self.order_id.id,
            "fleet_maintenance_part_line_id": self.id,
            "fleet_vehicle_id": self.order_id.vehicle_id.id,
        })
        move._action_confirm()
        move._action_assign()
        move.quantity = self.quantity
        move.picked = True
        move = move._action_done()

        self.write({
            "stock_move_id": move.id,
            "source_location_id": source_location.id,
            "consumed_cost": unit_cost * product_qty,
        })
        return move


class FleetVehicleMaintenanceLaborLine(models.Model):
    _name = "fleet.vehicle.maintenance.labor.line"
    _description = "Linea de mano de obra de mantenimiento vehicular"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)
    order_id = fields.Many2one(
        "fleet.vehicle.maintenance.order",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="Trabajo", required=True)
    technician_id = fields.Many2one("res.partner", string="Tecnico / Proveedor")
    hours = fields.Float(string="Horas", default=1.0)
    rate = fields.Monetary(string="Tarifa por hora")
    fixed_cost = fields.Monetary(string="Costo fijo")
    subtotal = fields.Monetary(string="Subtotal", compute="_compute_subtotal", store=True)
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)
    state = fields.Selection(related="order_id.state", readonly=True)

    @api.depends("hours", "rate", "fixed_cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.fixed_cost + (line.hours * line.rate)

    @api.constrains("hours")
    def _check_hours(self):
        for line in self:
            if line.hours < 0:
                raise ValidationError(_("Las horas de mano de obra no pueden ser negativas."))
