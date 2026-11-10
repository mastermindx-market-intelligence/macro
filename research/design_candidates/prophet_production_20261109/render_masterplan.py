from pathlib import Path
import re, html, json, hashlib
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, PageBreakIfNotEmpty, CondPageBreak, Table, TableStyle, KeepTogether, HRFlowable, Preformatted
from reportlab.platypus.tableofcontents import TableOfContents

# Recovered from the v5.1 renderer; preserves the complete masterplan composition.
# Dependencies: reportlab and DejaVu fonts. The PDF source revision is explicit.
import argparse
parser = argparse.ArgumentParser(description='Render the complete Prophet v5.2 masterplan.')
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--source-revision', required=True)
args = parser.parse_args()
if not re.fullmatch(r'[0-9a-f]{40}', args.source_revision):
    parser.error('--source-revision must be an exact 40-character Git commit SHA')
SOURCE, OUT, source_sha = args.source, args.output, args.source_revision
OUT.parent.mkdir(parents=True, exist_ok=True)
text = SOURCE.read_text()
source_url = f'https://github.com/mastermindx-market-intelligence/macro/blob/{source_sha}/research/prophet_v4/PROPHET_PRODUCTION_MASTERPLAN_2026-11-09.md'
refs = dict(re.findall(r'^\[([^]]+)\]:\s+(\S+)\s*$', text, re.M))
fontroot = Path('/usr/share/fonts/truetype/dejavu')
for name, file in [('Body','DejaVuSans.ttf'),('BodyBold','DejaVuSans-Bold.ttf'),('BodyItalic','DejaVuSans-Oblique.ttf'),('BodyBoldItalic','DejaVuSans-BoldOblique.ttf'),('Mono','DejaVuSansMono.ttf')]:
    fontfile=fontroot/file
    if not fontfile.exists():
        fontfile=fontroot/('DejaVuSans-Bold.ttf' if 'Bold' in name else 'DejaVuSans.ttf')
    pdfmetrics.registerFont(TTFont(name, str(fontfile)))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='BodyBold', italic='BodyItalic', boldItalic='BodyBoldItalic')
NAVY = colors.HexColor('#172738')
TEAL = colors.HexColor('#14766D')
MUTED = colors.HexColor('#5B6B78')
LIGHT = colors.HexColor('#F1F5F7')
RULE = colors.HexColor('#D9E2E7')
WHITE = colors.white
W,H = A4
LEFT,RIGHT,TOP,BOTTOM = 43,43,51,44
CW = W-LEFT-RIGHT

def normalize(s):
    return s.replace('\u2011','-').replace('\u2013','-').replace('\u2014','-').replace('\u2212','-').replace('\u00a0',' ')

