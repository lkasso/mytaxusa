"""Conservative local parsing of text PDFs. No OCR or network calls."""
import re
from decimal import Decimal
import pdfplumber
from .w2_identity import identity_fields

MAX_PAGES=20
LABELS={
 'W-2':{
  'wages':r'(?:1\s*)?wages,?\s*tips,?\s*(?:and\s*)?other compensation',
  'withheld':r'(?:2\s*)?federal income tax withheld',
  'ss_wages':r'(?:3\s*)?social security wages',
  'ss_tax':r'(?:4\s*)?social security tax withheld',
  'medicare_wages':r'(?:5\s*)?medicare wages and tips',
  'medicare_tax':r'(?:6\s*)?medicare tax withheld'},
 '1099-INT':{'interest':r'(?:1\s*)?interest income','interest_withheld':r'(?:4\s*)?federal income tax withheld'},
 '1099-G':{'unemployment':r'(?:1\s*)?unemployment compensation','unemployment_withheld':r'(?:4\s*)?federal income tax withheld'},
}
MONEY=re.compile(r'^\s*\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d{2})?\s*$')

def validate_pdf(path):
    try:
        with pdfplumber.open(path) as pdf:
            if not pdf.pages or len(pdf.pages)>MAX_PAGES:raise ValueError('PDF must contain between 1 and 20 pages.')
    except ValueError:raise
    except Exception as exc:raise ValueError('Unable to open this PDF. Use a valid, unencrypted PDF.') from exc

def extract(path, form_type):
    if form_type not in LABELS:return {'fields':{},'warnings':['This document is attachment-only; enter payment amounts manually.']}
    candidates={key:set() for key in LABELS[form_type]};warnings=[]
    try:
        with pdfplumber.open(path) as pdf:
            if len(pdf.pages)>MAX_PAGES:raise ValueError('PDF exceeds 20 pages.')
            texts=[];cells=[]
            for page in pdf.pages:
                texts.append(page.extract_text(layout=False) or '')
                for table in page.extract_tables():
                    for row in table:
                        cells.extend(cell for cell in row if cell)
            text='\n'.join(texts)
            if not text.strip():return {'fields':{},'warnings':['No readable text found. Scanned/image-only PDFs require manual entry; OCR is not enabled.']}
            marker={'W-2':r'\bw\s*-?\s*2\b','1099-INT':r'\b1099\s*[-–—]?\s*int\b','1099-G':r'\b1099\s*[-–—]?\s*g\b'}[form_type]
            if not re.search(marker,text,re.I):return {'fields':{},'warnings':[f'This PDF could not be identified as {form_type}. Check its document type or enter it manually.']}
            # Match labels within individual cells first, with conservative line-based fallback.
            for block in cells+[text]:
                lines=block.splitlines()
                for index,line in enumerate(lines):
                    for key,label in LABELS[form_type].items():
                        match=re.search(label,line,re.I)
                        if not match:continue
                        remainder=line[match.end():].strip(' :')
                        value=MONEY.fullmatch(remainder)
                        if not value and remainder in ('','$'):
                            following=[part.strip() for part in lines[index+1:index+4] if part.strip()]
                            if following and following[0]=='$':following=following[1:]
                            if following:value=MONEY.fullmatch(following[0])
                        if value:
                            number=Decimal(value[1].replace(',','')+(value[2] or ''))
                            candidates[key].add(str(number.quantize(Decimal('.01'))))
            fields={key:next(iter(values)) for key,values in candidates.items() if len(values)==1}
            for key,values in candidates.items():
                if len(values)>1:warnings.append(f'Conflicting values for {key}; enter this field manually.')
            if form_type=='W-2':
                fields.update(identity_fields(text,cells))
            years=set(re.findall(r'\b20(?:2\d|3\d)\b',text))
            if years and years!={'2026'}:warnings.append('Document year may differ from the fixed 2026 practice rules. Review it before applying.')
            if form_type in ['1099-INT','1099-G']:
                for key,label in [('interest','Box 1 — Interest income'),('interest_withheld','Box 4 — Federal income tax withheld')] if form_type=='1099-INT' else [('unemployment','Box 1 — Unemployment compensation'),('unemployment_withheld','Box 4 — Federal income tax withheld')]:
                    if key not in fields:
                        warnings.append(label+' is blank or could not be read. Enter the amount manually; use 0 only if you confirm none applies.')
            elif not fields:warnings.append('No fields could be extracted reliably from this layout. Enter the values manually.')
            warnings.append('Review all extracted values against the PDF. Missing fields remain blank; nothing has been saved to your return.')
            return {'fields':fields,'warnings':warnings}
    except Exception:
        return {'fields':{},'warnings':['This PDF could not be parsed. Enter its values manually.']}
