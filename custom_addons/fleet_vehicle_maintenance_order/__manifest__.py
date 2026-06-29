{
    "name": "Ordenes de mantenimiento vehicular",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Fleet",
    "summary": "Flujo de ordenes de mantenimiento vehicular para Flota",
    "depends": [
        "fleet",
        "product",
        "stock",
        "purchase",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/fleet_vehicle_system_data.xml",
        "data/ir_sequence_data.xml",
        "views/fleet_vehicle_maintenance_order_views.xml",
        "views/purchase_order_views.xml",
        "views/fleet_vehicle_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
