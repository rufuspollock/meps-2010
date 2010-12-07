'''Retrieve details of all MEPs.

http://www.europarl.europa.eu/members/archive/alphaOrder.do?letter=A&language=EN
'''
import os
import re

import BeautifulSoup as bs
import json

from swiss.cache import Cache

cache = os.path.join(os.path.dirname(__file__), 'cache')
DATAPATH = os.path.join(os.path.dirname(__file__), 'data')
europarl_url = 'http://www.europarl.europa.eu'
juri_url = 'http://www.europarl.europa.eu/activities/committees/membersCom.do?body=JURI'
itre_url = 'http://www.europarl.europa.eu/activities/committees/membersCom.do?body=ITRE'
member_base_url = 'http://www.europarl.europa.eu/members/expert/committees/view.do'

retriever = Cache(cache)
infopath = os.path.join(cache, 'info.js')

# from http://effbot.org/zone/re-sub.htm#unescape-html
import re, htmlentitydefs
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

def cleantext(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

party_mappings = {
    "Group of the European People's Party (Christian Democrats) and European Democrats": 'EPP',
    "Group of the Greens/European Free Alliance" : 'Greens/EFA',
    "Group of the Alliance of Liberals and Democrats for Europe": 'ALDE',
    "Socialist Group in the European Parliament": 'PSE',
    "Confederal Group of the European United Left - Nordic Green Left": 'GRUE',
    "Union for Europe of the Nations Group": 'UEN',
    "Independence/Democracy Group": 'INDE'
    }

def idfromurl(url):
    return re.findall('id=(\d+)', url)[0]

def mep_url(id):
    url = member_base_url + '?id=%s' % id 
    return url

def allmeps():
    # all meps from past
    archive = 'http://www.europarl.europa.eu/members/archive/alphaOrder.do?letter=%s&language=EN'
    active = 'http://www.europarl.europa.eu/members/expert/alphaOrder.do?letter=%s'
    meps = {}
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        url = active % letter
        print 'Processing: %s' % url
        path = retriever.retrieve(url)
        doc = open(path)
        soup = bs.BeautifulSoup(doc, convertEntities='html')
        hrefregex = '^/members/expert/alphaOrder/view.do?.*id=(\d+)'
        hrefre = re.compile(hrefregex)
        meplinks = soup.findAll('a', href=hrefre)
        # id: name
        for link in meplinks:
            id = hrefre.match(link['href']).group(1)
            name = cleantext(link.string)
            meps[id] = name
    print 'Found ids for %s MEPs' % len(meps)
    getinfo = GetInfo()
    for count, (id, values) in enumerate(meps.items()):
        url = mep_url(id)
        print id, values, url
        try:
            newdata = getinfo.info(url)
        except Exception, inst:
            print '!!!!! Failed to parse MEP info: %s %s %s' % (inst, id, url)
        # check names are the same?
        # assert newdata['name'] == values['name']
        meps[id] = newdata
    jspath = os.path.join(DATAPATH, 'meps.json')
    json.dump(meps, open(jspath, 'w'), indent=4)


class GetInfo(object):

    def info(self, url):
        filepath = retriever.retrieve(url)
        soup = bs.BeautifulSoup(open(filepath), convertEntities='html')
        mep = {
                'id': idfromurl(url),
                'name': '',
                'comms': {},
                'email': '',
                'url': url
                } 
        name = soup.find('td', 'mepname').string
        name = cleantext(name)
        # TODO: reverse name
        parts = name.split(' ')
        mep['name'] = name
        # only one child
        email = soup.find('td', 'mepmail').find('a')
        if email and email.string:
            mep['email'] = cleantext(email.string)
        def get_phone(prefix):
            phonere = '^.*(\+%s.*)' % prefix
            phone = soup.find(text=re.compile(phonere))
            phone = re.findall(phonere, phone)[0]
            return phone
        mep['phone_bxl'] = get_phone('32')
        mep['phone_stb'] = get_phone('33')
        ctry = soup.find('table', 'titlemep').findAll('td')[1].string
        mep['country'] = ctry
        # 2 of these but 1st is right one
        mep['party'] = cleantext(soup.find('span', 'titlemep').string)
        if mep['party'] in party_mappings:
            mep['party'] = party_mappings[mep['party']]
        return mep

    def committee_info(self, url):
        doc = open(retriever.retrieve(url)).read()
        soup = bs.BeautifulSoup(doc, convertEntities='html')
        meps = []
        for link in soup.findAll('a', href=re.compile('^/members/expert')):
            mep = { 'position': 'Chairman',
                    'party': None,
                    'country': None,
                    }
            mep['name'] = link.contents[0]
            # url is not reliable (includes jsession stuff etc)
            id = idfromurl(link['href'])
            mep['id'] = id
            mep['url'] = member_base_url + '?id=%s' % id 
            # chairman is different
            if link.get('class', '') != 'listOJ':
                mep['position'] = str(link.nextSibling.contents[0])[4:].strip()
                # get country and group
                otherhrefs = link.parent.parent.findAll('a',
                        onmouseover=re.compile('^overlib'))

                mep['country'] = self.cvt_mouseover(otherhrefs[0])
                mep['party'] = self.cvt_mouseover(otherhrefs[1])
            else: # TODO: chairman
                tds = link.parent.parent.parent.parent.findAll('td',
                        'list_blacklink')
                vals = [ td.contents[0] for td in tds ]
                mep['party'] = vals[0]
                mep['country'] = vals[1]
            meps.append(mep)
        return meps

    def show(self, meps):
        for mep in meps:
            print mep['name'], mep['position'], mep['party']

    def cvt_mouseover(self, href_tag):
        h = href_tag
        # stuff like ...
        # onmouseover="overlib('Group&nbsp;of&nbsp;the European&nbsp;People&#8217;s&nbsp;Party (Christian&nbsp;Democrats)&nbsp;and European&nbsp;Democrats',LEFT,BGCOLOR,'#48452D', ...
        val = h['onmouseover'].split(',')[0][9:-1]
        val = unescape(val)
        # seems like there are weird space characters
        # val = val.replace(u'\xc2', ' ')
        val = val.encode('ascii', 'replace')
        val = val.replace('?', ' ')
        val = unicode(val)
        return val.strip()

class TestGetInfo:
    gi = GetInfo()
    mep_url = 'http://www.europarl.europa.eu/members/expert/committees/view.do?id=2109'

    def test_juri(self):
        meps = self.gi.committee_info(juri_url)
        gargani = meps[0]
        print gargani
        assert gargani['name'] == u'GARGANI, Giuseppe'
        assert gargani['position'] == 'Chairman'
        assert gargani['id'] == '4562'

    def test_info(self):
        mep = self.gi.info(self.mep_url)
        print mep
        assert mep['id'] == u'2109'
        assert mep['name'] == u'Brian CROWLEY'
        assert mep['email'] == 'briancrowleymep@eircom.net'
        assert mep['phone_bxl'] == '+32 (0)2 28 45751'
        assert mep['phone_stb'] == '+33 (0)3 88 1 75751'
        assert mep['party'] == u'UEN'

    def test_idfromurl(self):
        out = idfromurl(self.mep_url)
        assert out == '2109'

def extract():
    gi = GetInfo()
    juri = gi.committee_info(juri_url)
    itre = gi.committee_info(itre_url)
    meps = {}
    def process(comm_mep, comm):
        m = comm_mep
        id = m['id']
        if id in meps:
            mep = meps[id]
        else:
            mep = gi.info(m['url'])
        mep['comms'][comm] = m['position']
        meps[id] = mep
    print 'JURI'
    for m in juri:
        print m['url']
        process(m, 'juri')
    print 'ITRE'
    for m in itre:
        print m['url']
        process(m, 'itre')
    json.dump(meps, open(infopath, 'w'), indent=4)

def use():
    meps = json.load(open(infopath))
    # TODO: sort by name
    juri = []
    itre = []
    for id,m in meps.items():
        # if m['country'] == 'Federal Republic of Germany':
        if True:
            if 'juri' in m['comms']:
                juri.append(m)
            else:
                itre.append(m)
    def makecmp(name):
        def mycmp(m1, m2):
            print m1,m2
            if m2[name]['position'] == 'Substitute':
                return 1
            elif m1[name]['position'] == 'Substitute':
                return -1
            else:
                return 0
        return mycmp
    # juri.sort(makecmp('juri'))
    # itre.sort(makecmp('itre'))
    import csv
    writer = csv.writer(open('meps.csv', 'w'))
    keys = ['name', 'email', 'phone_bxl', 'party', 'country', 'comms', 'url']
    writer.writerow(keys)
    def dorow(m):
        party = party_mappings.get(m['party'], m['party'])
        row = [ m[k].encode('utf8') for k in keys[:3] ]
        comms = ' '.join([ '%s (%s)' % (k.capitalize(),v) for k,v in m['comms'].items()])
        row.append(party)
        row.append(m['country'])
        row.append(comms)
        row.append(m['url'])
        writer.writerow(row)
    writer.writerow(['JURI'])
    for m in juri:
        dorow(m)
    writer.writerow([])
    writer.writerow(['ITRE'])
    for m in itre:
        dorow(m)

def printmep(m):
    print '##', m['name']
    print
    for k in ['party', 'email', 'phone_bxl']:
        print '%s: %s' % (k, m.get(k, ''))
    print 'Comms:', ' '.join([ '%s (%s)' % (k,v) for k,v in m['comms'].items()])
    print

if __name__ == '__main__':
    gi = GetInfo()
    import sys
    usage = 'meps.py { mep id | extract | use }'
    if len(sys.argv) <= 1:
        print usage
        sys.exit(1)
    if len(sys.argv) > 2:
        url = member_base_url + '?id=%s' % sys.argv[2]
        print gi.info(url)
    elif sys.argv[1] == 'extract':
        extract()
    elif sys.argv[1] == 'use':
        use()
    elif sys.argv[1] == 'all':
        allmeps()
    else:
        print usage
