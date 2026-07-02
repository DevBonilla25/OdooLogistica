{
    "name": "Filtro de choferes OrangeHRM en Flota",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Fleet",
    "summary": "Filtra los conductores de vehiculos por choferes sincronizados desde OrangeHRM",
    "depends": [
        "fleet",
        "hr",
        "orangehrm_odoo_users_sync",
    ],
    "data": [
        "views/fleet_vehicle_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
