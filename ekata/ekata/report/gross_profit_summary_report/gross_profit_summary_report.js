// Copyright (c) 2025, kiran.c@indictrans.in and contributors
// For license information, please see license.txt
frappe.query_reports["Gross Profit Summary Report"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2],
			reqd: 1,
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: "Monthly",
			default: "Monthly",
		},
		{
			"fieldname": "show_total_only",
			"label": "Show Total Only",
			"fieldtype": "Check"
		}
		
		
	],
	// tree: true,
	// name_field: "parent",
	// parent_field: "parent_invoice",
	// initial_depth: 3,
	// formatter: function (value, row, column, data, default_formatter) {
	// 	if (column.fieldname == "sales_invoice" && column.options == "Item" && data && data.indent == 0) {
	// 		column._options = "Sales Invoice";
	// 	} else {
	// 		column._options = "";
	// 	}
	// 	value = default_formatter(value, row, column, data);

	// 	if (data && (data.indent == 0.0 || (row[1] && row[1].content == "Total"))) {
	// 		value = $(`<span>${value}</span>`);
	// 		var $value = $(value).css("font-weight", "bold");
	// 		value = $value.wrap("<p></p>").parent().html();
	// 	}

	// 	return value;
	// },
};

// erpnext.utils.add_dimensions("Gross Profit", 15);
