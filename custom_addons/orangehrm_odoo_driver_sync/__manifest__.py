{
    "name": "OrangeHRM Odoo Driver Sync",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Fleet",
    "summary": "Sincroniza choferes desde OrangeHRM hacia Odoo Flota",
    "depends": [
        "base",
        "fleet",
        "hr",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/hr_employee_views.xml",
        "views/orangehrm_driver_sync_log_views.xml",
        "views/orangehrm_driver_sync_config_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
