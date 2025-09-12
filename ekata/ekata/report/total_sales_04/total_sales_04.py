import frappe

def execute(filters=None):
    columns = [
        {"label": "Sales Category", "fieldname": "sales_category", "fieldtype": "Data", "width": 200},
        {"label": "Total Sales", "fieldname": "total_sales", "fieldtype": "Currency", "width": 200},
    ]

    conditions = []
    values = {}

    # Main filter (date range)
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("gle.posting_date BETWEEN %(from_date)s AND %(to_date)s")
        values["from_date"] = filters.get("from_date")
        values["to_date"] = filters.get("to_date")

    # Day filter
    if filters.get("day"):
        conditions.append("gle.posting_date = %(day)s")
        values["day"] = filters.get("day")

    # Week filter (ISO week number)
    if filters.get("week"):
        conditions.append("WEEK(gle.posting_date, 1) = %(week)s")
        values["week"] = filters.get("week")

    # Month filter
    if filters.get("month"):
        conditions.append("MONTHNAME(gle.posting_date) = %(month)s")
        values["month"] = filters.get("month")

    # Fiscal Year filter
    if filters.get("fiscal_year"):
        fy = frappe.db.get_value("Fiscal Year", filters.get("fiscal_year"), ["year_start_date", "year_end_date"], as_dict=1)
        if fy:
            conditions.append("gle.posting_date BETWEEN %(fy_start)s AND %(fy_end)s")
            values["fy_start"] = fy.year_start_date
            values["fy_end"] = fy.year_end_date

    condition_str = " AND ".join(conditions) if conditions else "1=1"

    data = frappe.db.sql(f"""
        SELECT
          CASE
            WHEN gle.account = 'Export Sales (Karnataka) - EEPL' THEN 'International Sales'
            WHEN gle.account = 'Local Sales Karnataka - EEPL' THEN 'Local Sales'
            WHEN gle.account = 'Roasted Sales Karnataka - EEPL' THEN 'Roasted Coffee Sales'
            WHEN gle.account = 'Q Course Sales - EEPL' THEN 'CQI Sales'
            WHEN gle.account = 'Sample Sales - EEPL' THEN 'Sample Sales'
            ELSE 'Other'
          END AS sales_category,
          SUM(gle.credit - gle.debit) AS total_sales
        FROM `tabGL Entry` gle
        WHERE gle.docstatus = 1
          AND {condition_str}
          AND gle.account IN (
            'Export Sales (Karnataka) - EEPL',
            'Local Sales Karnataka - EEPL',
            'Roasted Sales Karnataka - EEPL',
            'Q Course Sales - EEPL',
            'Sample Sales - EEPL'
          )
        GROUP BY 1
        ORDER BY 2 DESC
    """, values, as_dict=1)

    return columns, data
