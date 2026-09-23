#!/usr/bin/env bash
# A server generated straight from an OpenAPI spec: one tool per endpoint,
# descriptions taken from the spec's summaries, several of them near-identical.
set -euo pipefail

cat > server.py <<'PY'
"""Generated from openapi.json. Do not edit by hand."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("acme-api")
PY

emit() {  # emit <name> <summary>
  cat >> server.py <<PY


@mcp.tool()
def $1(**params) -> dict:
    """$2"""
    return call("$1", params)
PY
}

emit get_user "Get user"
emit get_user_profile "Get user profile"
emit get_user_details "Retrieve user details"
emit list_users "List users"
emit search_users "Search users"
emit create_user "Create user"
emit update_user "Update user"
emit patch_user "Patch user"
emit delete_user "Delete user"
emit get_order "Get order"
emit get_order_lines "Get order lines"
emit get_order_status "Get order status"
emit list_orders "List orders"
emit search_orders "Search orders"
emit create_order "Create order"
emit update_order "Update order"
emit cancel_order "Cancel order"
emit get_invoice "Get invoice"
emit get_invoice_pdf "Get invoice PDF"
emit list_invoices "List invoices"
emit create_invoice "Create invoice"
emit void_invoice "Void invoice"
emit get_payment "Get payment"
emit list_payments "List payments"
emit create_payment "Create payment"
emit refund_payment "Refund payment"
emit get_subscription "Get subscription"
emit list_subscriptions "List subscriptions"
emit create_subscription "Create subscription"
emit cancel_subscription "Cancel subscription"
emit pause_subscription "Pause subscription"
emit resume_subscription "Resume subscription"
emit get_product "Get product"
emit list_products "List products"
emit search_products "Search products"
emit create_product "Create product"
emit update_product "Update product"
emit archive_product "Archive product"
emit get_price "Get price"
emit list_prices "List prices"
emit create_price "Create price"
emit get_customer "Get customer"
emit get_customer_addresses "Get customer addresses"
emit list_customers "List customers"
emit search_customers "Search customers"
emit create_customer "Create customer"
emit update_customer "Update customer"
emit get_shipment "Get shipment"
emit list_shipments "List shipments"
emit create_shipment "Create shipment"
emit track_shipment "Track shipment"
emit get_return "Get return"
emit list_returns "List returns"
emit create_return "Create return"
emit approve_return "Approve return"
emit get_webhook "Get webhook"
emit list_webhooks "List webhooks"
emit create_webhook "Create webhook"
emit delete_webhook "Delete webhook"
emit get_report "Get report"
emit run_report "Run report"
emit list_reports "List reports"
emit get_audit_log "Get audit log"

cat >> server.py <<'PY'


def call(operation, params):
    """Forward the call to the REST API."""
    raise NotImplementedError(operation)
PY

git init -q -b main .
git config user.email eval@example.invalid
git config user.name "Eval Fixture"
git config core.autocrlf false
git add -A
git commit -q -m "Generated MCP server"
