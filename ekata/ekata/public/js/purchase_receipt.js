frappe.ui.form.on("Purchase Receipt", {
    refresh: function(frm) {
        frm.add_custom_button(__('View Custom Stock Ledger'), function(){
           frappe.set_route("query-report", "Custom Stock Ledger", {
                "voucher_no": frm.doc.name,
                "receipt_no": frm.doc.lot_no
            });
        });
    },
    validate:function(frm){
        if (frm.is_new() && frm.doc.workflow_state){
            frm.set_value("custom_workflow_status",frm.doc.workflow_state);
        }
    },
    after_workflow_action:function(frm){
        if (frm.doc.workflow_state){
            frappe.call({
                method:"ekata.ekata.custom_scripts.purchase_receipt.purchase_receipt_py.update_workflow_status",
                args: {
                    docname : frm.doc.name,
                    workflow_state: frm.doc.workflow_state
                },
                callback:function(r){
                    cur_frm.reload_doc()
                }
            })
        }
    }
});
frappe.ui.form.on("Purchase Receipt Item", {
    qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.qty && row.bag_category){
            console.log(">>>> in kgs >>>>");
            frappe.call({
                method: 'ekata.ekata.custom_scripts.purchase_receipt.purchase_receipt_py.get_no_of_bags',
                args: {
                    qty : row.qty,
                    bag_cat : row.bag_category,
                },
                callback: function(r) {
                    console.log(">>>>",r.message);
                    if(r.message){
                        row.bags = r.message
                        frm.refresh_field('items');
                    }
                }
            });
        }
    },
    bag_category: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.qty && row.bag_category){
            console.log(">>>> in bag category >>>>");
            frappe.call({
                method: 'ekata.ekata.custom_scripts.purchase_receipt.purchase_receipt_py.get_no_of_bags',
                args: {
                    qty : row.qty,
                    bag_cat : row.bag_category,
                },
                callback: function(r) {
                    console.log(">>>>",r.message);
                    if(r.message){
                        row.bags = r.message
                        frm.refresh_field('items');
                    }
                }
            });
        }
    }
});




