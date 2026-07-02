from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    orangehrm_employee_ids = fields.One2many(
        "hr.employee",
        "work_contact_id",
        string="Empleados OrangeHRM vinculados",
    )
    is_orangehrm_fleet_driver_contact = fields.Boolean(
        string="Contacto de chofer OrangeHRM",
        compute="_compute_is_orangehrm_fleet_driver_contact",
        compute_sudo=True,
        store=True,
        index=True,
    )

    @api.depends("orangehrm_employee_ids.is_fleet_driver")
    def _compute_is_orangehrm_fleet_driver_contact(self):
        for partner in self:
            # Flota usa res.partner como conductor; OrangeHRM marca el rol en hr.employee.
            partner.is_orangehrm_fleet_driver_contact = any(
                partner.orangehrm_employee_ids.mapped("is_fleet_driver")
            )
