"""Validate a submitted page, updating only its draft values."""
from decimal import Decimal
from datetime import date
from .required import validate_required
from .scope import unavailable

def validate_page(step, fields, form, draft):
    validate_required(step, fields, form, draft)
    for key, label, kind, options in fields:
        value = form.get(key, '').strip()[:500]
        if step==5 and key in ['interest','interest_withheld','unemployment','unemployment_withheld']:
            topic='unemployment' if key.startswith('unemployment') else 'interest'
            if draft.get('has_'+topic)=='No':value='0'
        if kind == 'number' and value:
            number = Decimal(value)
            if not number.is_finite() or number < 0 or abs(number) > Decimal('1000000000000'):
                raise ValueError('Enter a finite amount below one trillion.')
            value = str(number.quantize(Decimal('0.01')))
        if kind == 'date' and value:
            date.fromisoformat(value)
        if options and value and value not in options:
            raise ValueError('Choose a listed option.')
        if unavailable(key,value):
            raise ValueError(label+' — this choice is not supported.')
        draft[key] = value
    if step==1 and draft.get('status')!='Married Filing Jointly':
        for key in ['spouse','spouse_ssn','spouse_dob']:draft[key]=''
    if step in (2, 4):
        is_w2 = step == 4
        prefix = 'w2' if is_w2 else 'dependent'
        keys = ['employer','ein','address','employee_name','employee_address','wages','withheld','ss_wages','ss_tax','medicare_wages','medicare_tax'] if is_w2 else ['name','ssn','dob','relationship','months','own_support','resident','joint_return','student']
        rows = []
        for n in range(6):
            row = {k:form.get(f'{prefix}_{n}_{k}', '').strip()[:500] for k in keys}
            if not any(row.values()):
                continue
            if is_w2:
                if not row['employer']:
                    raise ValueError('Enter an employer name for each W-2.')
                for k in keys[5:]:
                    number = Decimal(row[k] or '0')
                    if not number.is_finite() or number < 0 or number > Decimal('1000000000000'):
                        raise ValueError('W-2 amounts must be finite, nonnegative numbers.')
                    row[k] = str(number.quantize(Decimal('0.01')))
                row['document_id']=form.get(f'w2_{n}_document_id','').strip()[:100]
            elif not row['name']:
                raise ValueError('Enter a name for each dependent.')
            elif row['months'] and not 0 <= int(row['months']) <= 12:
                raise ValueError('Months must be between 0 and 12.')
            if not is_w2 and row['dob']:
                date.fromisoformat(row['dob'])
            if not is_w2:
                for key in ['own_support','resident','joint_return','student']:
                    if row[key] not in ('', 'Yes', 'No'):
                        raise ValueError('Choose Yes or No.')
            if not is_w2:
                for key in ['relationship','own_support','resident','joint_return']:
                    if unavailable(key,row.get(key)):
                        raise ValueError('This dependent situation is not supported: '+key.replace('_',' ')+'.')
            rows.append(row)
        draft['w2s' if is_w2 else 'dependents'] = rows
    if step == 0 and form.get('action') != 'back' and not all(draft.get(k) for k in ['first','last','dob']):
        raise ValueError('Enter first name, last name, and date of birth.')
    if step == 1 and form.get('action') != 'back' and not draft.get('status'):
        raise ValueError('Choose a filing status.')
