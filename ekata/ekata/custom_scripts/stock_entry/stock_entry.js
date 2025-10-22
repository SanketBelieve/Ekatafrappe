frappe.ui.form.on('Stock Entry', {
   refresh: function(frm) {
        frm.add_custom_button(__("Custom Stock Ledger"), function() {
                frappe.route_options = {
                    voucher_no: frm.doc.name,
                };
                frappe.set_route("query-report", "Custom Stock Ledger");
        }, __(""));
        frm.add_custom_button(__("Create Repack"), function() {
            frappe.model.open_mapped_doc({
                method: "ekata.ekata.custom_scripts.stock_entry.stock_entry.create_repack_entry",
                frm: frm,
                args: {
                    doc: frm.doc
                },
                run_link_triggers: true
            });
        }, __(""));

        if(frm.doc.docstatus > 0) {
            setTimeout(() => {
                frm.remove_custom_button('Stock Ledger', 'View');
                }, 10);

            cur_frm.add_custom_button(__("New Stock Ledger"), function() {
                frappe.route_options = {
                    voucher_no: frm.doc.name,
                    from_date: frm.doc.posting_date,
                    to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
                    company: frm.doc.company,
                    show_cancelled_entries: frm.doc.docstatus === 2
                };
                frappe.set_route("query-report", "New Stock Ledger");
            }, __("View"));
        }

   },

   validate: function(frm){
        if(frm.doc.stock_entry_type == 'Repack' || frm.doc.stock_entry_type == 'Bulking'){
            if (frm.doc.items && frm.doc.items.length) {
                var fg_per = 0;
                $.each(frm.doc.items || [], function(i, item) {
                    if (!item.is_finished_item && !item.is_scrap_item && !item.custom_is_process_loss) {
                        console.log(item.qty);
                    } else {
                        console.log(fg_per);
                        fg_per += item.fg_percentage;
                    }
                });
                if (fg_per < 100) {
                    frappe.throw('FG Percentage should be 100%');
                }
            }
        }

        if (frm.doc.outturn_no) {
            frm.events.updateItems(frm, 'outturn_no', frm.doc.outturn_no);
        }
        if (frm.doc.lot_no) {
            frm.events.updateItems(frm, 'receipt_no', frm.doc.lot_no);
        }
        if (frm.is_new() && frm.doc.workflow_state){
            frm.set_value("custom_workflow_status",frm.doc.workflow_state);
        }
   },
   
   updateItems: function(frm, field, value) {
        if (frm.doc.items && frm.doc.items.length) {
            let doctype = frm.doc.items[0].doctype;
            $.each(frm.doc.items || [], function(i, item) {
                frappe.model.set_value(doctype, item.name, field, value);
            });
        }
   },

   outturn_no: function(frm) {
        if (frm.doc.outturn_no) {
            frm.events.updateItems(frm, 'outturn_no', frm.doc.outturn_no);
        }
   },

   lot_no: function(frm) {
        if (frm.doc.lot_no) {
            frm.events.updateItems(frm, 'receipt_no', frm.doc.lot_no);
        }
   },
    stock_entry_type: function(frm) {
        // Copy value from stock_entry_type to stock_type
        frm.set_value('custom_stock_type', frm.doc.stock_entry_type);
    },
    after_workflow_action:function(frm){
        if (frm.doc.workflow_state){
            frappe.call({
                method:"ekata.ekata.custom_scripts.stock_entry.stock_entry.update_workflow_status",
                args: {
                    docname : frm.doc.name,
                    workflow_state: frm.doc.workflow_state
                },
                callback:function(r){
                    cur_frm.reload_doc()
                }
            })
        }
    },
    custom_stock_type: function(frm) {
        update_kanban_group(frm);
    },
    custom_workflow_status: function(frm) {
        update_kanban_group(frm);
    }
});

frappe.ui.form.on('Stock Entry Detail',{
    fg_percentage: function(frm,cdt,cdn){
        var row = locals[cdt][cdn];
        var rm_qty = 0
        var fg_per = 0
        var fg_qty = 0
        if (frm.doc.items && frm.doc.items.length) {
            $.each(frm.doc.items || [], function(i, item) {
                if (!item.is_finished_item && !item.is_scrap_item && !item.custom_is_process_loss)
                {
                    console.log(item.outturn_qty)
                    rm_qty += item.outturn_qty;
                }else{
                    console.log(item.fg_percentage)
                    fg_per += item.fg_percentage;
                }
            });
        }
        console.log('row qty',rm_qty,'fg per', fg_per)
        if (fg_per <= 100 ){
            var fg_qty = (rm_qty * row.fg_percentage) / 100
            fg_qty = Math.round(fg_qty);
            frappe.model.set_value(cdt, cdn, 'qty', fg_qty)
        }else{
            frappe.model.set_value(cdt, cdn, 'fg_percentage', 0)
            frappe.model.set_value(cdt, cdn, 'qty', 0)
            frappe.throw('FG Percentage cannot be greater than 100%');
        }
    }
});

function update_kanban_group(frm) {
    // Get current values
    let stockType = frm.doc.custom_stock_type || '';
    let workflow = frm.doc.custom_workflow_status || 'Not Started';

    // Combine values
    let combinedValue = `${stockType} - ${workflow}`;

    // Dynamically set options for Select field
    let options = [combinedValue];
    frm.set_df_property('custom_kanban_group', 'options', options);

    // Set the field value
    frm.set_value('custom_kanban_group', combinedValue);
}