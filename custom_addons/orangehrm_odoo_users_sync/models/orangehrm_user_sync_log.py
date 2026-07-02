from odoo import fields, models


class OrangeHrmUserSyncLog(models.Model):
    _name = "orangehrm.user.sync.log"
    _description = "Log de sincronizacion de empleados OrangeHRM"
    _order = "sync_at desc, id desc"

    name = fields.Char(
        string="Referencia",
        required=True,
        default="Sincronizacion OrangeHRM",
    )
    sync_at = fields.Datetime(
        string="Fecha",
        required=True,
        default=fields.Datetime.now,
    )
    state = fields.Selection(
        [
            ("success", "Correcto"),
            ("warning", "Advertencia"),
            ("error", "Error"),
        ],
        string="Estado",
        required=True,
        default="success",
    )
    total_read = fields.Integer(string="Consultados")
    total_employees = fields.Integer(string="Empleados sincronizados")
    total_fleet_drivers = fields.Integer(string="Choferes detectados")
    total_salespersons = fields.Integer(string="Vendedores detectados")
    total_created = fields.Integer(string="Creados")
    total_updated = fields.Integer(string="Actualizados")
    total_skipped = fields.Integer(string="Omitidos")
    error_count = fields.Integer(string="Errores")
    message = fields.Text(string="Mensaje")
