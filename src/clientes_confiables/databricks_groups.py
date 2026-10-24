"""Grupos de cuenta vía proxy SCIM del workspace; sin modificar miembros."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .project_config import load_config


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Nunca reenviar un Bearer a otro destino.


def scim_request(method, query="", payload=None):
    host = os.getenv("DATABRICKS_HOST", "").removeprefix("https://").rstrip("/")
    token = os.getenv("DATABRICKS_TOKEN")
    parsed = urlsplit("https://" + host)
    if not token or not host or parsed.path or parsed.query or parsed.username:
        raise ValueError("MISSING_DATABRICKS_SECRETS")
    url = f"https://{host}/api/2.0/account/scim/v2/Groups" + query
    request = Request(url, method=method,
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/scim+json"},
                      data=json.dumps(payload).encode("utf-8") if payload is not None else None)
    try:
        with build_opener(NoRedirects()).open(request, timeout=load_config()["socket_timeout_seconds"]) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code == 409:
            raise ValueError("GROUP_ALREADY_EXISTS") from None
        if error.code == 401:
            raise ValueError("GROUP_AUTHENTICATION_FAILED") from None
        if error.code == 403:
            raise ValueError("GROUP_PROVISIONING_DENIED") from None
        raise ValueError("GROUP_PROVISIONING_FAILED") from None
    except (URLError, ValueError, OSError):
        raise ValueError("GROUP_PROVISIONING_FAILED") from None


def find_group(name, request):
    query = "?" + urlencode({"filter": "displayName eq " + json.dumps(name)})
    result = request("GET", query)
    matches = [r for r in result.get("Resources", []) if r.get("displayName") == name]
    if len(matches) > 1:
        raise ValueError("AMBIGUOUS_ACCOUNT_GROUP")
    return matches[0] if matches else None


def ensure_account_groups(groups, request=None):
    request = request or scim_request
    for name in groups.values():
        existing = find_group(name, request)
        if existing:
            continue
        try:
            request("POST", payload={"displayName": name,
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"]})
        except ValueError as error:
            if str(error) != "GROUP_ALREADY_EXISTS":
                raise
        if not find_group(name, request):
            raise ValueError("ACCOUNT_GROUP_NOT_VERIFIED")
