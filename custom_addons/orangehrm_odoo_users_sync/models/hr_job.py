from odoo import fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    orangehrm_job_title_id = fields.Integer(
        string="ID puesto OrangeHRM",
        index=True,
        copy=False,
    )
    orangehrm_job_description = fields.Text(
        string="Descripcion puesto OrangeHRM",
        copy=False,
    )