def inline(s, size=9.2):
    s=normalize(s)
    saved=[]
    def hold(x):
        saved.append(x)
        return f'ZZTOKEN{len(saved)-1}ZZ'
    s=re.sub(r'`([^`]+)`', lambda m: hold('<font name="Mono" size="'+str(max(size-1.2,6.3))+'">'+escape(m[1])+'</font>'), s)
    s=re.sub(r'\[([^\]]+)\]\((https?://(?:[^()]|\([^()]*\))+)\)', lambda m: hold('<link href="'+escape(m[2],{'"':'&quot;'})+'" color="#14766D">'+escape(m[1])+'</link>'), s)
    s=re.sub(r'\[([^\]]+)\]\[([A-Z]+\d+)\]', lambda m: hold('<link href="'+escape(refs[m[2]],{'"':'&quot;'})+'" color="#14766D">'+escape(m[1])+'</link>') if m[2] in refs else m[0], s)
    s=re.sub(r'\[([A-Z]+\d+)\]', lambda m: hold('<link href="'+escape(refs[m[1]],{'"':'&quot;'})+'" color="#14766D">['+m[1]+']</link>') if m[1] in refs else m[0], s)
    s=escape(s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<i>\1</i>',s)
    for i,v in enumerate(saved):s=s.replace(f'ZZTOKEN{i}ZZ',v)
    return s

styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='Text',fontName='Body',fontSize=9.15,leading=13.25,textColor=NAVY,spaceAfter=7.8,splitLongWords=1,allowWidows=0,allowOrphans=0))
styles.add(ParagraphStyle(name='Intro',parent=styles['Text'],fontSize=10.1,leading=15.1,spaceAfter=10))
styles.add(ParagraphStyle(name='Chapter',fontName='BodyBold',fontSize=22,leading=28,textColor=NAVY,spaceBefore=1,spaceAfter=16,keepWithNext=True))
styles.add(ParagraphStyle(name='ChapterTable',parent=styles['Chapter'],keepWithNext=False))
styles.add(ParagraphStyle(name='Sub',fontName='BodyBold',fontSize=12.4,leading=17,textColor=NAVY,spaceBefore=13,spaceAfter=8,keepWithNext=True))
styles.add(ParagraphStyle(name='SubTable',parent=styles['Sub'],keepWithNext=False))
styles.add(ParagraphStyle(name='Minor',fontName='BodyBold',fontSize=9.6,leading=14,textColor=NAVY,spaceBefore=8,spaceAfter=7,keepWithNext=True))
styles.add(ParagraphStyle(name='MinorTable',parent=styles['Minor'],keepWithNext=False))
styles.add(ParagraphStyle(name='BulletX',parent=styles['Text'],leftIndent=13,firstLineIndent=-10,spaceAfter=6))
styles.add(ParagraphStyle(name='Cell',fontName='Body',fontSize=7.7,leading=11,textColor=NAVY,spaceAfter=0,splitLongWords=1,allowWidows=1,allowOrphans=1))
styles.add(ParagraphStyle(name='CellHead',parent=styles['Cell'],fontName='BodyBold',fontSize=7.8,leading=10.6,textColor=WHITE))
styles.add(ParagraphStyle(name='Small',fontName='Body',fontSize=7.7,leading=11.2,textColor=MUTED,spaceAfter=6,splitLongWords=1))
styles.add(ParagraphStyle(name='CodeX',fontName='Mono',fontSize=7.25,leading=10.5,textColor=NAVY,backColor=LIGHT,borderPadding=7,spaceBefore=7,spaceAfter=10))
styles.add(ParagraphStyle(name='CoverTitle',fontName='BodyBold',fontSize=46,leading=54,textColor=NAVY,spaceAfter=14))
styles.add(ParagraphStyle(name='CoverSub',fontName='Body',fontSize=23,leading=31,textColor=NAVY,spaceAfter=20))
styles.add(ParagraphStyle(name='CoverKicker',fontName='BodyBold',fontSize=10,leading=15,textColor=TEAL,spaceAfter=13))
styles.add(ParagraphStyle(name='CoverText',fontName='Body',fontSize=12,leading=18,textColor=MUTED,spaceAfter=15))

