"""Fill a bundled IRS Form 1040 layout (the 2024 form, used as a practice layout) with the supported practice-return facts."""
from io import BytesIO
from pathlib import Path
from decimal import Decimal
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from .rules import calculate, amount, age_on_year_end, VERSION

TEMPLATE=Path(__file__).resolve().parent.parent/'assets/pdf/form1040-2024.pdf'

def field_values(data, fields):
    values={}
    def put(short,value):
        matches=[key for key in fields if key.endswith('.'+short)]
        if len(matches)!=1:raise ValueError('PDF mapping is ambiguous or missing: '+short)
        values[matches[0]]=str(value)
    def money(short,value):put(short,format(value,'.2f'))
    def check(path):
        states=fields[path].get('/_States_',[])
        values[path]=next(s for s in states if s!='/Off')
    t=calculate(data)
    for key,value in {'f1_04[0]':' '.join(filter(None,[data.get('first'),data.get('middle')])),'f1_05[0]':data.get('last',''),'f1_06[0]':data.get('ssn','').replace('-',''),'f1_10[0]':data.get('address',''),'f1_11[0]':data.get('apt',''),'f1_12[0]':data.get('city',''),'f1_13[0]':data.get('region',''),'f1_14[0]':data.get('zip',''),'f2_33[0]':data.get('occupation',''),'f2_37[0]':data.get('phone','')}.items():put(key,value)
    joint=data.get('status')=='Married Filing Jointly'
    check('topmostSubform[0].Page1[0].FilingStatus_ReadOrder[0].c1_3['+('1' if joint else '0')+']')
    check('topmostSubform[0].Page1[0].c1_5[1]')
    if joint:
        parts=data.get('spouse','').rsplit(' ',1)
        put('f1_07[0]',parts[0]);put('f1_08[0]',parts[1] if len(parts)>1 else '')
        put('f1_09[0]',data.get('spouse_ssn','').replace('-',''))
    dependents=data.get('dependents',[])
    for n,d in enumerate(dependents[:4]):
        for offset,key in enumerate(['name','ssn','relationship']):put(f'f1_{20+n*3+offset:02d}[0]',d.get(key,'').replace('-','') if key=='ssn' else d.get(key,''))
        if data.get('claim_credit')=='Yes':
            short=f'c1_{14+n*2+(0 if age_on_year_end(d.get("dob"))<17 else 1)}[0]'
            check(next(key for key in fields if key.endswith('.'+short)))
    if len(dependents)>4:check('topmostSubform[0].Page1[0].Dependents_ReadOrder[0].c1_13[0]')
    w2=sum((amount(w,'withheld') for w in data.get('w2s',[])),Decimal(0))
    other=amount(data,'interest_withheld')+amount(data,'unemployment_withheld')
    mapped={
      'f1_32[0]':t['wages'],'f1_41[0]':t['wages'],'f1_43[0]':amount(data,'interest'),
      'f1_53[0]':amount(data,'unemployment'),'f1_54[0]':t['income'],'f1_55[0]':0,'f1_56[0]':t['agi'],
      'f1_57[0]':t['deduction'],'f1_59[0]':t['deduction'],'f1_60[0]':t['taxable'],
      'f2_02[0]':t['tax']+t['credits'],'f2_04[0]':t['tax']+t['credits'],
      'f2_05[0]':t['credits'],'f2_07[0]':t['credits'],'f2_08[0]':t['tax'],'f2_10[0]':t['tax'],
      'f2_11[0]':w2,'f2_12[0]':other,'f2_14[0]':w2+other,'f2_15[0]':amount(data,'estimated'),
      'f2_20[0]':amount(data,'extension'),'f2_21[0]':amount(data,'extension'),'f2_22[0]':t['payments'],
      'f2_23[0]':t['refund'],'f2_24[0]':t['refund'],'f2_28[0]':t['owed']}
    for key,value in mapped.items():money(key,value)
    return values

def generate(data):
    reader=PdfReader(TEMPLATE)
    writer=PdfWriter();writer.clone_document_from_reader(reader)
    writer.root_object['/AcroForm'].pop('/XFA',None)
    fields=writer.get_fields()
    values=field_values(data,fields)
    writer.update_page_form_field_values(None,values,auto_regenerate=False)
    # Keep canonical fields and appearances intact; a permanent footer identifies the exercise.
    stamp=BytesIO();c=canvas.Canvas(stamp,pagesize=(612,792))
    c.setFillColorRGB(.6,.05,.05);c.setFont('Helvetica-Bold',9)
    c.drawCentredString(306,780,'MYTAXUSA PRACTICE RETURN - NOT FOR FILING')
    c.drawCentredString(306,10,'MYTAXUSA PRACTICE RETURN - NOT FOR FILING')
    c.save()
    for page in writer.pages:page.merge_page(PdfReader(BytesIO(stamp.getvalue())).pages[0])
    notes=BytesIO();c=canvas.Canvas(notes,pagesize=(612,792));c.setFont('Helvetica-Bold',17)
    c.drawString(40,750,'MyTaxUSA - Practice return details')
    c.setFont('Helvetica',10)
    lines=[
      'NOT FOR FILING. This download uses simplified classroom calculations.',
      'Rule version: '+VERSION,
      'This is not an IRS submission, signed return, or complete tax-return package.',
      'Required official supporting schedules are not generated in this version.',
      'Unemployment is included on Form 1040 line 8 (normally from Schedule 1).',
      'Extension payments are included on line 31 (normally from Schedule 3).',
      'The dependent credit uses simulated eligibility and amounts, not a completed Schedule 8812.',
      'Signature and bank account fields are intentionally left blank.',
      '',
      f'Unemployment compensation: ${amount(data,"unemployment"):,.2f}',
      f'Federal extension payment: ${amount(data,"extension"):,.2f}',
      '', 'Additional dependents (beyond the first four):'
    ]
    for d in data.get('dependents',[])[4:]:
        lines.extend([d.get('name','')[:90],f'SSN: {d.get("ssn","")} | Relationship: {d.get("relationship","")}'])
    if len(data.get('dependents',[]))<=4:lines.append('None')
    for n,line in enumerate(lines):c.drawString(40,720-20*n,line)
    c.save();writer.append(PdfReader(notes))
    writer.add_metadata({'/Title':'MyTaxUSA Practice Form 1040','/Subject':'Not for filing; simplified classroom return'})
    output=BytesIO();writer.write(output);output.seek(0)
    # Verify canonical values survived serialization; missing fields must fail loudly.
    saved=PdfReader(output).get_fields()
    if any(str(saved[key].get('/V',''))!=value for key,value in values.items()):raise ValueError('PDF fields failed verification.')
    output.seek(0)
    return output
