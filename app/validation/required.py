"""Shared required-field contract for server validation and browser forms."""
REQUIRED={
 0: {'first','last','ssn','dob','address','city','region','zip','dependent','blind'},
 1: {'status'},
 5: {'has_interest','has_unemployment'},
 6: {'unsupported_income'}, 8: {'needs_itemized'}, 9: {'claim_credit'},
 10: {'other_credit_needed'}, 12: {'estimated','extension','foreign'},
}
DEPENDENT_REQUIRED={'name','ssn','dob','relationship','months','student','own_support','resident','joint_return'}
W2_REQUIRED={'employer','ein','address','wages','withheld'}
SPOUSE_REQUIRED={'spouse','spouse_ssn','spouse_dob'}

class RequiredFieldsError(ValueError):
    def __init__(self, errors):
        super().__init__('Complete the highlighted required fields before continuing.')
        self.errors=errors

def required_fields(step, data):
    fields=set(REQUIRED.get(step,set()))
    if step==1 and data.get('status')=='Married Filing Jointly':fields.update(SPOUSE_REQUIRED)
    if step==5:
        for topic in ['interest','unemployment']:
            if data.get('has_'+topic)=='Yes':fields.update({topic,topic+'_withheld'})
    return fields

def validate_required(step, fields, form, draft):
    # Preserve submitted values even if required-field validation fails.
    for key,_,_,_ in fields:draft[key]=form.get(key,'').strip()[:500]
    if step==5:
        for topic in ['interest','unemployment']:
            if draft.get('has_'+topic)=='No':
                draft[topic]='0'
                draft[topic+'_withheld']='0'
    errors={}
    if step in (2,4):
        prefix='dependent' if step==2 else 'w2'
        collection='dependents' if step==2 else 'w2s'
        needed=DEPENDENT_REQUIRED if step==2 else W2_REQUIRED
        rows=[]
        for n in range(6):
            start=f'{prefix}_{n}_'
            row={key[len(start):]:value.strip()[:500] for key,value in form.items() if key.startswith(start)}
            if not any(row.values()):
                rows.append({});continue
            rows.append(row)
            if form.get('action')!='back':
                for key in needed:
                    if not row.get(key):errors[start+key]='This field is required. Enter 0 for an amount that does not apply.'
        draft[collection]=rows
    if form.get('action')=='back':return
    for key in required_fields(step,draft):
        if not draft.get(key):errors[key]='This field is required. Enter 0 for an amount that does not apply.'
    if errors:raise RequiredFieldsError(errors)
