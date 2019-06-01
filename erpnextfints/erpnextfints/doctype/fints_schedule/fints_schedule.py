# -*- coding: utf-8 -*-
# Copyright (c) 2019, jHetzer and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from dateutil.relativedelta import relativedelta
from frappe.utils import now_datetime
import erpnextfints.erpnextfints.doctype.fints_import.fints_import as fin_imp
# from erpnextfints.utils.fints_wrapper import FinTSConnection

class FinTSSchedule(Document):
    pass

@frappe.whitelist()
def import_fints_payments(manual=None):

    schedule_settings = frappe.get_single('FinTS Schedule')

    # Query child table
    for child_item in schedule_settings.schedule_items:
        # Get the last run / last imported transaction date
        try:
            if child_item.active and (child_item.import_frequency or manual):
                lastruns = frappe.get_list(
                    'FinTS Import',
                    filters={
                        'fints_login':child_item.fints_login,
                        'docstatus': 1,
                        'end_date': ('>','1/1/1900')
                    },
                    fields=['name', 'end_date','modified'],
                    order_by='end_date, modified desc'
                )[:1] or [None]
                # Create new 'FinTS Import' doc
                fints_import = frappe.get_doc({
                    'doctype': 'FinTS Import',
                    'fints_login':child_item.fints_login
                })
                if lastruns[0] is not None:
                    if child_item.import_frequency == 'Daily':
                        checkdate = now_datetime().date() - relativedelta(days=1)
                    elif child_item.import_frequency == 'Weekly':
                        checkdate = now_datetime().date() - relativedelta(weeks=1)
                    elif child_item.import_frequency == 'Monthly':
                        checkdate = now_datetime().date() - relativedelta(months=1)
                    else:
                        raise Exception("Unknown frequency")
                    if lastruns[0].end_date < checkdate or manual:
                        fints_import.from_date = lastruns[0].end_date + relativedelta(days=1)
                        # overlap = child_item.overlap
                        # if overlap < 0:
                        #    overlap = 0
                    else:
                        frappe.db.rollback()
                        print("skip")
                        continue
                    #fints_import.from_date = lastruns[0].end_date - relativedelta(days=overlap)
                # else: load all available transactions of the past
                # always import transactions from yesterday
                fints_import.to_date = now_datetime().date() - relativedelta(days=1)

                fints_import.save()
                print(frappe.as_json(fints_import))
                fin_imp.import_transactions(fints_import.name, child_item.fints_login)

                print(frappe.as_json(child_item))
        except Exception as e:
            frappe.log_error(frappe.get_traceback())