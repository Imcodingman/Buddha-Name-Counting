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
    '南无': 'ná mó', '阿弥陀': 'ā mí tuó', '般若': 'bō rě', '波罗蜜': 'bō luó mì',
    '菩萨': 'pú sà', '菩提': 'pú tí', '摩诃': 'mó hē', '萨埵': 'sà duǒ', '萨婆诃': 'sà pó hē',
    '优婆塞': 'yōu pó sè', '优婆夷': 'yōu pó yí', '释迦': 'shì jiā', '牟尼': 'móu ní',
    '舍利子': 'shè lì zǐ', '舍利弗': 'shè lì fú', '毗离耶': 'pí lí yē', '摩耶': 'mó yē',
    '佛刹': 'fó chà', '刹土': 'chà tǔ', '刹那': 'chà nà', '那由他': 'nà yóu tā',
    '揭谛': 'jiē dì', '三藐': 'sān miǎo', '阿耨': 'ā nòu', '罣碍': 'guà ài', '究竟': 'jiū jìng',
    '涅槃': 'niè pán', '三昧': 'sān mèi', '伎乐': 'jì yuè', '音乐': 'yīn yuè',
    '行深': 'xíng shēn', '受想行识': 'shòu xiǎng xíng shí', '眷属': 'juàn shǔ',
    '阎浮提': 'yán fú tí', '忉利': 'dāo lì', '羼提': 'chàn tí', '鸠槃荼': 'jiū pán tú',
    '那罗延': 'nà luó yán', '阿僧祇': 'ā sēng qí', '比丘': 'bǐ qiū', '迦楼罗': 'jiā lóu luó',
    '紧那罗': 'jǐn nà luó', '摩睺罗伽': 'mó hóu luó qié', '乾闼婆': 'qián tà pó',
    '毗舍遮': 'pí shè zhē', '富单那': 'fù dān nà', '一切': 'yī qiè',
    '相好': 'xiàng hǎo', '空相': 'kōng xiàng', '诸相': 'zhū xiàng', '宝相': 'bǎo xiàng',
    '毫相': 'háo xiàng', '无相': 'wú xiàng', '佛相': 'fó xiàng', '此相': 'cǐ xiàng',
    '长者': 'zhǎng zhě', '兜率': 'dōu shuài', '苦难': 'kǔ nàn', '灾难': 'zāi nàn',
    '障难': 'zhàng nàn', '诸难': 'zhū nàn', '舍宅': 'shè zhái', '此舍': 'cǐ shè',
    '应供': 'yìng gòng', '久处': 'jiǔ chǔ', '永处': 'yǒng chǔ', '无处': 'wú chù',
    '善处': 'shàn chù', '居处': 'jū chù', '三藏': 'sān zàng', '返舍': 'fǎn shè',
    '其舍': 'qí shè', '弹指': 'tán zhǐ', '咽病': 'yān bìng', '供具': 'gòng jù',
    '设供': 'shè gòng', '少善': 'shǎo shàn', '间绝': 'jiàn jué', '吾难': 'wú nàn',
    '产难': 'chǎn nàn',
    # Readings as printed in 达缘讲堂《地藏菩萨本愿经》全文拼音 (乾隆藏 edition).
    '白衣': 'bái yī', '白虎': 'bái hǔ', '白毫': 'bái háo', '觉华': 'jué huá',
    '雨无量': 'yù wú liàng', '苦乐法': 'kǔ yào fǎ', '刚强': 'gāng qiáng',
    '重白': 'chóng bó', '重海': 'chóng hǎi', '长钉': 'cháng dīng', '还复': 'huán fù',
    '大乘': 'dà shèng', '愿乐': 'yuàn yào', '攒': 'cuán', '之分': 'zhī fèn',
    '戟中': 'jǐ zhòng', '或中口': 'huò zhòng kǒu', '或中腹': 'huò zhòng fù',
    '斗诤': 'dòu zhēng', '斗乱': 'dòu luàn', '喑哑': 'yīn yǎ', '悭吝': 'qiān lìn',
}
# Characters whose reading is (nearly) fixed in sutra recitation.
SINGLE = {
    '刹': 'chà', '阿': 'ā', '般': 'bō', '祇': 'qí', '伽': 'qié', '佛': 'fó', '一': 'yī',
    '不': 'bù', '尽': 'jìn', '藏': 'zàng', '行': 'xíng', '当': 'dāng', '为': 'wèi', '那': 'nà', '横': 'hèng',
    '白': 'bó', '华': 'huā', '调': 'tiáo',
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

# Bring the CBETA (大正藏) text in line with the 乾隆藏 wording used by the reference edition.
TEXT_FIXES = [
    ('彊', '强'), ('毘', '毗'), ('销', '消'), ('一沙一界', '一沙之界'), ('果位已来', '果位以来'),
    ('傥', '倘'), ('支节', '肢节'), ('稣', '苏'), ('辠', '罪'), ('麁', '粗'), ('点污', '玷污'), ('啗', '噉'),
    ('洋铜', '烊铜'), ('羗', '羌'), ('累劫已来', '累劫以来'), ('七日已来', '七日以来'), ('隣', '邻'), ('鼈', '鳖'),
    ('三涂', '三塗'), ('婬', '淫'), ('鬪', '斗'), ('瘖痖', '喑哑'), ('岐路', '歧路'), ('氷', '冰'),
    ('然油灯', '燃油灯'), ('悋', '吝'), ('旛', '幡'),
]

# Opening / closing liturgy, transcribed from the reference edition with its pinyin.
# Each entry: (kind, text, pinyin, note). kind: h heading, n note, c invocation, v verse, p prose.
CALL_SHAKYA = ('c', '南无本师释迦牟尼佛', 'ná mó běn shī shì jiā móu ní fó', '（合掌三称）')
DIZANG_PRE = [
    ('h', '香赞', 'xiāng zàn', None),
    ('n', '（一遍）', None, None),
    ('p', '炉香乍爇，法界蒙薰，诸佛海会悉遥闻，随处结祥云，诚意方殷，诸佛现全身。',
     'lú xiāng zhà ruò fǎ jiè méng xūn zhū fó hǎi huì xī yáo wén suí chù jié xiáng yún '
     'chéng yì fāng yīn zhū fó xiàn quán shēn', None),
    ('c', '南无香云盖菩萨摩诃萨', 'ná mó xiāng yún gài pú sà mó hē sà', '（合掌三称）'),
    CALL_SHAKYA,
    ('h', '地藏菩萨偈', 'dì zàng pú sà jì', None),
    ('n', '（一遍）', None, None),
    ('v', '稽首本然净心地 无尽佛藏大慈尊\n南方世界涌香云 香雨花云及花雨\n宝雨宝云无数种 为祥为瑞遍庄严\n'
          '天人问佛是何因 佛言地藏菩萨至\n三世如来同赞叹 十方菩萨共皈依\n我今宿植善因缘 称扬地藏真功德',
     'qǐ shǒu běn rán jìng xīn dì wú jìn fó zàng dà cí zūn nán fāng shì jiè yǒng xiāng yún xiāng yǔ huā yún jí huā yǔ '
     'bǎo yǔ bǎo yún wú shù zhǒng wéi xiáng wéi ruì biàn zhuāng yán tiān rén wèn fó shì hé yīn fó yán dì zàng pú sà zhì '
     'sān shì rú lái tóng zàn tàn shí fāng pú sà gòng guī yī wǒ jīn sù zhí shàn yīn yuán chēng yáng dì zàng zhēn gōng dé', None),
    ('p', '慈因积善，誓救众生，手中金锡，振开地狱之门。掌上明珠，光摄大千世界。智慧音里，吉祥云中，'
          '为阎浮提苦众生，作大证明功德主。大悲大愿，大圣大慈，本尊地藏菩萨摩诃萨。',
     'cí yīn jī shàn shì jiù zhòng shēng shǒu zhōng jīn xī zhèn kāi dì yù zhī mén zhǎng shàng míng zhū '
     'guāng shè dà qiān shì jiè zhì huì yīn lǐ jí xiáng yún zhōng wèi yán fú tí kǔ zhòng shēng '
     'zuò dà zhèng míng gōng dé zhǔ dà bēi dà yuàn dà shèng dà cí běn zūn dì zàng pú sà mó hē sà', None),
    ('c', '南无大愿地藏王菩萨', 'ná mó dà yuàn dì zàng wáng pú sà', '（合掌三称）'),
    CALL_SHAKYA,
    ('h', '开经偈', 'kāi jīng jì', None),
    ('n', '（一遍）', None, None),
    ('v', '无上甚深微妙法 百千万劫难遭遇\n我今见闻得受持 愿解如来真实义',
     'wú shàng shèn shēn wēi miào fǎ bǎi qiān wàn jié nán zāo yù wǒ jīn jiàn wén dé shòu chí yuàn jiě rú lái zhēn shí yì', None),
]
DIZANG_POST = [
    ('h', '补阙真言', 'bǔ quē zhēn yán', None),
    ('p', '南无喝啰怛那，哆罗夜耶，佉啰佉啰，俱住俱住，摩啰摩啰，虎啰，吽，贺贺，苏怛那，吽，泼抹拏，娑婆诃。',
     'ná mó hē là dá nà duō là yè yē qié là qié là jù zhù jù zhù mó là mó là hǔ là hōng hè hè sū dá nà hōng '
     'pō mò ná suō pó hē', '（三遍）'),
    ('h', '补阙圆满真言', 'bǔ quē yuán mǎn zhēn yán', None),
    ('p', '唵，呼嚧呼嚧，社曳穆契，娑诃。', 'ōng hū lú hū lú shè yì mù qiè suō hē', '（三遍）'),
    ('h', '普回向真言', 'pǔ huí xiàng zhēn yán', None),
    ('p', '唵，娑麽啰，娑麽啰，弭麽曩，萨嚩诃，摩诃斫迦啰嚩吽。',
     'ōng suō mó là suō mó là mǐ mó nǎng sà pó hē mó hē zhuó jiā luó wá hōng', '（三遍）'),
    ('h', '七佛灭罪真言', 'qī fó miè zuì zhēn yán', None),
    ('p', '离婆离婆帝，求诃求诃帝，陀罗尼帝，尼诃啰帝，毗黎你帝，摩诃伽帝，真陵乾帝，莎婆诃。',
     'lí pó lí pó dì qiú hē qiú hē dì tuó luó ní dì ní hē là dì pí lí nǐ dì mó hē qié dì zhēn líng qián dì suō pó hē',
     '（三遍）'),
    ('h', '灭定业真言', 'miè dìng yè zhēn yán', None),
    ('p', '唵，钵啰末邻陀宁，娑婆诃。', 'ōng bō là mò lín tuó níng suō pó hē', '（三遍）'),
    CALL_SHAKYA,
    ('c', '南无地藏菩萨摩诃萨', 'ná mó dì zàng pú sà mó hē sà', '（合掌三称）'),
    ('h', '回向偈', 'huí xiàng jì', None),
    ('n', '（一遍）', None, None),
    ('v', '诵经功德殊胜行 无边胜福皆回向\n普愿沉溺诸有情 速往无量光佛刹\n十方三世一切佛 一切菩萨摩诃萨\n摩诃般若波罗蜜',
     'sòng jīng gōng dé shū shèng hèng wú biān shèng fú jiē huí xiàng pǔ yuàn chén nì zhū yǒu qíng sù wǎng wú liàng guāng fó chà '
     'shí fāng sān shì yí qiè fó yí qiè pú sà mó hē sà mó hē bō rě bō luó mì', None),
    ('h', '回向偈', 'huí xiàng jì', None),
    ('n', '（一遍）', None, None),
    ('v', '愿以此功德 庄严佛净土\n上报四重恩 下济三途苦\n若有见闻者 悉发菩提心\n尽此一报身 同生极乐国',
     'yuàn yǐ cǐ gōng dé zhuāng yán fó jìng tǔ shàng bào sì chóng ēn xià jì sān tú kǔ '
     'ruò yǒu jiàn wén zhě xī fā pú tí xīn jìn cǐ yī bào shēn tóng shēng jí lè guó', None),
]

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
    for m in re.finditer('不(?=[？?])', run):
        out[m.start()] = 'fǒu'
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


def liturgy(title, entries):
    paras = []
    for kind, text, py, note in entries:
        p = {'t': text, 'k': kind}
        if py:
            toks = iter(py.split())
            p['p'] = ' '.join(next(toks) if HAN.match(c) else '_' for c in text if not c.isspace())
            assert next(toks, None) is None, text
            assert '_' not in [t for c, t in zip([c for c in text if not c.isspace()], p['p'].split()) if HAN.match(c)]
        if note:
            p['note'] = note
        paras.append(p)
    return {'title': title, 'x': 1, 'paras': paras}


def apply_text_fixes(chapters):
    for old, new in TEXT_FIXES:
        hits = 0
        for ch in chapters:
            for p in ch['paras']:
                hits += p['t'].count(old)
                p['t'] = p['t'].replace(old, new)
        assert hits, old
    return chapters


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
            if 'p' not in p and p.get('k') != 'n':
                p['p'] = to_pinyin(p['t'])
    return chapters


def main():
    src, out = sys.argv[1], sys.argv[2].rstrip('/')
    setup_pinyin()
    body = apply_text_fixes(parse_dizang(src))
    body[0]['juan'] = '卷上'
    body[4]['juan'] = '卷中'
    body[9]['juan'] = '卷下'
    dizang = add_pinyin([liturgy('开经', DIZANG_PRE)] + body + [liturgy('结经回向', DIZANG_POST)])
    xinjing = add_pinyin([{
        'title': '般若波罗蜜多心经',
        'paras': [{'t': t} for t in XINJING] + [{'t': XINJING_MANTRA, 'v': 1}],
    }])
    for name, data in (('dizang', dizang), ('xinjing', xinjing)):
        with open('%s/%s.json' % (out, name), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
