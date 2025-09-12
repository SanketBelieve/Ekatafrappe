// Copyright (c) 2025, kiran.c@indictrans.in and contributors
// For license information, please see license.txt

frappe.query_reports["Account payables report"] = {
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
		  "fieldname": "supplier_group",
		  "label": "Supplier Group",
		  "fieldtype": "Link",
		  "options": "Supplier Group"
		}
	  ]
	  
};
