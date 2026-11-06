#!/usr/bin/env python3
"""Render the complete Markdown report with readable landscape figure pages."""
import re,html
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate,PageTemplate,Frame,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,NextPageTemplate,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.pagesizes import letter,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT
from PIL import Image as PILImage

ROOT=Path(__file__).parent;source=ROOT/'REPORT.md'
dest=ROOT/'deliverables'/'Durable_Pivot_Addition_Timing_Assessment.pdf'
fontroot=Path('/usr/share/fonts/truetype/dejavu')
pdfmetrics.registerFont(TTFont('DejaVu',str(fontroot/'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('DejaVu-Bold',str(fontroot/'DejaVuSans-Bold.ttf')))
pdfmetrics.registerFontFamily('DejaVu',normal='DejaVu',bold='DejaVu-Bold',italic='DejaVu',boldItalic='DejaVu-Bold')
navy=colors.HexColor('#173d63');teal=colors.HexColor('#147f79');light=colors.HexColor('#eef3f8');gray=colors.HexColor('#65758a')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='ReportTitle',fontName='DejaVu-Bold',fontSize=26,leading=32,textColor=navy,spaceAfter=20,keepWithNext=True))
styles.add(ParagraphStyle(name='Section',fontName='DejaVu-Bold',fontSize=15,leading=20,textColor=navy,spaceBefore=18,spaceAfter=10,keepWithNext=True))
styles.add(ParagraphStyle(name='Subsection',fontName='DejaVu-Bold',fontSize=11.5,leading=16,textColor=teal,spaceBefore=12,spaceAfter=7,keepWithNext=True))
styles.add(ParagraphStyle(name='Copy',fontName='DejaVu',fontSize=9.3,leading=13.3,textColor=colors.HexColor('#26364a'),spaceAfter=7.5))
styles.add(ParagraphStyle(name='BulletCopy',parent=styles['Copy'],leftIndent=12,firstLineIndent=-8,spaceAfter=6))
styles.add(ParagraphStyle(name='Cell',fontName='DejaVu',fontSize=7.7,leading=10.5,textColor=colors.HexColor('#26364a')))
styles.add(ParagraphStyle(name='CellHead',parent=styles['Cell'],fontName='DejaVu-Bold',textColor=colors.white))
styles.add(ParagraphStyle(name='Caption',fontName='DejaVu',fontSize=9,leading=13,textColor=gray,spaceAfter=6))
styles.add(ParagraphStyle(name='CompactReportTitle',parent=styles['ReportTitle'],fontSize=22,leading=27,spaceAfter=15))
styles.add(ParagraphStyle(name='CompactSection',parent=styles['Section'],fontSize=13,leading=17,spaceBefore=10,spaceAfter=6))
styles.add(ParagraphStyle(name='CompactSubsection',parent=styles['Subsection'],spaceBefore=9,spaceAfter=6))
styles.add(ParagraphStyle(name='CompactCopy',parent=styles['Copy'],fontSize=9,leading=11.6,spaceAfter=5.2))
styles.add(ParagraphStyle(name='CompactBulletCopy',parent=styles['BulletCopy'],fontSize=9,leading=11.6,spaceAfter=5))

def inline(text):
    text=html.escape(text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'`([^`]+)`',r'<font name="DejaVu">\1</font>',text)
    text=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'<link href="\2" color="#147f79">\1</link>',text)
    text=re.sub(r'\[([^\]]+)\]\((?!https?://)([^)]+)\)', lambda m:'<link href="https://github.com/mastermindx-market-intelligence/macro/blob/main/research/addition_timing_20261021/'+m.group(2)+'" color="#147f79">'+m.group(1)+'</link>',text)
    return text

def footer(c,doc):
    w,h=c._pagesize
    c.saveState();c.setStrokeColor(colors.HexColor('#d8e1eb'));c.line(35,34,w-35,34)
    c.setFont('DejaVu',7);c.setFillColor(gray)
    c.drawString(35,22,'Durable Pivot Signals  |  Contribution timing  |  Exploratory research  |  21 October 2026')
    c.drawRightString(w-35,22,str(doc.page));c.restoreState()

