from frappe.model.document import Document

class CompositionofItems(Document):
    def validate(self):
        if not self.item_qty or self.item_qty == 0:
            frappe.throw("Item Qty must be greater than zero.")

        for row in self.composition:
            if row.qty and row.qty > 0:
                row.ratio = row.qty / self.item_qty
            else:
                row.ratio = 0  # Ensuring no division by zero

