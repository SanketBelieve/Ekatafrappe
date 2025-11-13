frappe.ui.form.on('Quotation',{
    
    refresh(frm) {
        // Check if Quotation is Approved
        setTimeout(() => {
            if (frm.doc.workflow_state === "Approved from customer"){
                 {
                frm.remove_custom_button('Sales Order', 'Create');
                
            }}
        }, 500); 
    },

    workflow_state(frm) {
        // Trigger refresh when workflow changes
        frm.trigger('refresh');
    }
});
