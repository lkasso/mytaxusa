import sys,tempfile,threading,io
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from app import create_app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
from reportlab.pdfgen import canvas
with tempfile.TemporaryDirectory() as directory:
 app=create_app({'DATABASE':str(Path(directory)/'db'),'DOCUMENT_DIRECTORY':str(Path(directory)/'documents'),'TESTING':True})
 server=make_server('127.0.0.1',0,app,threaded=True);threading.Thread(target=server.serve_forever,daemon=True).start()
 base=f'http://127.0.0.1:{server.server_port}'
 with sync_playwright() as pw:
  browser=pw.chromium.launch();page=browser.new_page();page.on('dialog',lambda dialog:dialog.accept());errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
  def advance(step):
   page.locator('button[value=continue]').click();page.wait_for_url(base+f'/filing/{step}')
  page.goto(base);page.get_by_role('link',name='Sign in',exact=True).first.click();page.get_by_text('Begin Tax Return',exact=True).click();page.get_by_role('button',name='Create blank return').click();page.wait_for_url(base+'/filing/0')
  page.locator('button[value=continue]').click();assert page.url.endswith('/filing/0')
  for key,value in dict(first='Alex',last='Example',ssn='000000001',dob='1990-01-01',address='123 Sample St',city='Example',region='CA',zip='90001').items():page.locator(f'[name="{key}"]').fill(value)
  for key in ['dependent','blind']:page.locator(f'[name="{key}"]').select_option('No')
  advance(1);page.locator('[name="status"]').select_option('Single');advance(2)
  assert page.locator('.dependent-card:visible').count()==0
  page.get_by_role('button',name='+ Add dependent').click();assert page.locator('.dependent-card:visible').count()==1
  page.get_by_role('button',name='Remove dependent').first.click();assert page.locator('.dependent-card:visible').count()==0
  advance(3);advance(4)
  assert page.locator('.w2-card:visible').count()==0
  page.get_by_role('button',name='Enter manually',exact=True).click()
  for key,value in dict(employer='Example Company',ein='120000001',address='456 Business St',wages='50000',withheld='6000').items():page.locator(f'[name="w2_0_{key}"]').fill(value)
  page.get_by_role('button',name='+ Add employer').click();assert page.locator('.w2-card:visible').count()==2
  page.locator('.w2-card').nth(1).get_by_role('button',name='Remove employer').click()
  advance(5)
  for key in ['has_interest','has_unemployment']:page.locator(f'[name="{key}"]').select_option('No')
  advance(6);page.locator('[name="unsupported_income"]').select_option('No');advance(7)
  assert 'Calculation incomplete' not in page.locator('main').inner_text()
  advance(8);page.locator('[name="needs_itemized"]').select_option('No');advance(9);page.locator('[name="claim_credit"]').select_option('No');advance(10);page.locator('[name="other_credit_needed"]').select_option('No');advance(11);advance(12)
  for key in ['estimated','extension']:page.locator(f'[name="{key}"]').fill('0')
  page.locator('[name="foreign"]').select_option('No');advance(13)
  assert page.get_by_role('link',name='Download Form 1040 (PDF)').is_visible()
  with page.expect_download() as download:page.get_by_role('link',name='Download Form 1040 (PDF)').click()
  assert Path(download.value.path()).read_bytes().startswith(b'%PDF-')
  # Import into another employer without overwriting the original.
  page.goto(base+'/filing/4');page.get_by_role('button',name='Upload a PDF',exact=True).click()
  out=io.BytesIO();pdf=canvas.Canvas(out)
  for n,line in enumerate(['Form W-2 2026','1 Wages, tips, other compensation 10000.00','2 Federal income tax withheld 500.00','Employer EIN 12-3456789']):pdf.drawString(30,800-n*20,line)
  pdf.save()
  page.locator('.document-upload [type=file]').set_input_files({'name':'w2.pdf','mimeType':'application/pdf','buffer':out.getvalue()})
  page.get_by_role('button',name='Upload W-2',exact=True).click();page.locator('.w2-import-status').wait_for()
  assert page.locator('[name="w2_1_wages"]').input_value()=='10000.00'
  assert page.locator('[name="w2_0_wages"]').input_value()=='50000.00'
  for key,value in dict(employer='Second Company',address='Other Street').items():page.locator(f'[name="w2_1_{key}"]').fill(value)
  advance(5)
  page.locator('[name="has_interest"]').select_option('Yes')
  page.locator('.income-topic[data-topic=interest] [data-method=upload]').click()
  out=io.BytesIO();pdf=canvas.Canvas(out);pdf.drawString(30,800,'Form 1099-INT 2026');pdf.drawString(30,780,'1 Interest income 100.00');pdf.save()
  upload=page.locator('.income-upload[data-topic=interest]');upload.locator('[type=file]').set_input_files({'name':'interest.pdf','mimeType':'application/pdf','buffer':out.getvalue()});upload.get_by_role('button',name='Upload 1099-INT').click()
  page.get_by_role('button',name='Apply reviewed values to form').wait_for();page.get_by_role('button',name='Apply reviewed values to form').click()
  assert page.locator('[name=interest]').input_value()=='100.00'
  page.locator('[name=interest_withheld]').fill('0');advance(6)
  page.goto(base+'/filing/13');assert '$60,100.00' in page.locator('main').inner_text()
  assert not errors,errors
  browser.close();print('PASS: browser full manual flow, add/remove cards, skip income, PDF review/import, saved totals and Form 1040 download; no JavaScript errors.')
 server.shutdown()
