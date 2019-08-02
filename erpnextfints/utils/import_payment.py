from __future__ import unicode_literals

import frappe
import hashlib


class ImportPaymentEntry:
    def __init__(self, fints_login, allow_error=False, debug=False):
        self.debug = debug
        self.allow_error = allow_error
        self.payment_entries = []
        self.fints_login = fints_login
        self.default_customer = fints_login.default_customer
        self.default_supplier = fints_login.default_supplier

    def get_party_by_value(self, sender, party_type, iban=None):
        party = None
        is_default = False
        party_name = frappe.get_value(party_type, sender, 'name')

        if iban:
            iban_sql_query = ("SELECT `name` " +
                        "FROM `tab{0}` " +
                        "WHERE `iban` = '{1}'").format(party_type, iban)
            party_by_iban = frappe.db.sql(iban_sql_query, as_dict=True)
            if len(party_by_iban) == 1:
                party = party_by_iban[0].name
        if not party and party_name:
            party = party_name
        if not party:
            "party"
            if party_type == "Customer":
                party = self.default_customer
            elif party_type == "Supplier":
                party = self.default_supplier
            is_default = True

        return {"is_default": is_default, "party": party}

    def fints_import(self, fints_transaction):
        total_items = len(fints_transaction)
        remarkType = ""
        for idx,t in enumerate(fints_transaction):
            if float(t["amount"]["amount"])  != 0:
                # Convert to positive value if required
                amount = abs(float(t["amount"]["amount"]))

                partyMapping = t["applicant_name"]
                uniquestr = "{0},{1},{2},{3},{4}".format(
                    t["date"],
                    amount,
                    partyMapping,
                    t["posting_text"],
                    t['purpose']
                )
                transaction_id = hashlib.md5(uniquestr.encode('utf-8')).hexdigest()
                if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
                    new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
                    if t["status"].lower() == "c":
                        if self.fints_login.enable_received:
                            rappe.msgprint("Is Enabled")
                            new_payment_entry.payment_type = "Receive"
                            new_payment_entry.party_type = "Customer"
                            new_payment_entry.paid_to = self.fints_login.erpnext_account
                            remarkType = "Sender"
                        else:
                            continue
                    elif t["status"].lower() == "d":
                        if self.fints_login.enable_pay:
                            new_payment_entry.payment_type = "Pay"
                            new_payment_entry.party_type = "Supplier"
                            new_payment_entry.paid_from = self.fints_login.erpnext_account
                            remarkType = "Receiver"
                        else:
                            continue
                    else:
                         frappe.log_error(_("Payment type not handled"),_("FinTS Import Error"))
                         continue

                    # date is in YYYY.MM.DD (json)
                    new_payment_entry.posting_date = t["date"]
                    new_payment_entry.company = self.fints_login.company

                    new_payment_entry.paid_amount = amount
                    new_payment_entry.received_amount = amount
                    new_payment_entry.iban = t["applicant_iban"]
                    new_payment_entry.bic = t["applicant_bin"]

                    party = self.get_party_by_value(
                        t["applicant_name"],
                        new_payment_entry.party_type,
                        t["applicant_iban"]
                    )
                    new_payment_entry.party = party["party"]
                    if party["is_default"]:
                        remarks = ("{0} '{1}':\n{2} {3}").format(
                            remarkType,
                            t["applicant_name"],
                            t["posting_text"],
                            t['purpose']
                        )
                    else:
                        remarks = "{0} {1}".format(t["posting_text"],t['purpose'])
                    new_payment_entry.remarks = remarks

                    new_payment_entry.reference_no = transaction_id
                    new_payment_entry.reference_date = t["date"]
                    if self.debug:
                        frappe.msgprint(frappe.as_json(new_payment_entry))
                    self.payment_entries.append(new_payment_entry.insert())
