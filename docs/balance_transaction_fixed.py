# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class BalanceTransaction(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		currency: DF.Link | None
		description: DF.SmallText | None
		docstatus: DF.Literal[0, 1, 2]
		ending_balance: DF.Currency
		invoice: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		source: DF.Data | None
		team: DF.Link
		type: DF.Literal[
			"Adjustment",
			"Applied To Invoice",
			"Free Credits",
			"Unapplied From Invoice",
			"Transferred",
			"Transferred From",
			"Withdrawn",
			"Partnership Fee",
			"Invoiced Amount",
		]
		unallocated_amount: DF.Currency
	# end: auto-generated types

	def validate(self):
		if self.amount == 0:
			frappe.throw("Amount cannot be 0")

	def before_submit(self):
		if self.type == "Partnership Fee":
			# don't update ending balance or unallocated amount for partnership fee
			return

		# FIXED: Use direct SQL to avoid Frappe v16 query builder incompatibility
		# Original code used: fields=["sum(amount) as ending_balance"]
		# This syntax is obsolete in Frappe v16 and causes ValidationError
		last_balance_result = frappe.db.sql("""
			SELECT SUM(amount) as ending_balance
			FROM `tabBalance Transaction`
			WHERE team = %s
			  AND docstatus = 1
			  AND type != %s
			GROUP BY team
		""", (self.team, "Partnership Fee"), as_dict=1)

		if last_balance_result:
			last_balance = last_balance_result[0].ending_balance or 0
		else:
			last_balance = 0

		if last_balance:
			self.ending_balance = (last_balance or 0) + self.amount
		else:
			self.ending_balance = self.amount

		# get unallocated amount of team
		allocated_amount = frappe.db.get_value(
			"Team", self.team, "total_allocated_amount_without_tax"
		)
		self.unallocated_amount = allocated_amount - (last_balance or 0)