class PlanDoc(BaseDocTemplate):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        frame=Frame(LEFT,BOTTOM,CW,H-TOP-BOTTOM,id='body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.addPageTemplates(PageTemplate(id='master',frames=[frame],onPage=self.decorate))
    def decorate(self, canv, doc):
        canv.saveState()
        if doc.page>1:
            canv.setFillColor(MUTED);canv.setFont('BodyBold',7.2)
            canv.drawString(LEFT,H-29,'PROPHET  /  PRODUCTION MASTERPLAN')
            canv.setFont('Body',7.2);canv.drawRightString(W-RIGHT,H-29,'9 NOVEMBER 2026')
            canv.setStrokeColor(RULE);canv.setLineWidth(.45);canv.line(LEFT,H-37,W-RIGHT,H-37)
        canv.setStrokeColor(RULE);canv.setLineWidth(.45);canv.line(LEFT,31,W-RIGHT,31)
        canv.setFillColor(MUTED);canv.setFont('Body',7)
        canv.drawString(LEFT,20,'MASTERPLAN v5.2  |  SECTOR INTELLIGENCE  |  SOURCE BASELINE')
        canv.drawRightString(W-RIGHT,20,str(doc.page))
        canv.restoreState()
    def afterFlowable(self,flowable):
        if getattr(flowable,'toc_key',None):
            self.canv.bookmarkPage(flowable.toc_key)
            self.canv.addOutlineEntry(flowable.getPlainText(),flowable.toc_key,level=0,closed=False)
            self.notify('TOCEntry',(0,flowable.getPlainText(),self.page,flowable.toc_key))

doc=PlanDoc(str(OUT),pagesize=A4,leftMargin=LEFT,rightMargin=RIGHT,topMargin=TOP,bottomMargin=BOTTOM,title='Prophet production masterplan - Sector Intelligence integration v5.2',author='MastermindX',subject='Beta-first Sector integration, complete retained architecture, Paper build instructions and Fable commission',pageCompression=1)
story=[]
story.extend([Spacer(1,47),Paragraph('MASTERMINDX  /  PRODUCT & INTELLIGENCE',styles['CoverKicker']),Paragraph('PROPHET',styles['CoverTitle']),Paragraph('Production masterplan',styles['CoverSub']),Paragraph('Market participation. Sector leadership. Company evidence.',styles['CoverText']),HRFlowable(width=CW,thickness=1,color=RULE),Spacer(1,25)])
story.append(Paragraph('Sector-connected edition',styles['Sub']))
story.append(Paragraph('The complete Prophet architecture, strengthened with shared market and sector intelligence, independent company evidence and benchmark-first acceptance.',styles['CoverText']))
cover_rows=[['20','7','24','24'],['New integration contracts','Delivery packets amended','New proof cases specified','Research packets preserved']]
ct=Table([[Paragraph(x,ParagraphStyle('num',fontName='BodyBold',fontSize=24,leading=30,textColor=NAVY)) for x in cover_rows[0]],[Paragraph(x,styles['Small']) for x in cover_rows[1]]],colWidths=[CW/4]*4)
ct.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),13),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
story.extend([Spacer(1,19),ct,Spacer(1,20)])
story.append(Paragraph('<b>Status:</b> Twelve Sector-connected Paper roots have review coverage, including completed attribution, four disclosures and compact specimens. Source and builder guidance match the recovered designs. Section 18.15 records the retained receipt limits and original mobile Plans hold. Production implementation and scientific acceptance remain open.',styles['Text']))
story.append(Spacer(1,20))
story.append(Paragraph('9 November 2026  |  Version 5.2',styles['Small']))
story.append(Paragraph('<link href="'+source_url+'" color="#14766D">Open the exact source masterplan</link>',styles['Small']))
story.append(Paragraph('Source revision: '+source_sha,styles['Small']))
story.append(PageBreak())
story.append(Paragraph('Contents',styles['Chapter']))
story.append(Paragraph('Section 18 governs Sector integration and beta-first acceptance; section 18.15 records completed v5.2 evaluation designs and recovery evidence. Sections 10-12 carry delivery and current boundaries; sections 14-17 preserve the original owner contracts and release proof with v5 bindings. Section 13 and appendices retain prior design and the complete original programme.',styles['Intro']))
toc=TableOfContents();toc.levelStyles=[ParagraphStyle(name='TOC',fontName='Body',fontSize=9.4,leading=13,leftIndent=0,firstLineIndent=0,spaceBefore=1.5,textColor=NAVY)]
story.extend([toc,PageBreak(),Paragraph('Scope and source',styles['Chapter'])])

def make_table(raw):
    cells=[[x.strip() for x in row.strip().strip('|').split('|')] for row in raw]
    cells=[r for r in cells if not all(re.fullmatch(r':?-{2,}:?',x) for x in r)]
    n=len(cells[0])
    if n==5:
        widths=[CW*.11,CW*.32,CW*.12,CW*.225,CW*.225]
    elif n==4:
        if cells[0][0]=='Contract': widths=[CW*.16,CW*.28,CW*.46,CW*.10]
        elif cells[0][0]=='Unit': widths=[CW*.08,CW*.30,CW*.27,CW*.35]
        elif cells[0][0]=='Requirement': widths=[CW*.10,CW*.40,CW*.30,CW*.20]
        elif cells[0][0]=='Decision': widths=[CW*.09,CW*.40,CW*.31,CW*.20]
        else: widths=[CW*.18,CW*.30,CW*.28,CW*.24]
    elif n==3:
        if cells[0][0] in ['R6 unit','PR']:
            widths=[CW*.12,CW*.57,CW*.31]
        else:widths=[CW*.23,CW*.365,CW*.405]
    elif n==2:widths=[CW*.32,CW*.68]
    else:widths=[CW/n]*n
    data=[]
    if cells[0][0] in ['Requirement','Decision']: cells[0][0]='ID'
    for i,row in enumerate(cells):
        if len(row)!=n:raise ValueError(f'Table columns: {len(row)} vs {n}: {row}')
        data.append([Paragraph(inline(x,7.7),styles['CellHead'] if i==0 else styles['Cell']) for x in row])
    table=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT',splitByRow=1)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,LIGHT]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.5,NAVY),('LINEBELOW',(0,1),(-1,-1),.3,RULE)]))
    return table

