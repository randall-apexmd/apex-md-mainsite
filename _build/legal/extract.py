import re, sys, html as H
from html.parser import HTMLParser
KEEP_BLOCK={'p','h1','h2','h3','h4','h5','h6','ul','ol','li','table','thead','tbody','tr','td','th','blockquote'}
KEEP_INLINE={'strong','b','em','i','u','a','br'}
VOID={'br','img','hr','input','meta','link','source','wbr'}
class P(HTMLParser):
    def __init__(s, marker):
        super().__init__(convert_charrefs=True); s.marker=marker; s.on=False; s.depth=0; s.out=[]; s.done=False; s.armed=False
    def handle_starttag(s,t,a):
        if s.done: return
        a=dict(a)
        if not s.on:
            if t=='div' and s.marker in (a.get('class') or '') : s.armed=True
            elif s.armed and t=='div' and 'elementor-widget-container' in (a.get('class') or ''):
                s.on=True; s.depth=1
            return
        if t not in VOID: s.depth+=1
        if t in KEEP_BLOCK: s.out.append('<%s>'%('strong' if False else t))
        elif t=='a' and a.get('href'): s.out.append('<a href="%s">'%H.escape(a['href'],quote=True))
        elif t in ('strong','b'): s.out.append('<strong>')
        elif t in ('em','i'): s.out.append('<em>')
        elif t=='u': s.out.append('<u>')
        elif t=='br': s.out.append('<br>')
    def handle_endtag(s,t):
        if not s.on or s.done: return
        if t in VOID: return
        s.depth-=1
        if s.depth==0: s.done=True; s.on=False; return
        if t in KEEP_BLOCK: s.out.append('</%s>'%t)
        elif t=='a': s.out.append('</a>')
        elif t in ('strong','b'): s.out.append('</strong>')
        elif t in ('em','i'): s.out.append('</em>')
        elif t=='u': s.out.append('</u>')
    def handle_data(s,d):
        if s.on and not s.done: s.out.append(H.escape(d,quote=False))
src, marker, dst = sys.argv[1:4]
p=P(marker); p.feed(open(src).read())
x=''.join(p.out)
x=re.sub(r'<p>[\s\xa0]*</p>','',x)
x=re.sub(r'<(strong|em|u)>([\s\xa0]*)</\1>',r'\2',x)
x=re.sub(r'[ \t]*\n[ \t\n]*','\n',x)
x=re.sub(r'(</(p|h\d|ul|ol|li|table|tr|blockquote)>)',r'\1\n',x)
open(dst,'w').write(x.strip()+'\n')
txt=re.sub(r'<[^>]+>',' ',x); print(dst, 'words', len(H.unescape(txt).split()))
