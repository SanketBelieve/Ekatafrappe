frappe.query_reports["Net Profit"] = {
    "filters": [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -12)
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "account_type",
            label: __("Account Type"),
            fieldtype: "MultiSelectList",
            options: [
                { value: "Income", description: "Income" },
                { value: "Expense", description: "Expense" },
                { value: "Net Profit", description: "Net Profit" }
            ],
            default: ["Income", "Expense", "Net Profit"]
        }
    ]
};
