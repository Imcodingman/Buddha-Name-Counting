"""Build data/*.json sutra files (simplified text + pinyin).

Usage:
  curl -sO https://raw.githubusercontent.com/cbeta-org/xml-p5/master/T/T13/T13n0412.xml
  pip install opencc-python-reimplemented pypinyin
  python3 tools/build_sutras.py T13n0412.xml data/

地藏经 comes from CBETA T0412 (converted to simplified); 心经 uses the common
recitation text of Xuanzang's translation (T0251). Pinyin is generated with
pypinyin plus the Buddhist readings below.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET

import opencc
from pypinyin import Style, load_phrases_dict, load_single_dict, pinyin

# Conventional readings in Buddhist recitation.
PHRASES = {
    '南无': 'nā mó', '阿弥陀': 'ā mí tuó', '般若': 'bō rě', '波罗蜜': 'bō luó mì',
    '菩萨': 'pú sà', '菩提': 'pú tí', '摩诃': 'mó hē', '萨埵': 'sà duǒ', '萨婆诃': 'sà pó hē',
    '优婆塞': 'yōu pó sè', '优婆夷': 'yōu pó yí', '释迦': 'shì jiā', '牟尼': 'móu ní',
    '舍利子': 'shè lì zǐ', '舍利弗': 'shè lì fú', '毘离耶': 'pí lí yē', '摩耶': 'mó yē',
    '佛刹': 'fó chà', '刹土': 'chà tǔ', '刹那': 'chà nà', '那由他': 'nà yóu tā',
    '揭谛': 'jiē dì', '三藐': 'sān miǎo', '阿耨': 'ā nòu', '罣碍': 'guà ài', '究竟': 'jiū jìng',
    '涅槃': 'niè pán', '三昧': 'sān mèi', '伎乐': 'jì yuè', '音乐': 'yīn yuè',
    '行深': 'xíng shēn', '受想行识': 'shòu xiǎng xíng shí', '眷属': 'juàn shǔ',
    '阎浮提': 'yán fú tí', '忉利': 'dāo lì', '羼提': 'chàn tí', '鸠槃荼': 'jiū pán tú',
    '那罗延': 'nà luó yán', '阿僧祇': 'ā sēng qí', '比丘': 'bǐ qiū', '迦楼罗': 'jiā lóu luó',
    '紧那罗': 'jǐn nà luó', '摩睺罗伽': 'mó hóu luó qié', '乾闼婆': 'qián tà pó',
    '毘舍遮': 'pí shè zhē', '富单那': 'fù dān nà', '一切': 'yī qiè',
    '相好': 'xiàng hǎo', '空相': 'kōng xiàng', '诸相': 'zhū xiàng', '宝相': 'bǎo xiàng',
    '毫相': 'háo xiàng', '无相': 'wú xiàng', '佛相': 'fó xiàng', '此相': 'cǐ xiàng',
    '长者': 'zhǎng zhě', '兜率': 'dōu shuài', '苦难': 'kǔ nàn', '灾难': 'zāi nàn',
    '障难': 'zhàng nàn', '诸难': 'zhū nàn', '舍宅': 'shè zhái', '此舍': 'cǐ shè',
    '应供': 'yìng gòng', '久处': 'jiǔ chǔ', '永处': 'yǒng chǔ', '无处': 'wú chù',
    '善处': 'shàn chù', '居处': 'jū chù', '三藏': 'sān zàng', '返舍': 'fǎn shè',
    '其舍': 'qí shè', '弹指': 'tán zhǐ', '咽病': 'yān bìng', '供具': 'gòng jù',
    '设供': 'shè gòng', '少善': 'shǎo shàn', '间绝': 'jiàn jué', '吾难': 'wú nàn',
    '产难': 'chǎn nàn',
}
# Characters whose reading is (nearly) fixed in sutra recitation.
SINGLE = {
    '刹': 'chà', '阿': 'ā', '般': 'bō', '祇': 'qí', '伽': 'qié', '佛': 'fó', '一': 'yī',
    '不': 'bù', '尽': 'jìn', '藏': 'zàng', '行': 'xíng', '当': 'dāng', '为': 'wèi', '那': 'nà', '横': 'hèng',
}
# 为 reads wéi ("to be / to act as") in these contexts; elsewhere wèi ("for").
WEI = ['充为劫', '身为大', '尚为菩', '所为善', '为虑', '名为', '铁为', '等为', '为善为恶',
       '为小国', '为友', '为下贱', '生为梵', '常为', '而为教', '犹为', '翻为', '劫为帝',
       '可为喻', '以为', '为王臣', '或为帝']

# 心经 · 唐三藏法师玄奘译 (common recitation text)
XINJING = [
    '观自在菩萨，行深般若波罗蜜多时，照见五蕴皆空，度一切苦厄。',
    '舍利子，色不异空，空不异色，色即是空，空即是色，受想行识，亦复如是。',
    '舍利子，是诸法空相，不生不灭，不垢不净，不增不减。',
    '是故空中无色，无受想行识，无眼耳鼻舌身意，无色声香味触法，无眼界，乃至无意识界，无无明，亦无无明尽，乃至无老死，亦无老死尽，无苦集灭道，无智亦无得。',
    '以无所得故，菩提萨埵，依般若波罗蜜多故，心无罣碍，无罣碍故，无有恐怖，远离颠倒梦想，究竟涅槃。',
    '三世诸佛，依般若波罗蜜多故，得阿耨多罗三藐三菩提。',
    '故知般若波罗蜜多，是大神咒，是大明咒，是无上咒，是无等等咒，能除一切苦，真实不虚。',
    '故说般若波罗蜜多咒，即说咒曰：',
]
XINJING_MANTRA = '揭谛揭谛，波罗揭谛，\n波罗僧揭谛，菩提萨婆诃。'

HAN = re.compile(r'[㐀-鿿\U00020000-\U0003ffff]')


def setup_pinyin():
    load_phrases_dict({k: [[s] for s in v.split()] for k, v in PHRASES.items()})
    load_single_dict({ord(k): v for k, v in SINGLE.items()})


def apply_overrides(run, out):
    for i, c in enumerate(run):
        if c in SINGLE:
            out[i] = SINGLE[c]
    for word in sorted(PHRASES, key=len):
        for m in re.finditer(re.escape(word), run):
            out[m.start():m.end()] = PHRASES[word].split()
    for ctx in WEI:
        for m in re.finditer(re.escape(ctx), run):
            for j in range(m.start(), m.end()):
                if run[j] == '为':
                    out[j] = 'wéi'


def to_pinyin(text):
    """One token per non-whitespace char: pinyin for Han, '_' otherwise."""
    chars = [c for c in text if not c.isspace()]
    run = ''.join(chars)
    out = []
    for c, py in zip(run, pinyin(run, style=Style.TONE, errors=lambda s: ['_'] * len(s), neutral_tone_with_five=False)):
        p = py[0]
        if not HAN.match(c):
            p = '_'
        elif not re.search(r'[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]', p):
            # Recitation uses full tones; replace a neutral tone with the first toned reading.
            toned = [h for h in pinyin(c, style=Style.TONE, heteronym=True)[0]
                     if re.search(r'[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]', h)]
            if toned:
                p = toned[0]
        out.append(p)
    apply_overrides(run, out)
    assert len(out) == len(chars)
    return ' '.join(out)


def parse_dizang(path):
    cc = opencc.OpenCC('t2s')
    ns = {'tei': 'http://www.tei-c.org/ns/1.0', 'cb': 'http://www.cbeta.org/ns/1.0'}
    T = '{%s}' % ns['tei']
    CB = '{%s}' % ns['cb']
    skip = {T + 'note', T + 'rdg', CB + 'mulu', T + 'head', T + 'byline', CB + 'jhead', CB + 'docNumber'}

    def text(el):
        out = []

        def walk(e):
            if e.tag in skip:
                return
            if e.tag == T + 'caesura':
                out.append('\x01')
            if e.text:
                out.append(e.text)
            for c in e:
                walk(c)
                if c.tail:
                    out.append(c.tail)
        walk(el)
        return re.sub(r'[ \t\r\n]+', '', ''.join(out)).replace('\x01', ' ')

    chapters = []

    def visit(e):
        for c in e:
            if c.tag == CB + 'mulu' and c.get('level') == '1':
                chapters.append({'title': None, 'paras': []})
            elif c.tag == T + 'head' and chapters and chapters[-1]['title'] is None:
                chapters[-1]['title'] = cc.convert(''.join(c.itertext()).strip())
            elif c.tag == T + 'p' and chapters:
                t = text(c)
                if t:
                    chapters[-1]['paras'].append({'t': cc.convert(t)})
            elif c.tag == T + 'lg' and chapters:
                lines = [cc.convert(text(l)) for l in c.findall('tei:l', ns)]
                chapters[-1]['paras'].append({'t': '\n'.join(lines), 'v': 1})
            else:
                visit(c)

    visit(ET.parse(path).getroot().find('.//tei:body', ns))
    return chapters


def add_pinyin(chapters):
    for ch in chapters:
        for p in ch['paras']:
            p['p'] = to_pinyin(p['t'])
    return chapters


def main():
    src, out = sys.argv[1], sys.argv[2].rstrip('/')
    setup_pinyin()
    dizang = add_pinyin(parse_dizang(src))
    xinjing = add_pinyin([{
        'title': '般若波罗蜜多心经',
        'paras': [{'t': t} for t in XINJING] + [{'t': XINJING_MANTRA, 'v': 1}],
    }])
    for name, data in (('dizang', dizang), ('xinjing', xinjing)):
        with open('%s/%s.json' % (out, name), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
