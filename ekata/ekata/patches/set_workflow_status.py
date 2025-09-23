import frappe
def execute():
    try:
        purchase_receipts = frappe.get_all(
                "Purchase Receipt",
                filters={"workflow_state": ["is", "set"]},
                fields=["name", "workflow_state"]
        )
        for pr in purchase_receipts:
            frappe.db.set_value(
                "Purchase Receipt",
                pr.name,
                "custom_workflow_status",
                pr.workflow_state
            )

        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            message=f"Patch failed: {str(e)}",
            title="Purchase Receipt Patch Fatal Error"
        )