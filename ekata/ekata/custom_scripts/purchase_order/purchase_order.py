import frappe


def validate(self, method):
    #print("ejhfhefegfgegfegfeg")

    for d in self.items:
        item = frappe.db.get_value("Item", d.item_code, "is_stock_item")
        if not item:
            d.db_set("delivered_by_supplier", 1)
    
    frappe.db.commit()
   
def on_update_after_submit(self,method):
    
    print("ejhfhefegfgegfegfeg")

    for d in self.items:
        item = frappe.db.get_value("Item", d.item_code, "is_stock_item")
        if not item:
            d.db_set("delivered_by_supplier", 1)
    
    frappe.db.commit()   