"""Workflow navigation and summary presentation."""
from .filing import PAGES

def next_step(step, action):
    return max(0, step-1) if action == "back" else min(len(PAGES)-1, step+1)

def summary_rows(step):
    return [('wages','Wages'),('income','Total income')] if step == 7 else [('adjustments','Adjustments to income'),('deduction','Standard deduction'),('credits','Nonrefundable credits')] if step == 11 else [('income','Total income'),('adjustments','Total adjustments'),('agi','Adjusted gross income'),('deduction','Deductions'),('taxable','Taxable income'),('credits','Nonrefundable credits'),('tax','Total tax after credits'),('payments','Total payments and refundable credits'),('refund','Refund'),('owed','Amount owed')]
