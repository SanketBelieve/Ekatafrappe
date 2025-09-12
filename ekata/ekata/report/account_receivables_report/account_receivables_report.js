// Copyright (c) 2025, kiran.c@indictrans.in and contributors
// For license information, please see license.txt

frappe.query_reports["Account Receivables Report"] = {
	"filters": [
		{
		  "fieldname": "from_date",
		  "label": "From Date",
		  "fieldtype": "Date",
		  "reqd": 1
		},
		{
		  "fieldname": "to_date",
		  "label": "To Date",
		  "fieldtype": "Date",
		  "reqd": 1
		},
		{
		  "fieldname": "customer_group",
		  "label": "Customer Group",
		  "fieldtype": "Link",
		  "options": "Customer Group"
		}
	  ]
	  
};
