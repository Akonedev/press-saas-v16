# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.team.test_team import create_test_team


class TestBalanceTransaction(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_team_balance(self):
		team = create_test_team()

		team.allocate_credit_amount(50, source="")
		self.assertEqual(team.get_balance(), 50)

		team.allocate_credit_amount(-10, source="")
		self.assertEqual(team.get_balance(), 40)

		team.allocate_credit_amount(100, source="")
		self.assertEqual(team.get_balance(), 140)

		self.assertEqual(frappe.db.count("Balance Transaction", {"team": team.name}), 3)

	def test_before_submit_basic_balance(self):
		"""Test ending balance calculation with sequential transactions (SQL fix validation)"""
		team = create_test_team()

		# Transaction 1: +50
		team.allocate_credit_amount(50, source="Prepaid Credits")
		bt1 = frappe.get_last_doc("Balance Transaction", {"team": team.name})
		self.assertEqual(bt1.ending_balance, 50)

		# Transaction 2: +30
		team.allocate_credit_amount(30, source="Free Credits")
		bt2 = frappe.get_last_doc("Balance Transaction", {"team": team.name})
		self.assertEqual(bt2.ending_balance, 80)

		# Transaction 3: -20
		team.allocate_credit_amount(-20, source="")
		bt3 = frappe.get_last_doc("Balance Transaction", {"team": team.name})
		self.assertEqual(bt3.ending_balance, 60)

	def test_before_submit_no_prior_transactions(self):
		"""Test first transaction for a team (no history)"""
		team = create_test_team()

		# First transaction should set ending_balance = amount
		team.allocate_credit_amount(100, source="Prepaid Credits")
		bt = frappe.get_last_doc("Balance Transaction", {"team": team.name})

		self.assertEqual(bt.ending_balance, 100)

	def test_before_submit_negative_balance(self):
		"""Test negative balance scenarios with sufficient credits"""
		team = create_test_team()

		# Start with positive balance
		team.allocate_credit_amount(100, source="Prepaid Credits")

		# Transfer less than available (test negative amount, but valid)
		team.allocate_credit_amount(-30, source="")
		bt = frappe.get_last_doc("Balance Transaction", {"team": team.name})

		self.assertEqual(bt.ending_balance, 70)  # 100 - 30 = 70

	def test_before_submit_partnership_fee_excluded(self):
		"""Test that Partnership Fee transactions are excluded from balance calculation"""
		team = create_test_team()

		# Regular transaction
		team.allocate_credit_amount(100, source="Prepaid Credits")

		# Partnership fee (should be excluded from sum)
		partnership_fee = frappe.get_doc({
			"doctype": "Balance Transaction",
			"team": team.name,
			"type": "Partnership Fee",
			"amount": -10
		})
		partnership_fee.insert()
		partnership_fee.submit()

		# New transaction should NOT include partnership fee in balance
		team.allocate_credit_amount(50, source="Free Credits")
		bt = frappe.get_last_doc("Balance Transaction", {
			"team": team.name,
			"type": ("!=", "Partnership Fee")
		})

		self.assertEqual(bt.ending_balance, 150)  # 100 + 50, NOT 100 - 10 + 50

	def test_before_submit_team_isolation(self):
		"""Test that team balances are isolated (GROUP BY team)"""
		team1 = create_test_team("team1@example.com")
		team2 = create_test_team("team2@example.com")

		# Team 1 transactions
		team1.allocate_credit_amount(100, source="Prepaid Credits")

		# Team 2 transactions
		team2.allocate_credit_amount(50, source="Free Credits")

		# Verify isolation
		self.assertEqual(team1.get_balance(), 100)
		self.assertEqual(team2.get_balance(), 50)

	def test_before_submit_concurrent_transactions(self):
		"""Test that rapid sequential transactions calculate balance correctly"""
		team = create_test_team()

		# Simulate rapid sequential submissions
		amounts = [10, 20, 30, 40, 50]
		for amount in amounts:
			team.allocate_credit_amount(amount, source="Prepaid Credits")

		# Final balance should be sum of all amounts
		self.assertEqual(team.get_balance(), sum(amounts))  # 150
