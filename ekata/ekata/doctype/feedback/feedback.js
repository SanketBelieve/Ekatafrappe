// Copyright (c) 2025, kiran.c@indictrans.in and contributors
// For license information, please see license.txt

frappe.ui.form.on("Feedback", {
	refresh(frm) {
		frm.set_intro("⚠️ Kindly set Quantity (qty) properly before submitting the form.");
	}
});
