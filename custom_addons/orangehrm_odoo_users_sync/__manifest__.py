{
    "name": "OrangeHRM Odoo Users Sync",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "summary": "Sincroniza empleados de OrangeHRM hacia Odoo",
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
        "views/orangehrm_hr_catalog_views.xml",
        "views/orangehrm_user_sync_log_views.xml",
        "views/orangehrm_user_sync_config_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
