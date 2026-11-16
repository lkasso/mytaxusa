"""Conservative labeled identity extraction from W-2 text and table cells."""
import re

LABELS={
 'employer':r"(?:box\s*c\s*[-:]?\s*|c\s*)?employer['’]?s?\s+name(?:,?\s*address(?:,?\s*(?:and\s*)?(?:zip\s*code|ZIP))?)?",
 'address':r"(?:box\s*c\s*[-:]?\s*)?employer['’]?s?\s+address",
 'employee_name':r"(?:box\s*e\s*[-:]?\s*|e\s*)?employee['’]?s?\s+(?:first\s+name\s+and\s+initial(?:\s+last\s+name)?(?:\s+suff\.?)?|(?:full\s+)?name)",
 'employee_address':r"(?:box\s*f\s*[-:]?\s*|f\s*)?employee['’]?s?\s+address(?:\s+and\s+zip\s*code)?",
}
STOP=re.compile(r"^(?:[a-f1-9]\s+)?(?:employer|employee|federal|social security|medicare|wages|form w-?2|omb|control number|copy\s+[a-d])",re.I)

def identity_fields(text,cells):
    candidates={k:set() for k in LABELS};eins=set()
    # Tables isolate adjacent form boxes; whole-page text can mix their columns.
    for block in (cells if cells else [text]):
        lines=[line.strip() for line in block.splitlines() if line.strip()]
        for n,line in enumerate(lines):
            ein_label=re.search(r"(?:employer\s+(?:identification\s+(?:number|no\.?)|EIN)|\bEIN\b)(?:\s*\(EIN\))?",line,re.I)
            if ein_label:
                value=line[ein_label.end():].strip(' :')
                if not value and n+1<len(lines):value=lines[n+1]
                match=re.fullmatch(r'(\d{2})\s*-?\s*(\d{7})',value)
                if match:eins.add(match[1]+'-'+match[2])
            for key,label in LABELS.items():
                match=re.fullmatch(label+r'\s*[:\-]?\s*(.*)',line,re.I)
                if not match:continue
                value=match[1].strip()
                subsequent=[]
                for following in lines[n+1:n+4]:
                    if STOP.search(following):break
                    subsequent.append(following)
                if value:candidates[key].add(value[:250])
                elif subsequent:
                    candidates[key].add((' '.join(subsequent) if 'address' in key else subsequent[0])[:250])
                if key=='employee_name' and len(subsequent)>1 and not value:
                    candidates['employee_address'].add(' '.join(subsequent[1:])[:250])
                if key=='employer' and 'address' in line.lower() and len(subsequent)>1:
                    candidates['address'].add(' '.join(subsequent[1:])[:250])
    if not eins:
        # A single conventionally formatted EIN is an acceptable fallback.
        eins=set(re.findall(r'\b\d{2}-\d{7}\b',text))
    fields={k:next(iter(v)) for k,v in candidates.items() if len(v)==1}
    if len(eins)==1:fields['ein']=next(iter(eins))
    return fields
