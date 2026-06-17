import base64
import functools
import hashlib
import hmac
import json
from typing import List

import frappe
from frappe import _
from shopify.resources import Webhook
from shopify.session import Session

from ecommerce_integrations.shopify.constants import (
	API_VERSION,
	EVENT_MAPPER,
	SETTING_DOCTYPE,
	WEBHOOK_EVENTS,
)
from ecommerce_integrations.shopify.utils import create_shopify_log




def validate_request(req, hmac_header):
    settings = frappe.get_doc(SETTING_DOCTYPE)
    secret_key = (
        settings.get_password("shared_secret", raise_exception=False)
        or settings.get_password("api_secret", raise_exception=False)
        or settings.get_password("client_secret", raise_exception=False)
    )
    if not secret_key:
        frappe.throw(_("Shopify Secret Key is missing"))
    payload = req.get_data(cache=False, as_text=False)
    computed_hmac = base64.b64encode(
        hmac.new(
            secret_key.encode("utf-8"),
            payload,
            hashlib.sha256
        ).digest()
    ).decode("utf-8")

    if not hmac.compare_digest(computed_hmac, hmac_header):
        create_shopify_log(
            status="Error",
            request_data=payload.decode("utf-8", errors="ignore"),
            response_data={
                "computed_hmac": computed_hmac,
                "received_hmac": hmac_header
            }
        )

        frappe.throw(_("Unverified Webhook Data"))

    return True