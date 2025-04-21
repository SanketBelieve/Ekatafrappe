import frappe
from frappe.model.mapper import get_mapped_doc

def on_submit(doc,method=None):
    for item in doc.items:
        frappe.db.set_value('Stock Ledger Entry',{'voucher_no':doc.name,'item_code':item.item_code},'supplier',item.supplier)

def validate(doc, method=None):
    

    # 🥇 First: Adjust qty based on loss
    

    # 🥈 Second: Apply basic rate logic for Repack and Bulking
    if doc.stock_entry_type in ['Repack', 'Bulking']:
        rm_amount = 0
        fg_qty = 0
        rate = 0
        last_fg_item = []

        for i in doc.items:
            if i.custom_is_process_loss:
                i.db_set('is_finished_item', 0)

            i.db_set('set_basic_rate_manually', 1)

            if not i.is_finished_item and not i.is_scrap_item and not i.custom_is_process_loss:
                rm_amount += i.amount

            if i.is_finished_item:
                fg_qty += i.qty

            if i.custom_is_process_loss:
                i.db_set('basic_rate', 0)
                i.db_set('amount', 0)

        if fg_qty > 0:
            rate = rm_amount / fg_qty
            print(f'>>> fg qty: {fg_qty}, rate: {rate}')

            for i in doc.items:
                if i.is_finished_item:
                    last_fg_item.append(i)
                    amount = rate * i.qty
                    i.db_set('basic_rate', rate)
                    i.db_set('amount', amount)
                    i.db_set('basic_amount', amount)

        # Recalculate total values
        doc.set_total_incoming_outgoing_value()



@frappe.whitelist()
def create_repack_entry(source_name, target_doc=None):
	print('>>> create repack entry >>>')
	doc = frappe.flags.args.doc
	SEDoc = frappe.get_doc('Stock Entry', doc['name'])
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type = "Repack"
	stock_entry.set_posting_time = 1
	for item in SEDoc.items:
		print('\n\n >>>> ', item)
		if item.is_finished_item == 1:
			stock_entry.append('items', {
				's_warehouse': item.t_warehouse,
				'item_code': item.item_code,
				'qty': item.qty,
				'uom': item.uom,
				'stock_uom': item.stock_uom,
				'basic_rate': item.basic_rate,
				'batch_no': item.batch_no,
				'receipt_no': item.receipt_no,
				'outturn_no': item.outturn_no,
				'season': item.season,
				'coffee_processing_details': item.coffee_processing_details
			})
	return stock_entry

def apply_composition_items_to_stock_entry(doc, method):
    # Check if this is a Cropster entry and item_type is "Material Receipt"
    if not doc.custom_cropster_type_entry or doc.custom_cropster_type_entry.upper() != "YES":
        return

    if doc.item_type != "Material Receipt":
        return

    raw_warehouse = doc.get("custom_cropster_raw_material_warehouse")
    if not raw_warehouse:
        frappe.msgprint("⚠️ No Raw Material Warehouse specified for Cropster entry.")
        return

    # ✅ Create Material Issue Entry for Composition Deduction
    material_issue_entry = frappe.new_doc("Stock Entry")
    material_issue_entry.stock_entry_type = "Material Issue"
    material_issue_entry.purpose = "Material Issue"
    material_issue_entry.company = doc.company
    material_issue_entry.custom_cropster_entry = 1
    material_issue_entry.posting_date = doc.posting_date
    material_issue_entry.posting_time = doc.posting_time
    material_issue_entry.set_posting_time = 1
    material_issue_entry.remarks = f"Auto-created to deduct raw materials for Cropster entry {doc.name}"
    material_issue_entry.reference_doctype = "Stock Entry"
    material_issue_entry.reference_name = doc.name

    has_items = False

    for item in doc.items:
        compositions = frappe.get_all(
            "Composition of Items",
            filters={"item": item.item_code},
            fields=["name"]
        )

        composition_summary = []  # to build summary for this item

        for composition in compositions:
            comp_doc = frappe.get_doc("Composition of Items", composition.name)

            for child in comp_doc.composition:
                total_qty = (child.qty or 0) * (item.qty or 0)

                material_issue_entry.append("items", {
                    "item_code": child.item,
                    "qty": total_qty,
                    "uom": child.uom,
                    "stock_uom": child.uom,
                    "conversion_factor": 1,
                    "s_warehouse": raw_warehouse
                })

                has_items = True
                composition_summary.append(
                    f"{child.item}: {total_qty} {child.uom}"
                )

        # 📝 Set the composition summary in the main stock entry item's custom field
        if composition_summary:
            item.custom_composition_description = "\n".join(composition_summary)

    if has_items:
        material_issue_entry.save()
        frappe.msgprint(
            f'✅ <a href="/app/stock-entry/{material_issue_entry.name}" target="_blank">'
            f'View Material Issue: <b>{material_issue_entry.name}</b></a>',
            indicator="green"
        )

        # ⛓️ Link back the created material issue
        doc.custom_cropster_raw_material_entry = f"/app/stock-entry/{material_issue_entry.name}"
        doc.save()
    else:
        frappe.msgprint("ℹ️ No composition items found to deduct.")