def next_table_min(lines, index):
    j=index+1
    while j<len(lines) and not lines[j].strip(): j+=1
    if j>=len(lines) or not lines[j].startswith('|'): return None
    raw=[];actual=0
    while j<len(lines) and lines[j].startswith('|') and actual<2:
        row=lines[j];raw.append(row)
        vals=[x.strip() for x in row.strip().strip('|').split('|')]
        if not all(re.fullmatch(r':?-{2,}:?',x) for x in vals): actual+=1
        j+=1
    _,height=make_table(raw).wrap(CW,H)
    return height+52

lines=text.splitlines();i=0; chapter_n=0
while i<len(lines):
    line=lines[i]
    if not line.strip():i+=1;continue
    if re.match(r'^\[[^]]+\]:',line):i+=1;continue
    if line.startswith('# ') or line.startswith('## Version 5.2') or line in ['### Reference definitions','### Turn 3 reference definitions','### Final Turn 4 reference definitions','### Sector integration reference definitions']:i+=1;continue
    if line.startswith('```'):
        block=[];i+=1
        while i<len(lines) and not lines[i].startswith('```'):
            block.append(normalize(lines[i]));i+=1
        i+=1
        story.append(Preformatted('\n'.join(block),styles['CodeX'],maxLineLength=108,splitChars=' ,|'))
        continue
    if line.startswith('#### '):
        minimum=next_table_min(lines,i)
        if minimum is not None: story.append(CondPageBreak(minimum))
        story.append(Paragraph(inline(line[5:],9.6),styles['MinorTable'] if minimum is not None else styles['Minor']))
        i+=1;continue
    if line.startswith('##### '):
        story.append(Paragraph(inline(line[6:],9.6),styles['Minor']));i+=1;continue
    if line.startswith('## '):
        title=line[3:];chapter_n+=1
        minimum=next_table_min(lines,i)
        para=Paragraph(inline(title,22),styles['ChapterTable'] if minimum is not None else styles['Chapter']);para.toc_key='chapter'+str(chapter_n)
        _,heading_height=para.wrap(CW,H)
        if title.startswith('Appendix'):
            story.append(PageBreakIfNotEmpty())
        else:
            story.extend([CondPageBreak(max(235,(minimum or 0)+heading_height+34)),Spacer(1,18)])
        story.append(para);i+=1;continue
    if line.startswith('### '):
        minimum=next_table_min(lines,i)
        if minimum is not None: story.append(CondPageBreak(minimum))
        story.append(Paragraph(inline(line[4:],12.4),styles['SubTable'] if minimum is not None else styles['Sub']))
        i+=1;continue
    if re.fullmatch(r'\*\*[^*]+\*\*',line):
        minimum=next_table_min(lines,i)
        if minimum is not None: story.append(CondPageBreak(minimum))
        story.append(Paragraph(inline(line[2:-2],9.6),styles['MinorTable'] if minimum is not None else styles['Minor']))
        i+=1;continue
    if line.startswith('|'):
        raw=[]
        while i<len(lines) and lines[i].startswith('|'):raw.append(lines[i]);i+=1
        table=make_table(raw);table.spaceAfter=11
        story.append(table);continue
    if re.match(r'^\d+\.\s',line):
        m=re.match(r'^(\d+\.)\s+(.*)',line)
        story.append(Paragraph(m[1]+' '+inline(m[2]),styles['BulletX']));i+=1;continue
    if line.startswith('- '):story.append(Paragraph('- '+inline(line[2:]),styles['BulletX']));i+=1;continue
    group=[line];i+=1
    while i<len(lines) and lines[i].strip() and not re.match(r'^(#{1,5} |```|\||- |\d+\. |\[[^]]+\]:)',lines[i]):group.append(lines[i]);i+=1
    story.append(Paragraph(inline(' '.join(group)),styles['Text']))

doc.multiBuild(story)
print(json.dumps({'output':str(OUT),'bytes':OUT.stat().st_size,'source_chars':len(text),'source_sha256':hashlib.sha256(text.encode()).hexdigest()},indent=2))
