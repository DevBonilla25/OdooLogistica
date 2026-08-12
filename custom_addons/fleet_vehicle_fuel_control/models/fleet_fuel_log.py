import uuid

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class FleetVehicleLogFuel(models.Model):
    _inherit = "fleet.vehicle.log.fuel"

    liter = fields.Float(digits=(16, 3))
    price_per_liter = fields.Float(digits=(16, 6))
    gallons = fields.Float(
        string="Galones",
        related="liter",
        readonly=False,
        store=True,
        tracking=True,
        aggregator="sum",
    )
    price_per_gallon = fields.Float(
        string="Precio por galon",
        related="price_per_liter",
        readonly=False,
        store=True,
        tracking=True,
    )
    fuel_subtotal = fields.Monetary(
        string="Subtotal combustible",
        compute="_compute_fuel_metrics",
        store=True,
        tracking=True,
        aggregator="sum",
    )
    fuel_tax_amount = fields.Monetary(
        string="IVA 15%",
        compute="_compute_fuel_metrics",
        store=True,
        tracking=True,
        aggregator="sum",
    )
    fuel_total_cost = fields.Monetary(
        string="Costo total con IVA",
        compute="_compute_fuel_metrics",
        store=True,
        tracking=True,
        aggregator="sum",
    )
    previous_odometer = fields.Float(
        string="Odometro anterior",
        compute="_compute_previous_odometer",
        store=True,
        tracking=True,
    )
    current_odometer = fields.Float(
        string="Odometro actual",
        related="odometer",
        readonly=False,
        store=True,
        tracking=True,
    )
    has_previous_odometer = fields.Boolean(
        string="Tiene odometro anterior",
        compute="_compute_previous_odometer",
        store=True,
    )
    distance_km = fields.Float(
        string="Kilometros recorridos",
        compute="_compute_fuel_metrics",
        store=True,
        aggregator="sum",
    )
    km_per_gallon = fields.Float(
        string="Km por galon",
        compute="_compute_fuel_metrics",
        store=True,
        aggregator="avg",
    )
    cost_per_km = fields.Float(
        string="Costo por km",
        compute="_compute_fuel_metrics",
        store=True,
        digits=(16, 4),
        aggregator="avg",
    )
    invoice_number = fields.Char(
        string="Numero de factura",
        related="inv_ref",
        readonly=False,
        store=True,
        tracking=True,
    )
    fuel_station_id = fields.Many2one(
        "res.partner",
        string="Gasolinera",
        related="vendor_id",
        readonly=False,
        store=True,
        tracking=True,
    )
    invoice_attachment_ids = fields.Many2many(
        "ir.attachment",
        "fleet_fuel_log_invoice_attachment_rel",
        "fuel_log_id",
        "attachment_id",
        string="Facturas adjuntas",
    )
    legacy_service_id = fields.Many2one(
        "fleet.vehicle.log.services",
        string="Servicio de origen",
        copy=False,
        index=True,
        ondelete="set null",
    )
    legacy_total_cost = fields.Monetary(
        string="Costo historico",
        copy=False,
        readonly=True,
    )
    migration_pending = fields.Boolean(
        string="Migracion pendiente",
        compute="_compute_migration_pending",
        store=True,
    )
    _legacy_service_unique = models.Constraint(
        "UNIQUE(legacy_service_id)",
        "Este servicio de combustible ya fue migrado.",
    )
    approval_state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("pending_review", "Pendiente de revision"),
            ("approved", "Aprobado"),
            ("rejected", "Rechazado"),
        ],
        string="Validacion",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
        index=True,
    )
    external_uuid = fields.Char(
        string="UUID externo",
        default=lambda self: str(uuid.uuid4()),
        copy=False,
        index=True,
    )
    source_system = fields.Selection(
        [
            ("odoo", "Odoo"),
            ("laravel", "Laravel"),
            ("flutter", "Flutter"),
        ],
        string="Sistema origen",
        default="odoo",
        required=True,
        copy=False,
    )
    external_payload_json = fields.Json(string="Payload externo", copy=False)
    synced_at = fields.Datetime(string="Ultima sincronizacion", copy=False)
    sync_status = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("synced", "Sincronizado"),
            ("error", "Error"),
        ],
        string="Estado de sincronizacion",
        default="pending",
        required=True,
        copy=False,
    )

    @api.depends("legacy_service_id", "liter", "price_per_liter", "approval_state")
    def _compute_migration_pending(self):
        for record in self:
            record.migration_pending = bool(
                record.legacy_service_id
                and record.approval_state != "approved"
                and (record.liter <= 0 or record.price_per_liter <= 0)
            )
    @api.model_create_multi
    def create(self, vals_list):
        prepared_values = []
        for values in vals_list:
            values = self._prepare_compatibility_values(values)
            if (
                values.get("approval_state", "draft") != "draft"
                and not self.env.user.has_group("fleet.fleet_group_manager")
            ):
                raise AccessError(_("Solo un responsable de Flota puede crear registros validados."))
            prepared_values.append(values)
        return super().create(prepared_values)

    def write(self, vals):
        if len(self) > 1 and self._has_metric_values(vals):
            for record in self:
                record.write(vals)
            return True

        values = self._prepare_compatibility_values(vals, self[:1])
        if not self.env.context.get("fuel_control_workflow"):
            self._check_write_access(values)
        return super().write(values)

    def unlink(self):
        if not self.env.user.has_group("fleet.fleet_group_manager"):
            if any(record.approval_state != "draft" for record in self):
                raise AccessError(_("Solo puede eliminar registros de combustible en borrador."))
        legacy_services = self.mapped("legacy_service_id").with_context(active_test=False)
        result = super().unlink()
        legacy_services.write({"active": True})
        return result

    @api.model
    def _prepare_compatibility_values(self, vals, record=None):
        values = dict(vals)
        aliases = {
            "gallons": "liter",
            "price_per_gallon": "price_per_liter",
            "current_odometer": "odometer",
            "invoice_number": "inv_ref",
            "fuel_station_id": "vendor_id",
        }
        for alias, original in aliases.items():
            if alias in values:
                values.setdefault(original, values[alias])
                values.pop(alias)

        for computed_field in (
            "fuel_subtotal", "fuel_tax_amount", "fuel_total_cost"
        ):
            values.pop(computed_field, None)

        if self._has_metric_values(values):
            quantity = values.get("liter", record.liter if record else 0.0)
            price = values.get(
                "price_per_liter",
                record.price_per_liter if record else 0.0,
            )
            subtotal = round(quantity * price, 2)
            total = round(subtotal * 1.15, 2)
            values["amount"] = (
                0.0
                if record and record.legacy_service_id and record.approval_state != "approved"
                else total
            )
        return values

    @api.model
    def _has_metric_values(self, vals):
        return bool(
            {
                "gallons",
                "liter",
                "price_per_gallon",
                "price_per_liter",
            }
            & set(vals)
        )

    def _check_write_access(self, vals):
        if self.env.user.has_group("fleet.fleet_group_manager"):
            return
        for record in self:
            if record.approval_state != "draft":
                raise AccessError(
                    _("Los usuarios de Flota solo pueden editar registros en borrador.")
                )
            new_state = vals.get("approval_state")
            if new_state and new_state not in ("draft", "pending_review"):
                raise AccessError(_("Solo un responsable de Flota puede validar combustible."))

    @api.depends("vehicle_id", "date")
    def _compute_previous_odometer(self):
        FuelLog = self.env["fleet.vehicle.log.fuel"]
        for record in self:
            record.previous_odometer = 0.0
            record.has_previous_odometer = False
            if not record.vehicle_id:
                continue
            record_date = record.date or fields.Date.context_today(record)
            domain = [("vehicle_id", "=", record.vehicle_id.id)]
            if record.id and isinstance(record.id, int):
                domain += [
                    "|",
                    ("date", "<", record_date),
                    "&",
                    ("date", "=", record_date),
                    ("id", "<", record.id),
                ]
            else:
                domain.append(("date", "<=", record_date))
            domain += [
                "|",
                ("approval_state", "=", "approved"),
                ("state", "=", "done"),
            ]
            previous = FuelLog.search(domain, order="date desc, id desc", limit=1)
            if previous:
                record.previous_odometer = previous.current_odometer
                record.has_previous_odometer = True

    @api.depends(
        "liter",
        "price_per_liter",
        "odometer",
        "previous_odometer",
        "has_previous_odometer",
        "legacy_service_id",
        "legacy_total_cost",
    )
    def _compute_fuel_metrics(self):
        for record in self:
            currency = record.currency_id or record.company_id.currency_id
            if record.liter > 0 and record.price_per_liter > 0:
                subtotal = currency.round(record.liter * record.price_per_liter)
                tax_amount = currency.round(subtotal * 0.15)
            else:
                total = record.legacy_total_cost if record.legacy_service_id else 0.0
                subtotal = currency.round(total / 1.15) if total else 0.0
                tax_amount = total - subtotal
            record.fuel_subtotal = subtotal
            record.fuel_tax_amount = tax_amount
            record.fuel_total_cost = subtotal + tax_amount
            distance = (
                record.odometer - record.previous_odometer
                if record.has_previous_odometer
                else 0.0
            )
            record.distance_km = max(distance, 0.0)
            record.km_per_gallon = (
                record.distance_km / record.liter if record.liter else 0.0
            )
            record.cost_per_km = (
                record.fuel_total_cost / record.distance_km
                if record.distance_km
                else 0.0
            )

    @api.onchange("vehicle_id", "date")
    def _onchange_previous_odometer(self):
        for record in self:
            record.liter = record.gallons
            record.price_per_liter = record.price_per_gallon
        self._compute_previous_odometer()
        self._compute_fuel_metrics()

    @api.onchange("liter", "price_per_liter", "amount")
    def _onchange_liter_price_amount(self):
        self._compute_fuel_metrics()
        for record in self:
            record.amount = (
                0.0
                if record.legacy_service_id and record.approval_state != "approved"
                else record.fuel_total_cost
            )

    @api.onchange("gallons", "price_per_gallon")
    def _onchange_gallon_values(self):
        for record in self:
            record.liter = record.gallons
            record.price_per_liter = record.price_per_gallon
        self._compute_fuel_metrics()
        for record in self:
            record.amount = (
                0.0
                if record.legacy_service_id and record.approval_state != "approved"
                else record.fuel_total_cost
            )

    @api.constrains("liter", "price_per_liter", "odometer", "previous_odometer")
    def _check_fuel_metrics(self):
        for record in self:
            if record.liter <= 0 and not record.legacy_service_id:
                raise ValidationError(_("Los galones deben ser mayores que cero."))
            if record.price_per_liter < 0:
                raise ValidationError(_("El precio por galon no puede ser negativo."))
            if (
                record.previous_odometer
                and record.odometer < record.previous_odometer
            ):
                raise ValidationError(
                    _("El odometro actual no puede ser menor que el anterior.")
                )

    def action_submit_review(self):
        records = self.filtered(lambda record: record.approval_state == "draft")
        if any(record.liter <= 0 or record.price_per_liter <= 0 for record in records):
            raise ValidationError(
                _("Complete los galones y el precio por galon antes de enviar a revision.")
            )
        records.with_context(fuel_control_workflow=True).write(
            {"approval_state": "pending_review"}
        )
        return True

    def action_approve(self):
        self._ensure_fleet_manager()
        records = self.filtered(
            lambda record: record.approval_state == "pending_review"
        )
        for record in records:
            record.with_context(fuel_control_workflow=True).write(
                {
                    "approval_state": "approved",
                    "amount": record.fuel_total_cost,
                }
            )
            if record.legacy_service_id:
                record.legacy_service_id.with_context(active_test=False).write(
                    {"active": False}
                )
        records._recompute_following_logs()
        return True

    def action_reject(self):
        self._ensure_fleet_manager()
        self.filtered(
            lambda record: record.approval_state == "pending_review"
        ).with_context(fuel_control_workflow=True).write(
            {"approval_state": "rejected"}
        )
        return True

    def action_reset_to_draft(self):
        self._ensure_fleet_manager()
        self.filtered(
            lambda record: record.approval_state == "rejected"
        ).with_context(fuel_control_workflow=True).write(
            {"approval_state": "draft"}
        )
        return True

    def _ensure_fleet_manager(self):
        if not self.env.user.has_group("fleet.fleet_group_manager"):
            raise AccessError(_("Solo un responsable de Flota puede realizar esta accion."))

    def _recompute_following_logs(self):
        for record in self:
            following = self.search(
                [
                    ("vehicle_id", "=", record.vehicle_id.id),
                    "|",
                    ("date", ">", record.date),
                    "&",
                    ("date", "=", record.date),
                    ("id", ">", record.id),
                ]
            )
            following._compute_previous_odometer()
            following._compute_fuel_metrics()

    def button_running(self):
        if any(record.approval_state != "approved" for record in self):
            raise UserError(_("El registro debe estar aprobado antes de iniciar."))
        return super(
            FleetVehicleLogFuel,
            self.with_context(fuel_control_workflow=True),
        ).button_running()

    def button_done(self):
        if any(record.approval_state != "approved" for record in self):
            raise UserError(_("El registro debe estar aprobado antes de finalizar."))
        migrated = self.filtered(
            lambda record: record.legacy_service_id and record.state == "running"
        )
        regular = self - migrated
        if regular:
            super(
                FleetVehicleLogFuel,
                regular.with_context(fuel_control_workflow=True),
            ).button_done()
        for record in migrated:
            service = record.legacy_service_id.with_context(active_test=False)
            values = record._prepare_fleet_vehicle_log_services_vals()
            values["active"] = False
            service.write(values)
            record.with_context(fuel_control_workflow=True).write(
                {"service_id": service.id, "state": "done"}
            )
        return True

    def button_cancel(self):
        migrated = self.filtered("legacy_service_id")
        regular = self - migrated
        if regular:
            super(
                FleetVehicleLogFuel,
                regular.with_context(fuel_control_workflow=True),
            ).button_cancel()
        for record in migrated.filtered(
            lambda item: item.state in ("todo", "running", "done")
        ):
            record.legacy_service_id.with_context(active_test=False).write(
                {"active": True}
            )
            record.with_context(fuel_control_workflow=True).write(
                {"service_id": False, "state": "cancelled"}
            )
        return True

    def button_todo(self):
        migrated = self.filtered("legacy_service_id")
        regular = self - migrated
        if regular:
            super(
                FleetVehicleLogFuel,
                regular.with_context(fuel_control_workflow=True),
            ).button_todo()
        for record in migrated.filtered(lambda item: item.state == "cancelled"):
            record.legacy_service_id.with_context(active_test=False).write(
                {"active": False}
            )
            record.with_context(fuel_control_workflow=True).write({"state": "todo"})
        return True

    def _prepare_fleet_vehicle_log_services_vals(self):
        values = super()._prepare_fleet_vehicle_log_services_vals()
        values["amount"] = self.fuel_total_cost
        return values
