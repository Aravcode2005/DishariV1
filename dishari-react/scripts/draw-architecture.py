#!/usr/bin/env python3
"""Draw editable, layout-stable Dishari system overview. Uses stdlib; PNG optional via cairosvg."""
from pathlib import Path
from html import escape
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'diagrams' / 'architecture.svg'
W, H = 1800, 1090
pieces = []
def add(s): pieces.append(s)
add(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
<title id="t">Dishari proposed end-to-end system architecture</title><desc id="d">Four stages: operator desk, secure API, document intelligence, and deterministic rules with Bengali summary. Protected data stores and operator-only government submission.</desc>
<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#0E5A6B"/></marker>
<marker id="arrowSoft" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M 0 0 L 9 4.5 L 0 9 z" fill="#8C8A80"/></marker>
</defs><rect width="100%" height="100%" fill="#F5F3EE"/>
<text x="52" y="65" font-family="DejaVu Sans,Arial,sans-serif" font-size="32" font-weight="700" fill="#1C2024">DISHARI</text>
<text x="250" y="65" font-family="DejaVu Sans,Arial,sans-serif" font-size="27" fill="#4F5660">/ Proposed system architecture</text>
<text x="52" y="100" font-family="DejaVu Sans,Arial,sans-serif" font-size="17" fill="#4F5660">Backend architecture is a design proposal. Only the React frontend and local mock ship in the ZIP.</text>''')
colors = dict(blue='#E4EDEE', line='#D9D5CB', ink='#1C2024', teal='#0E5A6B', green='#E7F3EA', greenStroke='#2F7D4A', red='#FDEBE8', redStroke='#B3261E', amber='#FFF3D1', amberStroke='#A86B00', white='#FFFFFF')
def rect(x,y,w,h,fill,stroke,rad=16,sw=2):
 add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rad}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def txt(x,y,s,size=18,bold=False,color=colors['ink'],anchor='start'):
 add(f'<text x="{x}" y="{y}" font-family="DejaVu Sans,Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{anchor}">{escape(s)}</text>')
def inner(x,y,w,label,lines,fill=colors['white'],stroke=colors['line'],foot=None):
 h=120 if len(lines)>1 else 104
 rect(x,y,w,h,fill,stroke,12,1.7)
 txt(x+20,y+35,label,20,True)
 for i,line in enumerate(lines): txt(x+20,y+64+i*23,line,15,False,'#3B424A')
 if foot: txt(x+20,y+h-12,foot,13,True,'#4F5660')

def arrow(x1,y1,x2,y2,color='#0E5A6B',dash=False):
 add(f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="{color}" stroke-width="3" {"stroke-dasharray=\"9 7\"" if dash else ""} marker-end="url(#{"arrowSoft" if dash else "arrow"})"/>')

columns=[(52,'01','SERVICE DESK'),(491,'02','SECURE API'),(930,'03','DOCUMENT AI'),(1369,'04','RULES & OUTPUT')]
for x,n,label in columns:
 rect(x,135,382,620,'#FFFFFF','#D9D5CB',19,2)
 rect(x,135,382,82,'#E4EDEE','#D9D5CB',19,1.6)
 txt(x+22,171,n,16,True,'#0E5A6B')
 txt(x+22,199,label,22,True,'#1C2024')
inner(73,245,340,'Citizen + operator',['Consent, scan, document selection','Operator stays in control'])
inner(73,387,340,'React + TypeScript UI',['Upload → Review → Summary','Responsive + accessible + printable'],colors['blue'],colors['teal'])
inner(73,532,340,'Explicit human approval',['Checks original documents','Official portal submission is manual'],colors['green'],colors['greenStroke'])
inner(512,245,340,'HTTPS API gateway',['Auth, CORS, rate limiting','POST multipart case + files'],colors['blue'],colors['teal'])
inner(512,387,340,'Consent + case service',['Purpose-bound consent receipt','Tenant access + audit trail'])
inner(512,532,340,'Secure document ingest',['Type/size scan + quarantine','Temporary encrypted storage'])
inner(951,245,340,'OCR + Gemini reading',['Multilingual field extraction','Confidence + source evidence'])
inner(951,387,340,'Profile normalizer',['Canonical facts with provenance','Ambiguity stays unresolved'])
inner(951,532,340,'Mismatch audit',['Cross-document discrepancies','Likely outlier ≠ official rule'],colors['red'],colors['redStroke'])
inner(1390,245,340,'Deterministic rules',['Versioned, cited source packs','No AI-invented thresholds'],colors['green'],colors['greenStroke'])
inner(1390,387,340,'Bengali summary service',['Template-backed advice','Provisional status clearly labelled'],colors['green'],colors['greenStroke'])
inner(1390,532,340,'Official govt. portals',['Outside Dishari automation','Operator signs in and submits'],colors['white'],'#8C8A80')
for x in [73,512,951,1390]:
 arrow(x+170,349,x+170,378)
 arrow(x+170,491,x+170,523)
# horizontal stage handoffs between columns
for a,b in [(413,491),(852,930),(1291,1369)]:
 arrow(a,461,b,461)
# service response route annotation
rect(52,779,1680,54,'#FFFFFF','#D9D5CB',12,1.5)
txt(76,813,'RESULT PATH',16,True,'#0E5A6B')
txt(255,813,'Structured CheckResult → runtime validation (Zod) → operator Review → Bengali handout',18,False)
# infra blocks
for x in [52,491,930,1369]: rect(x,865,382,145,'#FAF9F6','#D9D5CB',13,1.7)
txt(75,905,'DATABASE + AUDIT',18,True,'#0E5A6B'); txt(75,940,'Cases · consent · access events',16); txt(75,969,'No raw PII in logs',15,False,'#4F5660')
txt(514,905,'ENCRYPTED OBJECT STORE',18,True,'#0E5A6B'); txt(514,940,'Temporary raw document blobs',16); txt(514,969,'Short retention + deletion',15,False,'#4F5660')
txt(953,905,'VERSIONED RULE PACKS',18,True,'#2F7D4A'); txt(953,940,'Official links · versions · dates',16); txt(953,969,'Manual review / publication',15,False,'#4F5660')
txt(1392,905,'OBSERVABILITY',18,True,'#0E5A6B'); txt(1392,940,'Metrics · opaque request IDs',16); txt(1392,969,'Masked structured logs',15,False,'#4F5660')
txt(52,1053,'BOUNDARY:  AI reads documents. Versioned deterministic rules evaluate cases. An authorized person approves and submits.',17,True,'#3B424A')
add('</svg>')
OUT.write_text('\n'.join(pieces),encoding='utf8')
try:
 import cairosvg
 cairosvg.svg2png(bytestring=OUT.read_bytes(), write_to=str(OUT.with_suffix('.png')), output_width=W, output_height=H)
except ImportError:
 print('SVG generated; optional pip install cairosvg to also update PNG')
print(OUT)
