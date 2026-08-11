{
    "name": "Control de combustible de vehiculos",
    "version": "19.0.1.1.0",
    "category": "Fleet",
    "summary": "Control, aprobacion y analisis de consumo de combustible",
    "author": "Bonilla",
    "license": "AGPL-3",
    "depends": [
        "fleet",
        "fleet_vehicle_log_fuel",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/fleet_fuel_log_views.xml",
        "views/fleet_fuel_report_menus.xml",
        "wizard/fleet_fuel_service_migration_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
