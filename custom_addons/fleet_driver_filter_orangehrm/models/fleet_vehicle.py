from odoo import api, fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    show_all_employee_driver_contacts = fields.Boolean(
        string="Ver todos los empleados/usuarios",
        help=(
            "Permite buscar cualquier contacto vinculado a un empleado o usuario. "
            "Si esta desactivado, solo se muestran choferes sincronizados desde OrangeHRM."
        ),
    )
    allowed_driver_partner_ids = fields.Many2many(
        "res.partner",
        compute="_compute_allowed_driver_partner_ids",
        compute_sudo=True,
        string="Conductores permitidos",
    )

    @api.depends("driver_id", "show_all_employee_driver_contacts")
    def _compute_allowed_driver_partner_ids(self):
        Partner = self.env["res.partner"].sudo()
        for vehicle in self:
            if vehicle.show_all_employee_driver_contacts:
                domain = [
                    "|",
                    ("orangehrm_employee_ids", "!=", False),
                    ("user_ids.share", "=", False),
                ]
            else:
                domain = [("is_orangehrm_fleet_driver_contact", "=", True)]

            partners = Partner.search(domain)
            if vehicle.driver_id:
                # Mantiene visible el conductor actual aunque no pertenezca al modo de busqueda seleccionado.
                partners |= vehicle.driver_id.sudo()
            vehicle.allowed_driver_partner_ids = partners
