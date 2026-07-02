import logging
from collections import Counter
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OrangeHrmUserSyncConfig(models.Model):
    _name = "orangehrm.user.sync.config"
    _description = "Configuracion de sincronizacion OrangeHRM"
    _inherit = ["mail.thread"]

    name = fields.Char(
        string="Nombre",
        required=True,
        default="OrangeHRM",
    )
    active = fields.Boolean(
        string="Sincronizacion activa",
        default=False,
        tracking=True,
    )
    orangehrm_base_url = fields.Char(
        string="URL base OrangeHRM",
        required=True,
        help="Ejemplo: http://192.168.1.10/orangehrm",
    )
    orangehrm_employee_endpoint = fields.Char(
        string="Endpoint empleados",
        required=True,
        default="/web/index.php/api/v2/pim/employees?limit=50&offset=0&model=detailed&includeEmployees=onlyCurrent&sortField=employee.firstName&sortOrder=ASC",
    )
    orangehrm_job_title_endpoint = fields.Char(
        string="Endpoint puestos",
        required=True,
        default=lambda self: self.env["orangehrm.api"].JOB_TITLES_ENDPOINT,
    )
    orangehrm_subunit_endpoint = fields.Char(
        string="Endpoint departamentos",
        required=True,
        default=lambda self: self.env["orangehrm.api"].SUBUNITS_ENDPOINT,
    )
    auth_type = fields.Selection(
        [
            ("none", "Sin autenticacion"),
            ("bearer", "Bearer token"),
            ("api_key", "API key"),
            ("basic", "Usuario y contrasena"),
            ("cookie", "Cookie"),
        ],
        string="Tipo de autenticacion",
        required=True,
        default="none",
    )
    username = fields.Char(string="Usuario")
    password = fields.Char(string="Contrasena / Token / Cookie")
    api_key_header = fields.Char(
        string="Cabecera API key",
        default="X-API-Key",
    )
    driver_job_titles = fields.Text(
        string="Cargos de chofer",
        default="Chofer Interno\nChofer Externo\nChofer\nConductor",
        help="Un cargo por linea. La comparacion no distingue mayusculas.",
    )
    salesperson_job_titles = fields.Text(
        string="Cargos de vendedor",
        default="Vendedor\nAsesor Comercial\nEjecutivo Comercial",
        help="Un cargo por linea. Se usara en fases posteriores para reglas comerciales.",
    )
    sync_terminated = fields.Boolean(
        string="Sincronizar empleados terminados",
        default=False,
    )
    timeout = fields.Integer(
        string="Timeout (segundos)",
        default=30,
    )
    frequency = fields.Selection(
        [
            ("manual", "Manual"),
            ("daily", "Diaria"),
        ],
        string="Frecuencia",
        default="manual",
    )
    last_sync_at = fields.Datetime(
        string="Ultima sincronizacion",
        readonly=True,
        copy=False,
    )
    last_sync_status = fields.Selection(
        [
            ("success", "Correcto"),
            ("warning", "Advertencia"),
            ("error", "Error"),
        ],
        string="Ultimo estado",
        readonly=True,
        copy=False,
    )
    last_sync_message = fields.Text(
        string="Ultimo mensaje",
        readonly=True,
        copy=False,
    )

    def action_sync_users(self):
        self.ensure_one()
        log = self._sync_users()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "orangehrm_odoo_users_sync.action_orangehrm_user_sync_log"
        )
        action["domain"] = [("id", "=", log.id)]
        action["views"] = [(False, "form")]
        action["res_id"] = log.id
        return action

    @classmethod
    def _normalize_text(cls, value):
        if value in (None, False):
            return ""
        if isinstance(value, (dict, list, tuple, set)):
            return ""
        return str(value).strip().casefold()

    def _title_set(self, field_name):
        self.ensure_one()
        return {
            self._normalize_text(line)
            for line in (self[field_name] or "").splitlines()
            if line.strip()
        }

    def _build_url(self):
        self.ensure_one()
        if not self.orangehrm_base_url:
            raise UserError(_("Configure la URL base de OrangeHRM."))
        if not self.orangehrm_employee_endpoint:
            raise UserError(_("Configure el endpoint de empleados de OrangeHRM."))
        base_url = self.orangehrm_base_url.strip()
        if not base_url.startswith(("http://", "https://")):
            base_url = "http://%s" % base_url
        url = "%s/%s" % (
            base_url.rstrip("/"),
            self.orangehrm_employee_endpoint.lstrip("/"),
        )
        return self._url_with_default_query(url)

    def _url_with_default_query(self, url):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query.setdefault("limit", ["50"])
        query.setdefault("offset", ["0"])
        query.setdefault("model", ["detailed"])
        query.setdefault("includeEmployees", ["onlyCurrent"])
        query.setdefault("sortField", ["employee.firstName"])
        query.setdefault("sortOrder", ["ASC"])
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    def _request_kwargs(self):
        self.ensure_one()
        headers = {"Accept": "application/json"}
        kwargs = {
            "headers": headers,
            "timeout": self.timeout or 30,
        }
        if self.auth_type == "bearer" and self.password:
            headers["Authorization"] = "Bearer %s" % self.password
        elif self.auth_type == "api_key" and self.password:
            headers[self.api_key_header or "X-API-Key"] = self.password
        elif self.auth_type == "basic":
            kwargs["auth"] = (self.username or "", self.password or "")
        elif self.auth_type == "cookie" and self.password:
            headers["Cookie"] = self.password
        return kwargs

    def _api(self):
        return self.env["orangehrm.api"]

    def _fetch_employees(self):
        self.ensure_one()
        return self._api().request_paginated(self, self.orangehrm_employee_endpoint)

    def _fetch_job_titles(self):
        self.ensure_one()
        return self._api().request_paginated(self, self.orangehrm_job_title_endpoint)

    def _fetch_subunits(self):
        self.ensure_one()
        payload = self._api().request_json(self, self.orangehrm_subunit_endpoint)
        return self._api().flatten_tree(self._api().extract_data_list(payload))

    def _request_json(self, url):
        try:
            response = requests.get(url, **self._request_kwargs())
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            if error.response is not None and error.response.status_code == 401:
                raise UserError(
                    _("OrangeHRM rechazo la consulta con 401 Unauthorized. Revise el tipo de autenticacion, token, usuario/contrasena o cookie de sesion configurada.")
                ) from error
            raise
        return response.json()

    def _extract_employee_list(self, payload):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and isinstance(data.get("employees"), list):
                return data["employees"]
            if isinstance(payload.get("employees"), list):
                return payload["employees"]
        raise UserError(_("OrangeHRM devolvio un JSON sin lista de empleados reconocible."))

    def _get_query_int(self, url, key):
        values = parse_qs(urlparse(url).query).get(key)
        if not values:
            return False
        try:
            return int(values[0])
        except (TypeError, ValueError):
            return False

    def _url_with_query(self, url, limit, offset):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query["limit"] = [str(limit)]
        query["offset"] = [str(offset)]
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    def _get_nested_value(self, values, paths):
        for path in paths:
            current = values
            for key in path.split("."):
                if not isinstance(current, dict):
                    current = None
                    break
                current = current.get(key)
            if current not in (None, "", False):
                if isinstance(current, (dict, list, tuple, set)):
                    continue
                return current
        return False

    def _extract_employee_values(self, employee_data):
        employee_id = self._get_nested_value(
            employee_data,
            ["empNumber", "employeeId", "id", "employee_id"],
        )
        employee_number = self._get_nested_value(
            employee_data,
            ["employeeId", "employeeNumber", "employee_number", "empNumber"],
        )
        first_name = self._get_nested_value(employee_data, ["firstName", "first_name"])
        middle_name = self._get_nested_value(employee_data, ["middleName", "middle_name"])
        last_name = self._get_nested_value(employee_data, ["lastName", "last_name"])
        full_name = self._get_nested_value(employee_data, ["name", "fullName", "full_name"])
        name_parts = [first_name, middle_name, last_name]
        name = full_name or " ".join(part.strip() for part in name_parts if part)
        job_title_id = self._get_nested_value(employee_data, ["jobTitle.id", "job_title_id"])
        subunit_id = self._get_nested_value(employee_data, ["subunit.id", "subunit_id"])
        subunit_name = self._get_nested_value(employee_data, ["subunit.name", "subunit_name"])
        job_title = self._get_nested_value(
            employee_data,
            ["jobTitle.title", "jobTitle.name", "job_title", "jobTitle", "jobSpecification.title"],
        )
        employment_status = self._get_nested_value(
            employee_data,
            ["empStatus.name", "employmentStatus.name", "employmentStatus.title", "employment_status", "employeeStatus"],
        )
        termination_id = self._get_nested_value(employee_data, ["terminationId", "termination_id"])
        return {
            "orangehrm_employee_id": str(employee_id) if employee_id else False,
            "orangehrm_employee_number": str(employee_number) if employee_number else False,
            "name": name or _("Empleado OrangeHRM %s") % (employee_id or employee_number or ""),
            "orangehrm_job_title_id": job_title_id or False,
            "orangehrm_job_title": job_title or False,
            "orangehrm_subunit_id": subunit_id or False,
            "orangehrm_subunit_name": subunit_name or False,
            "orangehrm_employment_status": employment_status or False,
            "orangehrm_termination_id": str(termination_id) if termination_id else False,
            "work_email": self._get_nested_value(
                employee_data,
                ["workEmail", "work_email", "email", "empWorkEmail"],
            ),
            "work_phone": self._get_nested_value(
                employee_data,
                ["workTelephone", "work_phone", "mobile", "empMobile", "telephone"],
            ),
            "identification_id": self._get_nested_value(
                employee_data,
                ["identificationId", "identification_id", "nationalId", "otherId", "ssnNumber"],
            ),
        }

    def _title_matches(self, job_title, field_name):
        titles = self._title_set(field_name)
        return any(title == job_title or title in job_title for title in titles)

    def _classify_role(self, values):
        job_title = self._normalize_text(values.get("orangehrm_job_title"))
        if job_title and self._title_matches(job_title, "driver_job_titles"):
            return "fleet_driver"
        if job_title and self._title_matches(job_title, "salesperson_job_titles"):
            return "salesperson"
        return "employee"

    def _infer_driver_type(self, job_title):
        normalized = self._normalize_text(job_title)
        if "interno" in normalized:
            return "interno"
        if "externo" in normalized:
            return "externo"
        return "no_definido"

    def _find_employee(self, values):
        Employee = self.env["hr.employee"].sudo()
        if values.get("orangehrm_employee_id"):
            employee = Employee.search(
                [("orangehrm_employee_id", "=", values["orangehrm_employee_id"])],
                limit=1,
            )
            if employee:
                return employee
        if values.get("identification_id") and "identification_id" in Employee._fields:
            employee = Employee.search(
                [("identification_id", "=", values["identification_id"])],
                limit=1,
            )
            if employee:
                return employee
        if values.get("work_email") and "work_email" in Employee._fields:
            employee = Employee.search(
                [("work_email", "=", values["work_email"])],
                limit=1,
            )
            if employee:
                return employee
        return Employee.browse()

    def _sync_departments(self):
        departments_data = self._fetch_subunits()
        Department = self.env["hr.department"].sudo()
        by_orangehrm_id = {}
        for department_data in departments_data:
            orangehrm_id = department_data.get("id")
            name = department_data.get("name")
            if not orangehrm_id or not name:
                continue
            parent = by_orangehrm_id.get(department_data.get("parent_orangehrm_id"))
            department = Department.search([("orangehrm_subunit_id", "=", int(orangehrm_id))], limit=1)
            if not department:
                department = Department.search([("name", "=", name), ("parent_id", "=", parent.id if parent else False)], limit=1)
            values = {
                "name": name,
                "parent_id": parent.id if parent else False,
            }
            if "orangehrm_subunit_id" in Department._fields:
                values["orangehrm_subunit_id"] = int(orangehrm_id)
            if "orangehrm_unit_id" in Department._fields:
                values["orangehrm_unit_id"] = department_data.get("unitId") or False
            if "orangehrm_level" in Department._fields:
                values["orangehrm_level"] = department_data.get("level") or 0
            if department:
                department.write(values)
            else:
                department = Department.create(values)
            by_orangehrm_id[orangehrm_id] = department
        return by_orangehrm_id

    def _sync_job_titles(self):
        job_titles = self._fetch_job_titles()
        for job_title in job_titles:
            self._ensure_hr_job(
                {
                    "orangehrm_job_title_id": job_title.get("id"),
                    "orangehrm_job_title": job_title.get("title"),
                    "orangehrm_job_description": job_title.get("description"),
                }
            )
        return job_titles

    def _ensure_hr_job(self, values):
        job_title = values.get("orangehrm_job_title")
        if not job_title:
            return False
        Job = self.env["hr.job"].sudo()
        job_title_id = values.get("orangehrm_job_title_id")
        job = Job.browse()
        if job_title_id and "orangehrm_job_title_id" in Job._fields:
            job = Job.search([("orangehrm_job_title_id", "=", int(job_title_id))], limit=1)
        if not job:
            job = Job.search([("name", "=", job_title)], limit=1)
        job_values = {"name": job_title}
        if job_title_id and "orangehrm_job_title_id" in Job._fields:
            job_values["orangehrm_job_title_id"] = int(job_title_id)
        if values.get("orangehrm_job_description") and "orangehrm_job_description" in Job._fields:
            job_values["orangehrm_job_description"] = values["orangehrm_job_description"]
        if values.get("orangehrm_job_description") and "description" in Job._fields:
            job_values["description"] = values["orangehrm_job_description"]
        if job:
            job.write(job_values)
        else:
            job = Job.create(job_values)
        return job

    def _prepare_employee_write_values(self, values, role):
        Employee = self.env["hr.employee"]
        job = self._ensure_hr_job(values)
        department = self._find_department(values)
        allowed_values = {
            key: value
            for key, value in values.items()
            if key in Employee._fields and value not in (False, None)
        }
        allowed_values.update(
            {
                "orangehrm_sync_role": role,
                "is_fleet_driver": role == "fleet_driver",
                "is_orangehrm_salesperson": role == "salesperson",
                "driver_type": self._infer_driver_type(values.get("orangehrm_job_title")) if role == "fleet_driver" else "no_definido",
                "orangehrm_last_sync_at": fields.Datetime.now(),
                "job_id": job.id if job and "job_id" in Employee._fields else False,
                "department_id": department.id if department and "department_id" in Employee._fields else False,
            }
        )
        return {key: value for key, value in allowed_values.items() if key in Employee._fields}

    def _find_department(self, values):
        Department = self.env["hr.department"].sudo()
        subunit_id = values.get("orangehrm_subunit_id")
        if subunit_id and "orangehrm_subunit_id" in Department._fields:
            department = Department.search([("orangehrm_subunit_id", "=", int(subunit_id))], limit=1)
            if department:
                return department
        if values.get("orangehrm_subunit_name"):
            department = Department.search([("name", "=", values["orangehrm_subunit_name"])], limit=1)
            if department:
                return department
        return Department.browse()

    def _ensure_work_contact(self, employee, values):
        if "work_contact_id" not in employee._fields:
            return
        partner_values = {
            "name": values.get("name") or employee.name,
            "email": values.get("work_email") or False,
            "phone": values.get("work_phone") or False,
        }
        partner_values = {key: value for key, value in partner_values.items() if value}
        if employee.work_contact_id:
            if partner_values:
                employee.work_contact_id.sudo().write(partner_values)
            return
        partner = self.env["res.partner"].sudo().create(partner_values or {"name": employee.name})
        employee.sudo().write({"work_contact_id": partner.id})

    def _sync_users(self):
        self.ensure_one()
        counters = {
            "total_read": 0,
            "total_employees": 0,
            "total_fleet_drivers": 0,
            "total_salespersons": 0,
            "total_created": 0,
            "total_updated": 0,
            "total_skipped": 0,
            "error_count": 0,
        }
        messages = []
        state = "success"
        try:
            self._sync_departments()
            self._sync_job_titles()
            employees_data = self._fetch_employees()
            counters["total_read"] = len(employees_data)
            for employee_data in employees_data:
                try:
                    if not isinstance(employee_data, dict):
                        counters["total_skipped"] += 1
                        continue
                    values = self._extract_employee_values(employee_data)
                    if values.get("orangehrm_termination_id") and not self.sync_terminated:
                        counters["total_skipped"] += 1
                        continue
                    if not values.get("orangehrm_employee_id") and not values.get("orangehrm_employee_number"):
                        counters["total_skipped"] += 1
                        messages.append(_("Empleado omitido porque no vino empNumber ni employeeId."))
                        continue
                    role = self._classify_role(values)
                    employee = self._find_employee(values)
                    write_values = self._prepare_employee_write_values(values, role)
                    if employee:
                        employee.write(write_values)
                        counters["total_updated"] += 1
                    else:
                        employee = self.env["hr.employee"].sudo().create(write_values)
                        counters["total_created"] += 1
                    self._ensure_work_contact(employee, values)
                    counters["total_employees"] += 1
                    if role == "fleet_driver":
                        counters["total_fleet_drivers"] += 1
                    elif role == "salesperson":
                        counters["total_salespersons"] += 1
                except Exception as error:
                    counters["error_count"] += 1
                    counters["total_skipped"] += 1
                    messages.append(str(error))
                    _logger.exception("Error sincronizando empleado OrangeHRM")
            if counters["error_count"]:
                state = "warning"
        except Exception as error:
            state = "error"
            counters["error_count"] += 1
            messages.append(str(error))
            _logger.exception("Error en sincronizacion OrangeHRM")

        message = self._build_sync_message(counters, messages)
        log = self.env["orangehrm.user.sync.log"].sudo().create(
            {
                "name": _("Sincronizacion OrangeHRM %s") % fields.Datetime.now(),
                "state": state,
                "message": message,
                **counters,
            }
        )
        self.write(
            {
                "last_sync_at": fields.Datetime.now(),
                "last_sync_status": state,
                "last_sync_message": message,
            }
        )
        return log

    def _build_sync_message(self, counters, messages):
        summary = _(
            "Consultados: %(total_read)s, empleados: %(total_employees)s, choferes: "
            "%(total_fleet_drivers)s, vendedores: %(total_salespersons)s, creados: "
            "%(total_created)s, actualizados: %(total_updated)s, omitidos: "
            "%(total_skipped)s, errores: %(error_count)s."
        ) % counters
        if messages:
            grouped_messages = Counter(str(message) for message in messages)
            detail = "\n".join(
                "%s%s" % (
                    message,
                    " (x%s)" % count if count > 1 else "",
                )
                for message, count in grouped_messages.most_common(10)
            )
            return "%s\n\nErrores:\n%s" % (summary, detail)
        return summary

    @api.model
    def cron_sync_active_configs(self):
        configs = self.search([("active", "=", True), ("frequency", "=", "daily")])
        for config in configs:
            config._sync_users()
