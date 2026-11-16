"""Manual-entry classroom workflow; no tax rules or external services."""

# Fields: key, label, type, options (where applicable).
def text(key, label, kind='text'):
    return (key, label, kind, [])
def choice(key, label, options=('Yes', 'No')):
    return (key, label, 'select', options)
def money(key, label):
    return text(key, label, 'number')

PAGES = [
 ('personal', 'Taxpayer Information', [text('first','First name'),text('middle','Middle initial'),text('last','Last name'),text('occupation','Occupation'),text('ssn','Sample Social Security number'),text('dob','Date of birth','date'),text('address','Street address'),text('apt','Apartment'),text('city','City'),text('region','State'),text('zip','ZIP code'),text('phone','Phone number'),choice('dependent','Can someone claim you as a dependent?'),choice('blind','Are you legally blind?')]),
 ('personal', 'Filing Status', [choice('status','Filing status',('Single','Married Filing Jointly','Married Filing Separately','Head of Household','Qualifying Surviving Spouse')),text('spouse','Spouse name (if applicable)'),text('spouse_ssn','Sample spouse SSN (if applicable)'),text('spouse_dob','Spouse date of birth','date')]),
 ('personal', 'Your Dependents and Qualifying Children', []),
 ('personal', 'Personal Information Summary', []),
 ('income', 'Wages (Form W-2)', []),
 ('income', 'Interest and Unemployment', [choice('has_interest','Did you earn taxable interest?'),choice('has_unemployment','Did you receive unemployment compensation?'),money('interest','Taxable interest (Form 1099-INT)'),money('interest_withheld','Federal tax withheld on interest'),money('unemployment','Unemployment compensation (Form 1099-G)'),money('unemployment_withheld','Federal tax withheld on unemployment')]),
 ('income', 'Supported Income Check', [choice('unsupported_income','Do you have income other than W-2 wages, taxable interest, or unemployment?')]),
 ('income', 'Income Summary', []),
 ('deductions', 'Standard Deduction', [choice('needs_itemized','Do you need to itemize deductions?')]),
 ('deductions', 'Dependent Credits', [choice('claim_credit','Would you like to claim the supported child / other qualifying child dependent credit?')]),
 ('deductions', 'Credit Scope Check', [choice('other_credit_needed','Do you need any other credit or adjustment (including refundable child credit or EIC)?')]),
 ('deductions', 'Deductions and Credits Summary', []),
 ('misc', 'Payments and Other Situations', [money('estimated','Estimated federal tax payments'),money('extension','Federal extension payment'),choice('foreign','Foreign accounts or trusts?')]),
 ('summary', 'Federal Tax Summary', []),
]
STAGES = [('personal','Personal'),('income','Income'),('deductions','Deductions / Credits'),('misc','Misc'),('summary','Summary')]

from app.services.rules import calculate

def totals(data):
    return calculate(data)
