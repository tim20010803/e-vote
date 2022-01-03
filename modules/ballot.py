from gluon import *
import re, hashlib, base64
import rsa
import json
import random
import _pickle as pickle
from uuid import uuid4
try:
    import ast
    have_ast=True
except:
    have_ast=False

regex_field = re.compile('{{(\w+)(\:\w+)?\!?}}')
regex_email = re.compile('[^\s<>"\',;]+\@[^\s<>"\',;]+',re.IGNORECASE)


def uuid():   #可能產生bc5f89c0-63d8-4aeb-bfde-108f2fff2a8a之類的唯一代碼，轉字串
    return str(uuid4()).replace('-','').upper()


def rsakeys():
    (pubkey,privkey) = rsa.newkeys(1024)
    return (pubkey.save_pkcs1(), privkey.save_pkcs1())

def sign(text,privkey_pem):
    privkey = rsa.PrivateKey.load_pkcs1(privkey_pem)
    # print(type(text))
    if type(text) == bytes:
        signature = base64.b16encode(rsa.sign(text,privkey,'SHA-256'))
    else:
        signature = base64.b16encode(rsa.sign(text.encode(),privkey,'SHA-256'))
    return signature

def ballot2form(ballot_model, readonly=False, vars=None, counters=None):    
    """If counters is passed this counts the results in the ballot.
    If readonly is False, then the voter has not yet voted; if readonly
    is True, then they have just voted."""    
    # ballot_model = [{"preamble":"","answers":["A","V","X"],"algorithm":"simple-majority","randomize":true,"comments":false,"name":"321331244310","type":"simple-majority"}]
    # ballot_model is a str????
    ballot_structure = json.loads(ballot_model)
    ballot = FORM()
    for question in ballot_structure:
        div =DIV(_class="question")
        ballot.append(div)
        html = MARKMIN(question['preamble'])
        div.append(html)
        table = TABLE()
        div.append(table)
        name = question['name']
        if counters:    #如果counters是None，表示選舉還沒結束
            options = []
            # print(question['algorithm'],"喔喔喔")
            for answer in question['answers']:
                key = name+ '/'+question['algorithm']+'/' +answer
                options.append((counters.get(key,0), answer))
                # print(options)
            options.sort(reverse=True)
            options = map(lambda a: a[1], options)
        else:
            options = question['answers']
            if question['randomize']:
                random.shuffle(options)
        for answer in options:
            key = name + '/'+question['algorithm']+'/' + answer
            if not counters:
                # print(question['algorithm'],"喔喔ㄚㄚㄚ")
                if question['algorithm'] == 'simple-majority':
                    inp = INPUT(_name=question['name'], _type="radio", _value=answer)
                # if question['algorithm'] == 'aaasimple-majority':
                    # inp = INPUT(_name=question['name'], _type="radio", _value=answer)
                if vars and vars.get(name) == answer:
                    inp['_checked'] = True
                if readonly:
                    inp['_disabled'] = True
            else:
                inp = STRONG(counters.get(key, 0))
            table.append(TR(TD(inp),TD(answer)))
        if question['comments']:
            value = readonly and vars.get(question['name']+'_comments') or ''
            textarea =  TEXTAREA(value, _disabled=readonly, _name=question['name']+'_comments')
            ballot.append(DIV(H4('Comments'), textarea))
    if not readonly and not counters:
        ballot.append(INPUT(_type='submit', _value="Submit Your Ballot!"))
    return ballot

def form2ballot(ballot_model, token, vars, results):
    ballot_content = ballot2form(ballot_model, readonly=True, vars=vars).xml().decode("utf-8")
    if token: ballot_content += '<pre>\n%s\n</pre>' % token
    return '<div class="ballot">%s</div>' % ballot_content.strip()
def blank_ballot(token):
    ballot_content = '<h2>Blank</h2>'
    if token: ballot_content += '<pre>\n%s\n</pre>' % token
    return '<div class="ballot">%s</div>' % ballot_content
