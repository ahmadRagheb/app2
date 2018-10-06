# -*- coding: utf-8 -*-,
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _, throw
from frappe.utils import today, flt, cint, fmt_money, formatdate, getdate, add_days, add_months, get_last_day
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.utils import get_fiscal_years, validate_fiscal_year, get_account_currency
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.controllers.sales_and_purchase_return import validate_return
from erpnext.accounts.party import get_party_account_currency, validate_party_frozen_disabled
from erpnext.exceptions import InvalidCurrency
import frappe
import datetime
import erpnext 
from frappe import utils



def period_close():
	#make_gl_entries("SAUD PRIVATE OFFICE","2018-12-30","2018")
	fiscal_year=frappe.get_doc("Global Defaults");
	company=frappe.get_all("Company",['name']);
	fiscal=fiscal_year.current_fiscal_year
	if fiscal:
		fis=frappe.get_doc("Fiscal Year",fiscal)
	print (fis.year_end_date).strftime("%Y-%m-%d")
	if (fis.year_end_date).strftime("%Y-%m-%d") == utils.today():
		acc=frappe.get_doc({
		"doctype" : "Period Closing Voucher",
		"company" : company[1]['name'],
		"posting_date": datetime.datetime.now(),
		"closing_account_head":"رأس المال - SPO",
		"remarks":"Period Closing Voucher"})

		acc.flags.ignore_permissions = True
		acc.save()
		acc.submit()


def make_gl_entries(company,posting_date,fiscal_year):
		gl_entries = []
		net_pl_balance = 0
		from erpnext.accounts.utils import get_fiscal_year, validate_fiscal_year

		year_start_date = get_fiscal_year(posting_date, fiscal_year, company)[1]

		pl_accounts = get_pl_balances(company,posting_date,year_start_date)

		for acc in pl_accounts:
			if flt(acc.balance_in_company_currency):
				gl_entries.append(get_gl_dict(company,posting_date,fiscal_year,{
					"account": acc.account,
					"cost_center": acc.cost_center,
					"account_currency": acc.account_currency,
					"debit_in_account_currency": abs(flt(acc.balance_in_account_currency)) \
						if flt(acc.balance_in_account_currency) < 0 else 0,
					"debit": abs(flt(acc.balance_in_company_currency)) \
						if flt(acc.balance_in_company_currency) < 0 else 0,
					"credit_in_account_currency": abs(flt(acc.balance_in_account_currency)) \
						if flt(acc.balance_in_account_currency) > 0 else 0,
					"credit": abs(flt(acc.balance_in_company_currency)) \
						if flt(acc.balance_in_company_currency) > 0 else 0
				}))

				net_pl_balance += flt(acc.balance_in_company_currency)

		if net_pl_balance:
			gl_entries.append(get_gl_dict(company,posting_date,fiscal_year,{
				"account": "رأس المال - SPO",
				"debit_in_account_currency": abs(net_pl_balance) if net_pl_balance > 0 else 0,
				"debit": abs(net_pl_balance) if net_pl_balance > 0 else 0,
				"credit_in_account_currency": abs(net_pl_balance) if net_pl_balance < 0 else 0,
				"credit": abs(net_pl_balance) if net_pl_balance < 0 else 0
			}))

		from erpnext.accounts.general_ledger import make_gl_entries
		make_gl_entries(gl_entries)

def get_pl_balances(company,posting_date,year_start_date):
	return frappe.db.sql("""select
				t1.account, t1.cost_center, t2.account_currency,
				sum(t1.debit_in_account_currency) - sum(t1.credit_in_account_currency) as balance_in_account_currency,
				sum(t1.debit) - sum(t1.credit) as balance_in_company_currency
			from `tabGL Entry` t1, `tabAccount` t2
			where t1.account = t2.name and t2.report_type = 'Profit and Loss'
			and t2.docstatus < 2 and t2.company = %s
			and t1.posting_date between %s and %s
			group by t1.account, t1.cost_center
		""", (company, year_start_date, posting_date), as_dict=1)


def get_gl_dict(company,posting_date,fiscal_year,args, account_currency=None):
		"""this method populates the common properties of a gl entry record"""

		fiscal_years = get_fiscal_years(posting_date, company=company)
		if len(fiscal_years) > 1:
			frappe.throw(_("Multiple fiscal years exist for the date {0}. Please set company in Fiscal Year").format(formatdate(self.posting_date)))
		else:
			fiscal_year = fiscal_years[0][0]

		gl_dict = frappe._dict({
			'company': company,
			'posting_date': posting_date,
			'fiscal_year': fiscal_year,
			'voucher_type': "Period Closing Voucher",
			'voucher_no': "Vc",
			'remarks': "period closing",
			'debit': 0,
			'credit': 0,
			'debit_in_account_currency': 0,
			'credit_in_account_currency': 0,
			'is_opening':  "No",
			'party_type': None,
			'party': None
		})
		gl_dict.update(args)

		if not account_currency:
			account_currency = get_account_currency(gl_dict.account)

		

		return gl_dict

