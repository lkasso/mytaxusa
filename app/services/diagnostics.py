"""Structured findings, recalculated from saved facts rather than persisted flags."""
from app.validation.required import required_fields
from app.services.filing import PAGES
from decimal import Decimal
from dataclasses import asdict, dataclass
from app.services.rules import amount, calculate, dependent_result, age_on_year_end, VERSION

@dataclass
class Finding:
    code: str
    severity: str
    field: str
    message: str
    step: int
    @property
    def fix_url(self): return f'/filing/{self.step}#{self.field}'
    def to_dict(self): return {**asdict(self),'fix_url':self.fix_url,'rule_version':VERSION}

LEGACY=['dividends','capital','retirement','social','business','rental','other_income','crypto_gain','ira','student','educator','hsa','car','other_adjustments','education_credit','care_credit','child_credit','energy_credit','earned_credit','other_credits','refundable','base_tax','other_tax','extra_withholding','mortgage','donations','other_donations','medical','taxes_paid','other_itemized']

def evaluate(data, prior=None, completed=()):
    findings=[]
    def add(code,severity,field,message,step):findings.append(Finding(code,severity,field,message,step))
    if not all(data.get(k) for k in ['first','last','dob','ssn','status']):add('PERSONAL_INCOMPLETE','error','personal','Complete taxpayer name, birth date, sample SSN, and filing status.',0)
    if data.get('status') and data['status'] not in ['Single','Married Filing Jointly']:add('STATUS_UNSUPPORTED','error','status','This demo supports Single and Married Filing Jointly only.',1)
    if data.get('status')=='Married Filing Jointly' and not all(data.get(k) for k in ['spouse','spouse_ssn','spouse_dob']):add('SPOUSE_INCOMPLETE','error','spouse','Enter spouse name, sample SSN, and birth date.',1)
    for key in ['dob','spouse_dob']:
        if data.get(key):
            age=age_on_year_end(data[key])
            if age is None or age<0:add('DOB_INVALID','error',key,'Birth date must be valid and on or before the practice year end.',0 if key=='dob' else 1)
            elif age>=65:add('AGE_ADDITION_UNSUPPORTED','error',key,'Additional standard deductions for age 65 or older are outside this demo.',1 if key=='spouse_dob' else 0)
    if data.get('blind')=='Yes' or data.get('dependent')=='Yes':add('FILER_SITUATION_UNSUPPORTED','error','personal','Blind filers and filers claimed by someone else are outside this demo.',0)
    for key,step in [('dependent',0),('blind',0),('unsupported_income',6),('needs_itemized',8),('claim_credit',9),('other_credit_needed',10),('foreign',12)]:
        if not data.get(key):
            questions = {
                'dependent': 'Personal: Can someone claim you as a dependent?',
                'blind': 'Personal: Are you legally blind?',
                'unsupported_income': 'Income: Do you have income other than W-2 wages, taxable interest, or unemployment?',
                'needs_itemized': 'Deductions: Do you need to itemize deductions?',
                'claim_credit': 'Credits: Would you like to claim the supported dependent credit?',
                'other_credit_needed': 'Credits: Do you need another credit or adjustment?',
                'foreign': 'Misc: Do you have foreign accounts or trusts?',
            }
            add('ANSWER_REQUIRED','error',key,'Answer the question: ' + questions[key],step)
    for key,step in [('unsupported_income',6),('needs_itemized',8),('other_credit_needed',10),('foreign',12)]:
        if data.get(key)=='Yes':add('SCOPE_UNSUPPORTED','error',key,'This situation is outside the supported simple federal return scope.',step)
    if data.get('crypto')=='Yes' or data.get('deduction_method')=='Itemized' or any(amount(data,k)!=0 for k in LEGACY):
        add('LEGACY_UNSUPPORTED','error','legacy','This saved return contains amounts from the earlier wider scope. Create a new blank return to calculate a supported return.',0)
    seen=set()
    for field,value in [('ssn',data.get('ssn')),('spouse_ssn',data.get('spouse_ssn'))]+[(f'dependents[{n}].ssn',d.get('ssn')) for n,d in enumerate(data.get('dependents',[]))]:
        if value:
            normalized=''.join(c for c in value if c.isdigit())
            if len(normalized)!=9:add('SSN_FORMAT','error',field,'Enter a nine-digit fictional SSN.',2 if field.startswith('dependents') else 1 if field=='spouse_ssn' else 0)
            elif normalized in seen:add('SSN_DUPLICATE','error',field,'Each person must have a different sample SSN.',2 if field.startswith('dependents') else 1 if field=='spouse_ssn' else 0)
            seen.add(normalized)
    for n,d in enumerate(data.get('dependents',[])):
        if not any(d.values()):continue
        result=dependent_result(d)
        if result!='eligible' or not d.get('ssn'):
            add('DEPENDENT_INCOMPLETE' if result=='needs_information' or not d.get('ssn') else 'DEPENDENT_UNSUPPORTED','error',f'dependents[{n}]','Complete the qualifying-child questions. This demo supports qualifying children only; qualifying-relative and exception cases are outside scope.',2)
    for n,w in enumerate(data.get('w2s',[])):
        if not any(w.values()):continue
        if not w.get('employer') or not w.get('ein') or not w.get('wages') or not w.get('withheld'):add('W2_INCOMPLETE','error',f'w2s[{n}]','Enter employer, EIN, wages, and federal withholding for each W-2.',4)
    threshold=400000 if data.get('status')=='Married Filing Jointly' else 200000
    if data.get('claim_credit')=='Yes' and calculate(data)['income']>threshold:add('CREDIT_PHASEOUT_UNSUPPORTED','error','claim_credit','Credit phaseout calculations are outside this demo.',9)
    for topic in ['interest','unemployment']:
        if data.get('has_'+topic) not in ['Yes','No']:
            add('ANSWER_REQUIRED','error','has_'+topic,'Tell us whether you received '+topic+' income.',5)
        elif data.get('has_'+topic)=='Yes' and any(data.get(k,'')=='' for k in [topic,topic+'_withheld']):
            for key in [topic,topic+'_withheld']:
                if data.get(key,'')=='':add('INCOME_INCOMPLETE','error',key,'Enter this amount, or 0 if none was withheld.',5)
    # Final review also validates required facts in older or directly opened saved returns.
    for page, definition in enumerate(PAGES):
        for field in sorted(required_fields(page,data)):
            if data.get(field,'')=='' and not any(f.field==field for f in findings):
                add('REQUIRED_FIELD','error',field,'Complete the required field: '+field.replace('_',' ')+'.',page)
    if prior:
        if data.get('status')!=prior.get('status'):add('PRIOR_STATUS_CHANGED','warning','status','Filing status differs from the linked prior-year return. Review the change.',1)
        if len(data.get('dependents',[]))!=len(prior.get('dependents',[])):add('PRIOR_DEPENDENTS_CHANGED','warning','dependents','Dependent count differs from the linked prior-year return.',2)
        old=calculate(prior)['income'];new=calculate(data)['income']
        if abs(new-old)>max(1000,abs(old)*Decimal('.25')):add('PRIOR_INCOME_CHANGED','warning','income','Income differs from the linked prior-year return by more than 25% and $1,000.',5)
    return findings
