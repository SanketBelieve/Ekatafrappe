import frappe


def validate(self, method=None):
    if self.naming_series == "Q .##./.FY.":
        pass
        # if not frappe.db.exists('Quotation', 'Q 24/2022-23'):
        #     self.name = "Q 24/2022-23"
        #     frappe.db.sql("update `tabSeries` set current=24 where name = 'Q '")


def after_insert(self, method=None):
    if self.opportunity:
        opportunity = frappe.get_doc("Opportunity", self.opportunity)

        updated = False

        # Only copy if the fields are empty (first-time insert scenario)
        if (
            not self.custom_opportunity_category
            and opportunity.custom_opportunity_category
        ):
            self.custom_opportunity_category = opportunity.custom_opportunity_category
            updated = True

        if not self.custom_purpose and opportunity.purpose:
            self.custom_purpose = opportunity.purpose
            updated = True

        # Save silently to DB only if values were updated
        if updated:
            self.db_update()
