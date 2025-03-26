import frappe

def validate(self,method = None):

    pass
    # if self.naming_series == "EEPL/PI/.##./.FY.":
        
        # if not frappe.db.exists('Sales Order', 'EEPL/PI/01/22-23'):
        #     self.name = "EEPL/PI/01/22-23"
        #     frappe.db.sql("update `tabSeries` set current=01 where name = 'EEPL/PI/'")


def after_insert(doc, method):
    if not doc.items:
        return

    quotation_name = doc.items[0].prevdoc_docname
    
    if not quotation_name:
        return

    quotation = frappe.get_doc("Quotation", quotation_name)

    doc.custom_opportunity_category = quotation.custom_opportunity_category
    doc.custom_opportunity_purpose = quotation.custom_purpose
    doc.custom_lead_type = quotation.custom_lead_type


    doc.save(ignore_permissions=True)
