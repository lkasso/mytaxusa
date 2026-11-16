"""Versioned classroom rules, intentionally a limited simulation of federal taxes."""
from datetime import date
from decimal import Decimal

VERSION = 'classroom-2026-v1'
YEAR = 2026
STANDARD = {'Single':14600, 'Married Filing Jointly':29200}
BRACKETS = [(11600, '.10'), (47150, '.12'), (100525, '.22'), (191950, '.24'), (243725, '.32'), (609350, '.35'), (None, '.37')]

def amount(data, key):
    try:
        value=Decimal(str(data.get(key) or 0))
        return value if value.is_finite() else Decimal(0)
    except Exception:
        return Decimal(0)

def age_on_year_end(value):
    try:
        born=date.fromisoformat(value)
        return YEAR-born.year if born <= date(YEAR,12,31) else -1
    except (ValueError,TypeError):
        return None

def dependent_result(row):
    required=['dob','relationship','months','own_support','resident','joint_return','student']
    if any(row.get(k,'') == '' for k in required):
        return 'needs_information'
    age=age_on_year_end(row.get('dob'))
    try: months=int(row['months'])
    except ValueError: return 'needs_information'
    if age is None or age < 0: return 'needs_information'
    related=row['relationship'] in ('Child','Stepchild','Foster child','Sibling','Grandchild')
    qualifies=related and (age<19 or (age<24 and row['student']=='Yes')) and months>6 and row['own_support']=='No' and row['resident']=='Yes' and row['joint_return']=='No'
    return 'eligible' if qualifies else 'ineligible'

def calculate(data):
    wages=sum((amount(w,'wages') for w in data.get('w2s',[])),Decimal(0))
    income=wages+sum((amount(data,topic) for topic in ['interest','unemployment'] if data.get('has_'+topic)!='No'),Decimal(0))
    deduction=Decimal(STANDARD.get(data.get('status'),0))
    taxable=max(Decimal(0),income-deduction)
    tax=Decimal(0); previous=Decimal(0); factor=2 if data.get('status')=='Married Filing Jointly' else 1
    for limit,rate in BRACKETS:
        upper=Decimal(limit*factor) if limit else taxable
        tax+=max(Decimal(0),min(taxable,upper)-previous)*Decimal(rate)
        previous=upper
        if taxable<=upper: break
    qualified=[d for d in data.get('dependents',[]) if dependent_result(d)=='eligible']
    # Classroom CTC/ODC simulation, nonrefundable only, no phaseout calculation.
    credit=Decimal(0)
    if data.get('claim_credit')=='Yes':
        credit=sum((Decimal(2000 if age_on_year_end(d['dob'])<17 else 500) for d in qualified),Decimal(0))
    credit=min(tax,credit)
    total_tax=(tax-credit).quantize(Decimal('.01'))
    payments=sum((amount(w,'withheld') for w in data.get('w2s',[])),Decimal(0))+sum((amount(data,k) for k in ['estimated','extension']),Decimal(0))
    payments+=sum((amount(data,topic+'_withheld') for topic in ['interest','unemployment'] if data.get('has_'+topic)!='No'),Decimal(0))
    return dict(wages=wages,income=income,adjustments=Decimal(0),agi=income,deduction=deduction,taxable=taxable,credits=credit,tax=total_tax,payments=payments,refund=max(Decimal(0),payments-total_tax),owed=max(Decimal(0),total_tax-payments))
