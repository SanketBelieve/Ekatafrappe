import frappe


def execute(filters=None):
    filters = filters or {}

    # 1. build WHERE clauses
    conditions = ["ts.docstatus = 1"]
    if filters.get("employee"):
        conditions.append("ts.employee = %(employee)s")
    if filters.get("from_datetime"):
        conditions.append("td.from_time >= %(from_datetime)s")
    if filters.get("to_datetime"):
        conditions.append("td.to_time <= %(to_datetime)s")

    where_clause = " AND ".join(conditions)

    # 2. pull data (note: correct doctype table names, no posting_date)
    data = frappe.db.sql(
        f"""
        SELECT
            ts.name                       AS timesheet,
            ts.employee                   AS employee,
            ts.custom_designation         AS custom_designation,
            td.activity_type              AS activity_type,
            td.from_time                  AS from_time,
            td.to_time                    AS to_time,
            td.custom_expected_to_time    AS expected_to_time,

            /* compute delay in hours */
            CASE
              WHEN td.to_time > td.custom_expected_to_time THEN
                ROUND(
                  TIMESTAMPDIFF(
                    SECOND,
                    td.custom_expected_to_time,
                    td.to_time
                  ) / 3600
                , 2)
              ELSE 0
            END                            AS custom_delay,

            td.custom_remarks             AS custom_remarks,
            td.custom_impact              AS custom_impact,
            td.custom_status              AS custom_status,
            td.completed                  AS completed

        FROM `tabTimesheet Detail` td
        JOIN `tabTimesheet` ts
          ON ts.name = td.parent
        WHERE {where_clause}
        ORDER BY
          td.from_time,
          ts.name,
          td.idx
    """,
        filters,
        as_dict=True,
    )

    # 3. define your columns
    columns = [
        {
            "label": "Timesheet",
            "fieldname": "timesheet",
            "fieldtype": "Link",
            "options": "Timesheet",
            "width": 120,
        },
        {
            "label": "Employee",
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120,
        },
        {
            "label": "Employee Designation",
            "fieldname": "custom_designation",
            "fieldtype": "Link",
            "options": "Designation",
            "width": 120,
        },
        {
            "label": "Activity Type",
            "fieldname": "activity_type",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "From Time",
            "fieldname": "from_time",
            "fieldtype": "Datetime",
            "width": 140,
        },
        {
            "label": "To Time",
            "fieldname": "to_time",
            "fieldtype": "Datetime",
            "width": 140,
        },
        {
            "label": "Expected End",
            "fieldname": "expected_to_time",
            "fieldtype": "Datetime",
            "width": 140,
        },
        {
            "label": "Delay (hrs)",
            "fieldname": "custom_delay",
            "fieldtype": "Float",
            "width": 80,
        },
        {
            "label": "Remarks",
            "fieldname": "custom_remarks",
            "fieldtype": "Text",
            "width": 200,
        },
        {
            "label": "Impact",
            "fieldname": "custom_impact",
            "fieldtype": "Text",
            "width": 200,
        },
        {
            "label": "Status",
            "fieldname": "custom_status",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Completed",
            "fieldname": "completed",
            "fieldtype": "Check",
            "width": 80,
        },
    ]

    return columns, data
