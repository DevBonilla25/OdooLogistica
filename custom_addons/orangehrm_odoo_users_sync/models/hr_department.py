from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    orangehrm_subunit_id = fields.Integer(
        string="ID departamento OrangeHRM",
        index=True,
        copy=False,
    )
    orangehrm_unit_id = fields.Char(
        string="Codigo departamento OrangeHRM",
        copy=False,
    )
    orangehrm_level = fields.Integer(
        string="Nivel OrangeHRM",
        copy=False,
    )
