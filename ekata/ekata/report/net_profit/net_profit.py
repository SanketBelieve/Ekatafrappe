import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import (
	get_data,
	get_period_list,
)


def execute(filters=None):
    if not filters.company:
        frappe.throw(_("Company is mandatory"))
    if not filters.from_date or not filters.to_date:
        frappe.throw(_("From Date and To Date are mandatory"))

    # Ensure account_type is always a list
    selected_accounts = filters.get("account_type") or []
    if isinstance(selected_accounts, str):  
        selected_accounts = [selected_accounts]
    
    if not selected_accounts:
        selected_accounts = ["Income", "Expense", "Net Profit"]

    period_list = get_period_list(
        None,
        None,
        filters.from_date,
        filters.to_date,
        "Date Range",
        "Yearly",
        company=filters.company,
    )

    income = get_data(
        filters.company,
        "Income",
        "Credit",
        period_list,
        filters=filters,
        accumulated_values=0,
        ignore_closing_entries=True,
    )

    expense = get_data(
        filters.company,
        "Expense",
        "Debit",
        period_list,
        filters=filters,
        accumulated_values=0,
        ignore_closing_entries=True,
    )

    net_profit_loss = get_net_profit_loss(income, expense, period_list, filters.company)

    data = []

    if "Income" in selected_accounts and income:
        data.append({
            "account_name": _("Total Income"),
            "account": "Income",
            "amount": income[-2]["total"]
        })

    if "Expense" in selected_accounts and expense:
        data.append({
            "account_name": _("Total Expense"),
            "account": "Expense",
            "amount": expense[-2]["total"]
        })

    if "Net Profit" in selected_accounts and net_profit_loss:
        data.append({
            "account_name": _("Profit for the Year"),
            "account": "Net Profit",
            "amount": net_profit_loss["total"]
        })

    columns = [
        {"fieldname": "account_name", "label": _("Name"), "fieldtype": "Data", "width": 250},
        {"fieldname": "account", "label": _("Account"), "fieldtype": "Data", "width": 150},
        {"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 150},
    ]

    return columns, data

def get_net_profit_loss(income, expense, period_list, company, currency=None):
	total_income = flt(income[-2]["total"], 3) if income else 0
	total_expense = flt(expense[-2]["total"], 3) if expense else 0
	net_profit = total_income - total_expense

	return {
		"account_name": _("Profit for the Year"),
		"account": "Net Profit",
		"amount": net_profit,
		"total": net_profit,
		"currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
	}
