"""Map return-level findings to individual editable controls."""
from decimal import Decimal, InvalidOperation
from datetime import date

def field_errors(data, findings, fields, submitted=None):
    errors={}
    def add(name,message):errors.setdefault(name,message)
    for f in findings:
        if f.severity!='error':continue
        if f.code=='PERSONAL_INCOMPLETE':
            for name in ['first','last','dob','ssn','status']:
                if not data.get(name):add(name,'This field is required.')
        elif f.code=='SPOUSE_INCOMPLETE':
            for name in ['spouse','spouse_ssn','spouse_dob']:
                if not data.get(name):add(name,'Enter this spouse information.')
        elif f.field.startswith('dependents['):
            index=int(f.field.split('[')[1].split(']')[0]);row=data.get('dependents',[])[index]
            prefix=f'dependent_{index}_'
            if f.code in ['SSN_FORMAT','SSN_DUPLICATE']:add(prefix+'ssn',f.message)
            elif f.code=='DEPENDENT_INCOMPLETE':
                for name in ['name','ssn','dob','relationship','months','student','own_support','resident','joint_return']:
                    if row.get(name,'')=='':add(prefix+name,'Complete this dependent information.')
            else:
                for name in ['dob','relationship','months','student','own_support','resident','joint_return']:add(prefix+name,f.message)
        elif f.field.startswith('w2s['):
            index=int(f.field.split('[')[1].split(']')[0]);row=data.get('w2s',[])[index]
            for name in ['employer','ein','wages','withheld']:
                if row.get(name,'')=='':add(f'w2_{index}_{name}','Complete this W-2 field. Enter 0 if applicable.')
        elif f.field=='personal':
            for name in ['dependent','blind']:
                if data.get(name)=='Yes':add(name,f.message)
        elif f.field!='legacy':add(f.field,f.message)
    if submitted is not None:
        for name,label,kind,options in fields:
            value=submitted.get(name,'').strip()
            try:
                if kind=='number' and value:
                    number=Decimal(value)
                    if not number.is_finite() or number<0 or number>Decimal('1000000000000'):raise ValueError()
                if kind=='date' and value:date.fromisoformat(value)
                if options and value and value not in options:raise ValueError()
            except (ValueError,InvalidOperation):add(name,'Enter a valid date or nonnegative amount, or choose a listed option.')
        for name,value in submitted.items():
            if name.startswith('w2_') and name.rsplit('_',1)[-1] in ['wages','withheld','tax'] and value:
                try:
                    number=Decimal(value)
                    if not number.is_finite() or number<0:raise ValueError()
                except (ValueError,InvalidOperation):add(name,'Enter a valid nonnegative amount.')
    return errors
