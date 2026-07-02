import requests

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from odoo import _, models
from odoo.exceptions import UserError


class OrangeHrmApi(models.AbstractModel):
    _name = "orangehrm.api"
    _description = "Cliente API OrangeHRM"

    EMPLOYEES_ENDPOINT = "/web/index.php/api/v2/pim/employees?limit=50&offset=0&model=detailed&includeEmployees=onlyCurrent&sortField=employee.firstName&sortOrder=ASC"
    JOB_TITLES_ENDPOINT = "/web/index.php/api/v2/admin/job-titles?limit=50&offset=0&sortField=jt.jobTitleName&sortOrder=ASC"
    SUBUNITS_ENDPOINT = "/web/index.php/api/v2/admin/subunits?mode=tree"

    def build_url(self, config, endpoint):
        if not config.orangehrm_base_url:
            raise UserError(_("Configure la URL base de OrangeHRM."))
        if not endpoint:
            raise UserError(_("Configure el endpoint de OrangeHRM."))
        base_url = config.orangehrm_base_url.strip()
        if not base_url.startswith(("http://", "https://")):
            base_url = "http://%s" % base_url
        return "%s/%s" % (base_url.rstrip("/"), endpoint.lstrip("/"))

    def request_kwargs(self, config):
        headers = {"Accept": "application/json"}
        kwargs = {
            "headers": headers,
            "timeout": config.timeout or 30,
        }
        if config.auth_type == "bearer" and config.password:
            headers["Authorization"] = "Bearer %s" % config.password
        elif config.auth_type == "api_key" and config.password:
            headers[config.api_key_header or "X-API-Key"] = config.password
        elif config.auth_type == "basic":
            kwargs["auth"] = (config.username or "", config.password or "")
        elif config.auth_type == "cookie" and config.password:
            headers["Cookie"] = config.password
        return kwargs

    def request_json(self, config, endpoint):
        url = self.build_url(config, endpoint)
        try:
            response = requests.get(url, **self.request_kwargs(config))
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            if error.response is not None and error.response.status_code == 401:
                raise UserError(
                    _("OrangeHRM rechazo la consulta con 401 Unauthorized. Revise autenticacion, token, usuario/contrasena o cookie de sesion.")
                ) from error
            raise
        return response.json()

    def request_paginated(self, config, endpoint):
        url = self.build_url(config, endpoint)
        payload = self._request_url(config, url)
        records = self.extract_data_list(payload)
        if not isinstance(payload, dict):
            return records

        total = payload.get("meta", {}).get("total")
        if not total or len(records) >= total:
            return records

        limit = self._get_query_int(url, "limit") or len(records) or 50
        offset = self._get_query_int(url, "offset") or 0
        while len(records) < total:
            offset += limit
            page_payload = self._request_url(config, self._url_with_query(url, limit, offset))
            page_records = self.extract_data_list(page_payload)
            if not page_records:
                break
            records.extend(page_records)
        return records

    def extract_data_list(self, payload):
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
        raise UserError(_("OrangeHRM devolvio un JSON sin lista de datos reconocible."))

    def flatten_tree(self, records, parent_id=False):
        flattened = []
        for record in records:
            if not isinstance(record, dict):
                continue
            children = record.get("children") or []
            current = dict(record)
            current.pop("children", None)
            current["parent_orangehrm_id"] = parent_id
            flattened.append(current)
            flattened.extend(self.flatten_tree(children, record.get("id")))
        return flattened

    def _request_url(self, config, url):
        try:
            response = requests.get(url, **self.request_kwargs(config))
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            if error.response is not None and error.response.status_code == 401:
                raise UserError(
                    _("OrangeHRM rechazo la consulta con 401 Unauthorized. Revise autenticacion, token, usuario/contrasena o cookie de sesion.")
                ) from error
            raise
        return response.json()

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
