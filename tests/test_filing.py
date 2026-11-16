import io
import tempfile
import unittest
from pathlib import Path
from app import create_app
from reportlab.pdfgen import canvas

def sample_pdf(lines=None):
    output=io.BytesIO()
    page=canvas.Canvas(output)
    for index,line in enumerate(lines or ['Example attachment']):page.drawString(40,800-index*20,line)
    page.save()
    return output.getvalue()

from app.services.rules import calculate, dependent_result
from app.services.diagnostics import evaluate

class FilingTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.config={'TESTING':True,'SECRET_KEY':'test-key','DATABASE':str(Path(self.temp.name)/'test.db'),'DOCUMENT_DIRECTORY':str(Path(self.temp.name)/'documents')}
        self.app=create_app(self.config);self.client=self.app.test_client();self.client.get('/filing/0')
        with self.client.session_transaction() as s:self.csrf=s['csrf'];self.identifier=s['return_id'];self.owner=s['owner']
    def post(self,step,**values):
        return self.client.post(f'/filing/{step}',data={'csrf':self.csrf,'action':'continue',**values})
    def fill(self):
        inputs={0:dict(first='Alex',last='Example',dob='1990-01-01',ssn='000000001',address='123 Example St',city='Example',region='CA',zip='90001',dependent='No',blind='No'),1:dict(status='Single'),4:dict(w2_0_employer='Example Co',w2_0_ein='000000001',w2_0_address='456 Employer St',w2_0_wages='50000',w2_0_withheld='6000'),5:dict(has_interest='Yes',has_unemployment='Yes',interest='200',interest_withheld='0',unemployment='1000',unemployment_withheld='100'),6:dict(unsupported_income='No'),8:dict(needs_itemized='No'),9:dict(claim_credit='No'),10:dict(other_credit_needed='No'),12:dict(estimated='200',extension='0',foreign='No')}
        for step in range(13):self.assertEqual(self.post(step,**inputs.get(step,{})).status_code,302,step)
    def test_supported_return_and_restart(self):
        self.fill()
        summary=self.client.get('/filing/13').get_data(as_text=True)
        for value in ['$51,200.00','$14,600.00','$36,600.00','$4,160.00','$6,300.00','$2,140.00']:self.assertIn(value,summary)
        self.assertEqual(self.client.get('/diagnostics').json['findings'],[])
        self.assertEqual(self.post(13,action='reviewed').status_code,302)
        cookie=self.client.get_cookie('session');restarted=create_app(self.config).test_client();restarted.set_cookie('session',cookie.value)
        self.assertIn('value="Alex"',restarted.get('/filing/0').get_data(as_text=True))
        self.assertIn('14 of 14',restarted.get('/filing/13').get_data(as_text=True))
    def test_scope_blocks_summary_and_legacy(self):
        self.fill()
        self.assertEqual(self.post(6,unsupported_income='Yes').status_code,200)
        store=self.app.extensions['return_store']
        data=store.get(self.identifier,self.owner)[1]
        data['unsupported_income']='Yes'
        store.save(self.identifier,self.owner,data,6)
        response=self.post(13,action='reviewed')
        self.assertEqual(response.status_code,200)
        self.assertIn('SCOPE_UNSUPPORTED',response.get_data(as_text=True))
        self.assertNotIn('$51,200.00',response.get_data(as_text=True))
        self.assertTrue(any(f.code=='LEGACY_UNSUPPORTED' for f in evaluate({'business':'100'})))
        self.assertEqual(self.post(5,interest='NaN').status_code,200)
        self.assertEqual(self.post(5,interest='-1').status_code,200)
        self.assertEqual(self.client.post('/filing/5',data={}).status_code,400)
    def test_intermediate_summaries_show_cross_page_blockers(self):
        for step in (7, 11, 13):
            html = self.client.get(f'/filing/{step}').get_data(as_text=True)
            self.assertIn('Calculation incomplete', html)
            self.assertIn('PERSONAL_INCOMPLETE', html)
            if step==13:
                self.assertIn('Answer the question: Misc: Do you have foreign accounts or trusts?', html)
                self.assertIn('href="/filing/12#foreign"', html)
            else:
                self.assertNotIn('href="/filing/12#foreign"', html)
            self.assertIn('href="/filing/0#personal"', html)

    def test_optional_interest_and_unemployment(self):
        self.assertEqual(self.post(5,has_interest='No',has_unemployment='No').status_code,302)
        data=self.app.extensions['return_store'].get(self.identifier,self.owner)[1]
        self.assertEqual(data['interest'],'0.00')
        self.assertEqual(self.post(5,has_interest='Yes',has_unemployment='No').status_code,200)
        self.assertEqual(self.post(5,has_interest='Yes',has_unemployment='No',interest='100',interest_withheld='0').status_code,302)
        self.assertEqual(self.post(5,has_interest='No',has_unemployment='No',interest='999',interest_withheld='999').status_code,302)
        data=self.app.extensions['return_store'].get(self.identifier,self.owner)[1]
        self.assertEqual(data['interest'],'0.00')
        self.assertEqual(calculate(data)['income'],0)

    def test_income_summary_does_not_require_future_answers(self):
        self.fill()
        store=self.app.extensions['return_store']
        data=store.get(self.identifier,self.owner)[1]
        for key in ['needs_itemized','claim_credit','other_credit_needed','foreign']:data[key]=''
        store.save(self.identifier,self.owner,data,7)
        html=self.client.get('/filing/7').get_data(as_text=True)
        self.assertNotIn('Calculation incomplete',html)
        self.assertIn('$51,200.00',html)
        self.assertNotIn('/filing/8#needs_itemized',html)
        self.assertIn('/filing/8#needs_itemized',self.client.get('/filing/13').get_data(as_text=True))

    def test_saved_return_completeness_and_status_changes(self):
        self.fill()
        store=self.app.extensions['return_store']
        data=store.get(self.identifier,self.owner)[1]
        data['address']=''
        store.save(self.identifier,self.owner,data,0)
        self.assertEqual(self.client.get('/return/form-1040.pdf').status_code,409)
        self.assertTrue(any(f['field']=='address' for f in self.client.get('/diagnostics').json['findings']))
        self.post(1,status='Married Filing Jointly',spouse='Sam Example',spouse_ssn='000000003',spouse_dob='1991-01-01')
        self.post(1,status='Single',spouse='Sam Example',spouse_ssn='000000003',spouse_dob='1991-01-01')
        self.assertEqual(store.get(self.identifier,self.owner)[1]['spouse'],'')
        self.assertEqual(self.post(4,action='back',w2_0_wages='invalid').status_code,302)
        self.assertEqual(store.get(self.identifier,self.owner)[1]['w2s'][0]['wages'],'50000.00')
        self.client.get('/returns')
        self.client.post('/returns/new',data={'csrf':self.csrf})
        self.assertEqual(self.client.get('/return/form-1040.pdf').status_code,409)

    def test_unsupported_choices_are_disabled(self):
        from html.parser import HTMLParser
        class Options(HTMLParser):
            def __init__(self):super().__init__();self.options=[]
            def handle_starttag(self,tag,attrs):
                if tag=='option':self.options.append(dict(attrs))
        for step in [0,1,6,8,10,12]:
            parser=Options();parser.feed(self.client.get(f'/filing/{step}').get_data(as_text=True))
            disabled=[option for option in parser.options if 'disabled' in option]
            self.assertTrue(disabled,step)
        html=self.client.get('/filing/9').get_data(as_text=True)
        parser=Options();parser.feed(html)
        self.assertFalse(any('disabled' in option for option in parser.options))
        self.assertEqual(self.post(1,status='Head of Household').status_code,200)

    def test_required_fields_block_continue(self):
        for step in (0,1,5,6,8,9,10,12):
            response=self.post(step)
            self.assertEqual(response.status_code,200,step)
            self.assertIn('highlighted required fields',response.get_data(as_text=True))
        for step, values in [(1,dict(status='Married Filing Jointly')),(2,dict(dependent_0_name='Child')),(4,dict(w2_0_employer='Employer'))]:
            self.assertEqual(self.post(step,**values).status_code,200,step)
        self.assertEqual(self.post(2).status_code,302)
        self.assertEqual(self.post(4).status_code,302)
        self.assertEqual(self.post(5,has_interest='No',has_unemployment='No').status_code,302)
        self.assertEqual(self.post(0,action='back').status_code,302)
        html=self.client.get('/filing/6').get_data(as_text=True)
        self.assertIn('name="unsupported_income" required',html)

    def test_inline_findings_are_not_duplicated(self):
        for step in (0,1,6,8,9,10,12):
            html=self.client.get(f'/filing/{step}').get_data(as_text=True)
            self.assertNotIn('Checks to complete',html,step)
            self.assertIn('data-field-errors=',html)
        html=self.client.get('/filing/13').get_data(as_text=True)
        self.assertIn('Return review',html)
        self.assertIn('PERSONAL_INCOMPLETE',html)

    def test_field_error_mapping(self):
        from app.services.field_errors import field_errors
        errors = field_errors({}, evaluate({}), [])
        self.assertIn('first', errors)
        self.assertIn('ssn', errors)
        self.assertIn('foreign', errors)
        self.assertNotIn('middle', errors)
        dependent = {'name':'Child','dob':'2015-01-01'}
        data = {'dependents':[dependent], 'w2s':[{'employer':'Example'}]}
        errors = field_errors(data, evaluate(data), [])
        self.assertIn('dependent_0_months', errors)
        self.assertIn('w2_0_ein', errors)
        self.assertNotIn('dependent_1_name', errors)
        html = self.client.get('/filing/0').get_data(as_text=True)
        self.assertIn('data-field-errors=', html)
        self.assertIn('/static/js/filing.js', html)

    def test_dependent_rules(self):
        row=dict(name='Child',dob='2015-01-01',ssn='000000002',relationship='Child',months='12',student='No',own_support='No',resident='Yes',joint_return='No')
        self.assertEqual(dependent_result(row),'eligible')
        data=dict(status='Single',claim_credit='Yes',dependents=[row],w2s=[dict(wages='50000',withheld='6000')])
        self.assertEqual(calculate(data)['credits'],2000)
        self.assertEqual(calculate(data)['tax'],2016)
        self.assertEqual(dependent_result({**row,'months':'6'}),'ineligible')
        self.assertEqual(dependent_result({**row,'own_support':''}),'needs_information')
        self.assertEqual(dependent_result({**row,'dob':'2003-01-01','student':'Yes'}),'eligible')
        self.assertEqual(calculate({**data,'w2s':[]})['credits'],0)
    def test_clear_return_removes_w2_even_from_stale_tab(self):
        self.client.post('/documents/upload',data={'csrf':self.csrf,'form_type':'W-2','document':(io.BytesIO(sample_pdf(['Form W-2','1 Wages, tips, other compensation 100.00'])),'w2.pdf')},headers={'Accept':'application/json'})
        docs=self.app.extensions['documents']
        attachment=docs.list(self.identifier,self.owner)[0]
        file=docs.directory/attachment['stored_name']
        self.assertTrue(file.exists())
        self.client.post('/returns/new',data={'csrf':self.csrf,'name':'Other return'})
        with self.client.session_transaction() as session:other=session['return_id']
        response=self.client.post('/filing/reset',data={'csrf':self.csrf,'return_id':self.identifier})
        self.assertEqual(response.status_code,302)
        self.assertTrue(response.location.endswith('/welcome'))
        self.assertFalse(file.exists())
        store=self.app.extensions['return_store']
        self.assertIsNone(store.get(self.identifier,self.owner))
        self.assertIsNotNone(store.get(other,self.owner))
        with store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM documents WHERE id=?',(attachment['id'],)).fetchone()[0],0)
        self.assertEqual(self.client.get('/documents/'+attachment['id']).status_code,404)
        self.assertNotIn('w2.pdf',self.client.get('/filing/4').get_data(as_text=True))
        self.assertEqual(self.client.get('/filing/4').headers['Cache-Control'],'no-store')

    def test_typed_form_uploads(self):
        for form_type, step in [('W-2',4),('1099-INT',5),('1099-G',5),('1040-ES',12),('4868',12)]:
            html=self.client.get(f'/filing/{step}').get_data(as_text=True)
            self.assertIn('Upload '+form_type,html)
            response=self.client.post('/documents/upload',data={'csrf':self.csrf,'form_type':form_type,'document':(io.BytesIO(sample_pdf()),form_type+'.pdf')},headers={'Accept':'application/json'})
            self.assertEqual(response.status_code,201)
            self.assertEqual(response.json['document']['form_type'],form_type)
        documents=self.app.extensions['documents'].list(self.identifier,self.owner)
        self.assertEqual(len(documents),5)
        data=self.app.extensions['return_store'].get(self.identifier,self.owner)[1]
        self.assertEqual(data['w2s'],[])
        self.assertNotIn('interest',data)
        self.assertEqual(self.client.post('/documents/upload',data={'csrf':self.csrf,'form_type':'invalid'}).status_code,400)
        self.assertEqual(self.client.post('/documents/upload',data={}).status_code,400)

    def test_form1040_download(self):
        from pypdf import PdfReader
        self.assertEqual(self.client.get('/return/form-1040.pdf').status_code,409)
        self.fill()
        response=self.client.get('/return/form-1040.pdf')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.mimetype,'application/pdf')
        reader=PdfReader(io.BytesIO(response.data));fields=reader.get_fields()
        def field(short):return next(value for key,value in fields.items() if key.endswith('.'+short))
        self.assertEqual(field('f1_04[0]')['/V'],'Alex')
        self.assertEqual(field('f1_32[0]')['/V'],'50000.00')
        self.assertEqual(field('f1_54[0]')['/V'],'51200.00')
        self.assertEqual(field('f2_22[0]')['/V'],'6300.00')
        self.assertEqual(field('f2_24[0]')['/V'],'2140.00')
        self.assertEqual(len(reader.pages),3)
        self.assertNotIn('/XFA',reader.trailer['/Root']['/AcroForm'])
        # Page widgets must inherit the same canonical values and have rendered appearances.
        matched=0
        for page in reader.pages[:2]:
            for ref in page.get('/Annots',[]):
                widget=ref.get_object()
                if widget.get('/Subtype')!='/Widget':continue
                current=widget
                while '/V' not in current and '/Parent' in current:current=current['/Parent']
                if current.get('/V') not in (None,'','/Off'):
                    self.assertIn('/AP',widget)
                    self.assertIn('/N',widget['/AP'])
                    matched+=1
        self.assertGreater(matched,20)
        stranger=self.app.test_client()
        self.assertEqual(stranger.get('/return/form-1040.pdf').status_code,409)

    def test_w2_standard_compact_identity_labels(self):
        from app.services.w2_identity import identity_fields
        cells=["bEmployer identification number (EIN)\n123456789", "cEmployer’s name, address, and ZIP code\nExample Company\n123 Office Road\nExample CA 90001", "eEmployee’s first name and initial Last name\nAlex Example", "f Employee’s address and ZIP code\n456 Home Road\nExample CA 90002"]
        fields=identity_fields('\n'.join(cells),cells)
        self.assertEqual(fields['ein'],'12-3456789')
        self.assertEqual(fields['employer'],'Example Company')
        self.assertEqual(fields['employee_name'],'Alex Example')
        self.assertIn('123 Office Road',fields['address'])
        self.assertIn('456 Home Road',fields['employee_address'])
        html=self.client.get('/filing/4').get_data(as_text=True)
        self.assertIn('w2_0_document_id',html)

    def test_w2_identity_extraction_and_employee_persistence(self):
        from app.services.extraction import extract
        path=Path(self.temp.name)/'identity.pdf'
        path.write_bytes(sample_pdf(['Form W-2 2026',"b Employer identification number (EIN)",'123456789',"c Employer name, address and ZIP code",'Example Employer','123 Business Street','Example CA 90001',"e Employee name",'Alex Example',"f Employee address and ZIP code",'45 Home Street','Example CA 90002','1 Wages, tips, other compensation 50000.00']))
        fields=extract(path,'W-2')['fields']
        self.assertEqual(fields['ein'],'12-3456789')
        self.assertEqual(fields['employer'],'Example Employer')
        self.assertIn('123 Business Street',fields['address'])
        self.assertEqual(fields['employee_name'],'Alex Example')
        self.assertIn('45 Home Street',fields['employee_address'])
        self.assertEqual(self.post(4,w2_0_employer='Example',w2_0_ein='12-3456789',w2_0_address='Office',w2_0_wages='1',w2_0_withheld='0',w2_0_employee_name='Alex Example',w2_0_employee_address='45 Home Street').status_code,302)
        saved=self.app.extensions['return_store'].get(self.identifier,self.owner)[1]
        self.assertEqual(saved['w2s'][0]['employee_name'],'Alex Example')
        self.assertNotIn('first',saved)

    def test_1099_separate_currency_lines_and_blank_boxes(self):
        from app.services.extraction import extract
        path=Path(self.temp.name)/'1099.pdf'
        path.write_bytes(sample_pdf(['Form 1099-INT','1 Interest income','$','1,250.00','4 Federal income tax withheld','$','0.00']))
        result=extract(path,'1099-INT')
        self.assertEqual(result['fields']['interest'],'1250.00')
        self.assertEqual(result['fields']['interest_withheld'],'0.00')
        path.write_bytes(sample_pdf(['Form 1099-INT','1 Interest income','$','2 Early withdrawal penalty','$','4 Federal income tax withheld','$']))
        result=extract(path,'1099-INT')
        self.assertEqual(result['fields'],{})
        self.assertTrue(any('Box 1' in w and 'blank' in w for w in result['warnings']))
        self.assertTrue(any('Box 4' in w and 'blank' in w for w in result['warnings']))
        path.write_bytes(sample_pdf(['Form 1099-G','1 Unemployment compensation','$','3,500.00','4 Federal income tax withheld','$','350.00']))
        result=extract(path,'1099-G')
        self.assertEqual(result['fields']['unemployment'],'3500.00')
        self.assertEqual(result['fields']['unemployment_withheld'],'350.00')

    def test_pdf_extraction_and_image_rejection(self):
        from app.services.extraction import extract
        for kind,lines,key,value in [
            ('W-2',['Form W-2 2026','1 Wages, tips, other compensation 50,000.00','2 Federal income tax withheld 0.00','Employer EIN 12-3456789'],'wages','50000.00'),
            ('1099-INT',['Form 1099-INT 2026','1 Interest income 125.50'],'interest','125.50'),
            ('1099-G',['Form 1099-G 2026','1 Unemployment compensation 5,000.00'],'unemployment','5000.00')]:
            response=self.client.post('/documents/upload',data={'csrf':self.csrf,'form_type':kind,'document':(io.BytesIO(sample_pdf(lines)),kind+'.pdf')},headers={'Accept':'application/json'})
            self.assertEqual(response.status_code,201)
            self.assertEqual(response.json['extraction']['fields'][key],value)
            if kind=='W-2':self.assertEqual(response.json['extraction']['fields']['withheld'],'0.00')
            identifier=response.json['document']['id']
            self.assertEqual(self.client.post(f'/documents/{identifier}/extract',data={'csrf':self.csrf}).status_code,200)
            stranger=self.app.test_client();stranger.get('/filing/0')
            with stranger.session_transaction() as session:token=session['csrf']
            self.assertEqual(stranger.post(f'/documents/{identifier}/extract',data={'csrf':token}).status_code,404)
        image=self.client.post('/documents/upload',data={'csrf':self.csrf,'form_type':'W-2','document':(io.BytesIO(b'\x89PNG\r\n\x1a\n'),'scan.png')})
        self.assertEqual(image.status_code,400)
        path=Path(self.temp.name)/'conflict.pdf'
        path.write_bytes(sample_pdf(['W-2','1 Wages, tips, other compensation 100.00','1 Wages, tips, other compensation 200.00']))
        result=extract(path,'W-2')
        self.assertNotIn('wages',result['fields'])
        self.assertTrue(any('Conflicting' in warning for warning in result['warnings']))
        path.write_bytes(sample_pdf(['Not a tax form']))
        self.assertEqual(extract(path,'1099-INT')['fields'],{})
        output=io.BytesIO();page=canvas.Canvas(output);page.showPage();page.save();path.write_bytes(output.getvalue())
        self.assertIn('No readable text',extract(path,'W-2')['warnings'][0])
        self.assertEqual(self.app.extensions['return_store'].get(self.identifier,self.owner)[1]['w2s'],[])

    def test_documents_prior_year_and_isolation(self):
        self.fill()
        response=self.client.post('/return-resources',data={'csrf':self.csrf,'document':(io.BytesIO(sample_pdf()),'sample.pdf')},content_type='multipart/form-data')
        self.assertEqual(response.status_code,302)
        docs=self.app.extensions['documents'];attached=docs.list(self.identifier,self.owner)[0]
        with self.client.get('/documents/'+attached['id']) as download:
            self.assertTrue(download.data.startswith(b'%PDF-'))
        bad=self.client.post('/return-resources',data={'csrf':self.csrf,'document':(io.BytesIO(b'fake'),'sample.pdf')},content_type='multipart/form-data')
        self.assertIn('File contents must match',bad.get_data(as_text=True))
        stranger=self.app.test_client();stranger.get('/filing/0')
        self.assertEqual(stranger.get('/documents/'+attached['id']).status_code,404)
        store=self.app.extensions['return_store'];prior=store.create(self.owner,'Prior year')
        store.save(prior,self.owner,dict(status='Married Filing Jointly',w2s=[dict(wages='20000')]),0)
        before=store.get(self.identifier,self.owner)[1]
        docs.link_prior(self.identifier,self.owner,prior)
        codes={f['code'] for f in self.client.get('/diagnostics').json['findings']}
        self.assertIn('PRIOR_STATUS_CHANGED',codes);self.assertIn('PRIOR_INCOME_CHANGED',codes)
        self.assertEqual(before,store.get(self.identifier,self.owner)[1])
        with self.assertRaises(ValueError):docs.link_prior(self.identifier,self.owner,self.identifier)
        other=store.create('different-owner','Other')
        with self.assertRaises(KeyError):docs.link_prior(self.identifier,self.owner,other)
        self.client.post(f'/returns/{self.identifier}/delete',data={'csrf':self.csrf})
        self.assertFalse((docs.directory/attached['stored_name']).exists())
        self.assertIsNone(store.get(self.identifier,self.owner))

if __name__=='__main__':unittest.main()
