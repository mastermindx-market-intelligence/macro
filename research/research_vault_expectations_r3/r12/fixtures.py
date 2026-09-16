"""Synthetic original documents for the review-only evidence bridge."""
from pathlib import Path
import hashlib, importlib.util, subprocess
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

ROOT = Path(__file__).resolve().parents[1]
COMPOSITE_SHA256 = '58bfdaf91f1cb7f9a4f7e1f700bd90be3269fe9ea7d6cc156661a9a456b89d6f'

def load_corpus():
    path=ROOT/'upstream/corpus_review.py'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=COMPOSITE_SHA256:
        raise ValueError('Unqualified composite corpus: review refused')
    spec=importlib.util.spec_from_file_location('review_corpus',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def make_source(path: Path, margin: int=28):
    """Programmatically authored fixture; no outside research is reproduced."""
    c=canvas.Canvas(str(path),pagesize=letter,invariant=1)
    c.setTitle('Synthetic industrial review - not real investment research')
    for page in (1,2):
        c.setFont('Helvetica-Bold',15)
        c.drawString(54,734,'SYNTHETIC TEST DOCUMENT - NOT MARKET RESEARCH')
        c.setFont('Helvetica',11)
        lines=(['Industrial operations review','Fictional publisher: Example Research Laboratory',
                'All companies, forecasts and narratives in this document are invented.',
                'This first page discusses general operating conditions.'] if page==1 else [
                'Fictional business: Orionquartz Robotics',
                f'Orionquartz margin outlook for FY2027 is revised from 31% to {margin}%.',
                'The assumed reason is additional factory commissioning expense.',
                'This is not a change in the revenue estimate and is not a stock signal.',
                'The statement is conditional on the fictional factory schedule.',
                'No real institution, issuer or investment recommendation is represented.'])
        for i,line in enumerate(lines): c.drawString(54,690-i*24,line)
        c.drawString(54,40,f'Controlled fixture | Page {page} of 2')
        c.showPage()
    c.save()
    run=subprocess.run(['pdftotext','-layout',str(path),'-'],capture_output=True,check=True,timeout=10)
    body=run.stdout.decode('utf-8')
    return {'body':body,'pdf_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'body_sha256':hashlib.sha256(body[:60000].encode()).hexdigest(),'pages':2,
            'char_count':len(body),'text_layer':'text'}

def catalog_item(doc_id='example-report'):
    return {'id':doc_id,'title':'Industrial operations review','institution':'Example Research Laboratory',
            'summary_points':['General operating conditions and manufacturing developments.'],
            'published_at':'2026-09-16T12:00:00Z','side':'independent','pages':2,'language':'en'}

def populate(corpus,path: Path,item,source):
    conn=corpus.open_db(path)
    corpus.upsert(conn,item,source['body'],facts={
        'content_sha256':source['pdf_sha256'],'char_count':source['char_count'],
        'pages':source['pages'],'text_layer':source['text_layer']})
    conn.close()
