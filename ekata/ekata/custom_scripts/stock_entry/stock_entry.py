import frappe
from frappe.model.mapper import get_mapped_doc

def on_submit(doc,method=None):
    for item in doc.items:
        frappe.db.set_value('Stock Ledger Entry',{'voucher_no':doc.name,'item_code':item.item_code},'supplier',item.supplier)

def validate(doc, method=None):
    print('\n\n--------------apply loss and set basic rate--------------\n\n')

    # 🥇 First: Adjust qty based on loss
    for i in doc.items:
        if i.custom_loss and i.custom_loss > 0:
            # Store original quantity
            i.custom_qty_before_loss = i.qty

            # Apply loss (e.g., 5 means 5% loss)
            loss_factor = 1 - (i.custom_loss / 100)
            i.qty = round(i.qty * loss_factor, 4)
            i.transfer_qty = i.qty  # Optional: sync transfer_qty
            print(f"Applied loss on {i.item_code}: Original {i.custom_qty_before_loss} → New {i.qty}")

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
    if doc.stock_entry_type != "Material Issue" or not doc.custom_cropster_entry:
        return

    original_items = list(doc.items)

    for item in original_items:
        compositions = frappe.get_all(
            "Composition of Items",
            filters={"item": item.item_code},
            fields=["name"]
        )

        for composition in compositions:
            comp_doc = frappe.get_doc("Composition of Items", composition.name)

            for child in comp_doc.composition:
                total_qty = child.qty * item.qty

                doc.append(
                    "items",
                    {
                        "item_code": child.item,
                        "qty": total_qty,
                        "uom": child.uom,
                        "s_warehouse": item.s_warehouse
                    },
                )

    doc.save()