doc=BaseDocTemplate(str(dest),pagesize=letter,title='Durable Pivot Signals: The Cost of Waiting for an Entry',
                    author='ChatGPT research',leftMargin=43,rightMargin=43,topMargin=43,bottomMargin=46)
body=Frame(43,46,526,703,id='body_frame',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
wide=Frame(35,46,722,531,id='figure_frame',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
doc.addPageTemplates([PageTemplate(id='body',frames=[body],onPage=footer,pagesize=letter),
                     PageTemplate(id='figure',frames=[wide],onPage=footer,pagesize=landscape(letter))])
dest.parent.mkdir(exist_ok=True)
combined='\n\n<!-- PAGE_BREAK -->\n\n'.join((ROOT/n).read_text() for n in ['REPORT.md','SYSTEM_DESIGN.md','NEXT_HYPOTHESIS.md'])
combined=combined.replace('\u2014',' - ').replace('\u2013','-').replace('\u2011','-')
lines=combined.splitlines();flow=[];i=0;figcount=0;appendix=False
def style(name):
    return styles[('Compact'+name) if appendix else name]
while i<len(lines):
    line=lines[i].strip()
    if not line:i+=1;continue
    if line=='<!-- PAGE_BREAK -->':flow.append(PageBreak());appendix=True;i+=1;continue
    if line.startswith('!['):
        m=re.match(r'!\[(.*?)\]\((.*?)\)',line);path=ROOT/m.group(2)
        if path.suffix=='.svg':path=path.with_suffix('.png')
        im=PILImage.open(path);iw,ih=im.size;scale=min(722/iw,480/ih)
        figcount+=1
        flow.extend([NextPageTemplate('figure'),PageBreak(),Image(str(path),width=iw*scale,height=ih*scale),Spacer(1,9),
                     Paragraph(f'Figure {figcount}. '+inline(m.group(1))+'. See the report for methods, source labels and qualifications.',styles['Caption']),
                     NextPageTemplate('body'),PageBreak()])
        i+=1;continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].strip().startswith('|'):
            row=[x.strip() for x in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r'[:\- ]+',x) for x in row):rows.append(row)
            i+=1
        n=len(rows[0]);head=rows[0]
        if n==2:ratios=[.33,.67]
        elif n==3 and head[0].startswith('Joint-context comparison'):ratios=[.52,.24,.24]
        elif n==3 and head[0]=='Joint-context outcome':ratios=[.48,.26,.26]
        elif n==3:ratios=[.25,.36,.39]
        elif n==4:ratios=[.28,.23,.23,.26]
        elif n==5:ratios=[.24,.18,.18,.18,.22]
        elif n==6:ratios=[.38,.08,.10,.14,.15,.15]
        elif n==7 and head[0]=='Side':ratios=[.065,.44,.055,.085,.11,.13,.115]
        elif n==7:ratios=[.14,.24,.08,.12,.14,.14,.14]
        else:ratios=[1/n]*n
        cells=[[Paragraph(inline(x),styles['CellHead' if j==0 else 'Cell']) for x in row] for j,row in enumerate(rows)]
        t=Table(cells,colWidths=[526*r for r in ratios],repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,light]),
                               ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
                               ('TOPPADDING',(0,0),(-1,-1),5.5),('BOTTOMPADDING',(0,0),(-1,-1),5.5),
                               ('LINEBELOW',(0,0),(-1,0),.5,navy),('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#cfdae5'))]))
        flow.extend([t,Spacer(1,12)]);continue
    if line.startswith('# '):flow.append(Paragraph(inline(line[2:]),style('ReportTitle')));i+=1;continue
    if line.startswith('## '):flow.append(Paragraph(inline(line[3:]),style('Section')));i+=1;continue
    if line.startswith('### '):flow.append(Paragraph(inline(line[4:]),style('Subsection')));i+=1;continue
    if line.startswith('- '):flow.append(Paragraph('• '+inline(line[2:]),style('BulletCopy')));i+=1;continue
    para=[line];i+=1
    while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','![','- ')):
        para.append(lines[i].strip());i+=1
    flow.append(Paragraph(inline(' '.join(para)),style('Copy')))
doc.build(flow)
print('PDF_COMPLETE',dest.stat().st_size,figcount)
