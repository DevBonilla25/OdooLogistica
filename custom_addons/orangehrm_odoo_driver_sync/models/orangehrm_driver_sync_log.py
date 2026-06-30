from odoo import fields, models


class OrangeHrmDriverSyncLog(models.Model):
    _name = "orangehrm.driver.sync.log"
    _description = "Log de sincronizacion de choferes OrangeHRM"
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
    total_drivers = fields.Integer(string="Choferes detectados")
    total_created = fields.Integer(string="Creados")
    total_updated = fields.Integer(string="Actualizados")
    total_skipped = fields.Integer(string="Omitidos")
    error_count = fields.Integer(string="Errores")
    message = fields.Text(string="Mensaje")
