from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    orangehrm_employee_id = fields.Char(
        string="ID OrangeHRM",
        index=True,
        copy=False,
    )
    orangehrm_employee_number = fields.Char(
        string="Numero empleado OrangeHRM",
        index=True,
        copy=False,
    )
    orangehrm_job_title = fields.Char(
        string="Cargo OrangeHRM",
        copy=False,
    )
    orangehrm_employment_status = fields.Char(
        string="Estado laboral OrangeHRM",
        copy=False,
    )
    orangehrm_termination_id = fields.Char(
        string="ID terminacion OrangeHRM",
        copy=False,
    )
    orangehrm_last_sync_at = fields.Datetime(
        string="Ultima sincronizacion OrangeHRM",
        copy=False,
        readonly=True,
    )
    orangehrm_sync_role = fields.Selection(
        [
            ("employee", "Empleado"),
            ("fleet_driver", "Chofer de flota"),
            ("salesperson", "Vendedor"),
        ],
        string="Rol sincronizado",
        default="employee",
        copy=False,
        index=True,
    )
    is_fleet_driver = fields.Boolean(
        string="Chofer de flota",
        copy=False,
        index=True,
    )
    is_orangehrm_salesperson = fields.Boolean(
        string="Vendedor OrangeHRM",
        copy=False,
        index=True,
    )
    driver_type = fields.Selection(
        [
            ("interno", "Interno"),
            ("externo", "Externo"),
            ("no_definido", "No definido"),
        ],
        string="Tipo de chofer",
        default="no_definido",
        copy=False,
    )
