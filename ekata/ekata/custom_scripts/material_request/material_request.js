frappe.ui.form.on('Material Request', {
    onload(frm) {
        if (frm.is_new() && frm.doc.amended_from) {
            frappe.db.get_value(
                "Material Request",
                frm.doc.amended_from,
                "transaction_date",
                (r) => {
                    if (r && r.transaction_date) {
                        frm.set_value("transaction_date", r.transaction_date);
                    }
                }
            );
        }
    },
    supplier : function(frm){
        frm.clear_table('supplier_table');
        refresh_field('supplier_table');
        let rd = frm.add_child("supplier_table");
        rd.supplier = frm.doc.supplier
        refresh_field('supplier_table')
    }
    
});
