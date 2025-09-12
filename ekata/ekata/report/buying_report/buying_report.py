import frappe

DIRECT_ACCOUNTS = [
    'Direct Expenses - EEPL',
    'Bag Printing - EEPL',
    'Bulking Charge - EEPL',
    'CQI Expenses - EEPL',
    'Clean Coffee Colour Sorting - EEPL',
    'Courier Charges - EEPL',
    'Cupping Expense - EEPL',
    'Curing Charges - EEPL',
    'Drying Charges - EEPL',
    'Frieght - EEPL',
    'GAS (LPG) - EEPL',
    'Garbling Charges - EEPL',
    'Grading Charges - EEPL',
    'Handling Charges - EEPL',
    'Insurance - EEPL',
    'International Logistics - EEPL',
    'Loading & Unloading Charges - EEPL',
    'Packing Material - EEPL',
    'Packing and Loading Charges - EEPL',
    'Project Expenses - Arakku Valley - EEPL',
    'Quality Expenses - EEPL',
    'Sampling Expenses - EEPL',
    'Transportation - EEPL',
    'Warehousing Charges - EEPL'
]

def execute(filters=None):
    filters = filters or {}

    # Default Dates
    from_date = filters.get("from_date") or "2024-01-01"
    to_date = filters.get("to_date") or frappe.utils.today()

    # Conditions
    conditions = ""
    if filters.get("buying_category") == "Direct Buying":
        conditions += " AND gle.account IN ({})".format(
            ",".join([f"'{a}'" for a in DIRECT_ACCOUNTS])
        )
    elif filters.get("buying_category") == "Indirect Buying":
        conditions += " AND gle.account NOT IN ({})".format(
            ",".join([f"'{a}'" for a in DIRECT_ACCOUNTS])
        )

    # Show Detail
    if filters.get("show_detail"):
        query = f"""
            SELECT
                gle.account AS account,
                CASE
                    WHEN gle.account IN ({",".join([f"'{a}'" for a in DIRECT_ACCOUNTS])})
                        THEN 'Direct Buying'
                    ELSE 'Indirect Buying'
                END AS buying_category,
                SUM(gle.debit - gle.credit) AS amount
            FROM `tabGL Entry` gle
            JOIN `tabAccount` acc ON gle.account = acc.name
            WHERE gle.docstatus = 1
              AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
              AND acc.root_type = 'Expense'
              {conditions}
            GROUP BY gle.account
            ORDER BY amount DESC
        """
        columns = [
            {"label": "Account", "fieldname": "account", "fieldtype": "Data", "width": 300},
            {"label": "Buying Category", "fieldname": "buying_category", "fieldtype": "Data", "width": 200},
            {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 200},
        ]
    else:
        query = f"""
            SELECT
                CASE
                    WHEN gle.account IN ({",".join([f"'{a}'" for a in DIRECT_ACCOUNTS])})
                        THEN 'Direct Buying'
                    ELSE 'Indirect Buying'
                END AS buying_category,
                SUM(gle.debit - gle.credit) AS total_buying
            FROM `tabGL Entry` gle
            JOIN `tabAccount` acc ON gle.account = acc.name
            WHERE gle.docstatus = 1
              AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
              AND acc.root_type = 'Expense'
              {conditions}
            GROUP BY buying_category
            ORDER BY total_buying DESC
        """
        columns = [
            {"label": "Buying Category", "fieldname": "buying_category", "fieldtype": "Data", "width": 200},
            {"label": "Total Buying", "fieldname": "total_buying", "fieldtype": "Currency", "width": 200},
        ]

    data = frappe.db.sql(query, {"from_date": from_date, "to_date": to_date}, as_dict=True)
    return columns, data
