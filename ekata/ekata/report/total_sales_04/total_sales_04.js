// Copyright (c) 2025, kiran.c@indictrans.in and contributors
// For license information, please see license.txt

frappe.query_reports["Total Sales-04"] = {
	
		"filters": [
		 {
		  "fieldname": "from_date",
		  "label": "From Date",
		  "fieldtype": "Date",
		  "default": "2024-04-01",
		  "reqd": 1
		 },
		 {
		  "fieldname": "to_date",
		  "label": "To Date",
		  "fieldtype": "Date",
		  "default": "Today",
		  "reqd": 1
		 },
		 {
		  "fieldname": "day",
		  "label": "Day",
		  "fieldtype": "Date",
		  "reqd": 0
		 },
		 {
		  "fieldname": "week",
		  "label": "Week",
		  "fieldtype": "Select",
		  "options": "\n1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n13\n14\n15\n16\n17\n18\n19\n20\n21\n22\n23\n24\n25\n26\n27\n28\n29\n30\n31\n32\n33\n34\n35\n36\n37\n38\n39\n40\n41\n42\n43\n44\n45\n46\n47\n48\n49\n50\n51\n52",
		  "reqd": 0
		 },
		 {
		  "fieldname": "month",
		  "label": "Month",
		  "fieldtype": "Select",
		  "options": "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
		  "reqd": 0
		 },
		 {
		  "fieldname": "fiscal_year",
		  "label": "Fiscal Year",
		  "fieldtype": "Link",
		  "options": "Fiscal Year",
		  "reqd": 0
		 }
		]
	   }
	   
	
