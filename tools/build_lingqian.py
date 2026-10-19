"""Build data/lingqian.json (观音灵签一百签).

Sources, fetched page by page:
  A  https://www.nongli.com/item5/guanyin/{n}.html      (base: 签诗版本二, 诗意, 解曰, 圣意)
  B  https://3g.d5168.com/chouqian/guanyin/4/{n}/      (cross-check)

Usage: python3 tools/build_lingqian.py both.json data/lingqian.json
where both.json holds the parsed pages of A ("nl") and B ("d5").
The base is A with its collation notes removed; FIX lists every place where the
two sources disagree and we did not keep A's reading (mostly obvious typos in A,
or lots 98-100 whose A pages are malformed).
"""
import json
import re
import sys

LEVEL = {7: '下签'}  # A says 上签; B and the poem (进步为难，只宜守旧) say 下签.

FIX = {
    3: dict(poem=['临风冒雨去还乡', '正是其身似燕儿', '衔得坭来欲作垒', '到头垒坏复须泥'], shiyi='此卦燕子衔坭之象。凡事劳心费力也。'),
    4: dict(shiyi='此卦古镜重圆之象。凡事劳心有贵也。', jie='淘沙见金。骑龙踏虎。虽是劳心。于中有补。'),
    5: dict(poem=['一锥凿地要求泉', '努力求之得最难', '无意偶然遇知己', '相逢携手上青天']),
    6: dict(poem=['投身岩下铜鸟居', '须是还他大丈夫', '拾得营谋谁可得', '通行天地此人无'], jie='食用无余。身清喜贫。待时利乐。权与概人。'),
    7: dict(poem=['奔波阻隔重重险', '带水拖坭去度山', '更望他乡求用事', '千乡万里未回还'], jie='退身可得。进步为难。只宜守旧。莫望高攀。'),
    9: dict(shiyi='此卦皎月当空之象。凡事光明通达也。'),
    13: dict(shiyi='此卦龙门得遇之象。凡事有变大吉也。', jie='囚人逢赦。病即安然。龙门得遇。名遍皇都。'),
    14: dict(poem=['宛如仙鹤出樊笼', '脱得樊笼路路通', '南北东西无阻隔', '任君直上九霄宫']),
    15: dict(poem=['行人怨日气难吞', '忽有灾事勿近前', '巢破林鸟无所宿', '可寻深处稳安身']),
    17: dict(poem=['莫听闲言说是非', '晨昏只好念阿弥', '若将狂话为真实', '画饼如何止得饥'], shiyi='此卦画饼充饥之象。诸事多虚少实也。',
             jie='心中不定。枉看经文。恰似画饼。食也难吞。'),
    19: dict(poem=['急水滩头放船归', '风波作浪欲何为', '若要安然求稳静', '等待浪静过此危'], jie='急水下船。险处待时。若问营谋。尽可施为。'),
    20: dict(poem=['当春久雨喜开晴', '玉兔金乌渐渐明', '旧事消散新事遂', '看看一跳过龙门']),
    21: dict(shiyi='此卦阴阳道合之象。凡事和合大吉也。'),
    22: dict(shiyi='此卦旱逢甘雨之象。凡事难中有救也。', jie='田蚕倍熟。命运渐来。病遇良药。行人便回。'),
    23: dict(poem=['欲扳仙桂入蟾宫', '岂虑天门不任君', '忽遇一般音信好', '人人皆笑岭顶花'], jie='商贾利益。行藏有危。病安讼遂。尽可施为。'),
    27: dict(poem=['一谋一用一番书', '虑后思前不敢为', '时到贵人相助力', '如山壁立可安居']),
    28: dict(poem=['东边月上正婵娟', '顷刻云遮亦暗存', '或有圆时还有缺', '更言非者亦闲言'], jie='浮云遮月。不须疑惑。等待云收。便见明白。'),
    31: dict(poem=['清闲无忧静处坐', '饱后吃茶时坐卧', '放下身心不用忙', '必定不招冤与祸']),
    32: dict(poem=['前程杳杳定无疑', '石中藏玉有谁知', '一朝良匠分明剖', '始觉安然碧玉期']),
    33: dict(jie='内藏金玉。何必外寻。遇贵指引。不须劳心。'),
    36: dict(poem=['眼前病讼不须忧', '满地资财尽可求', '恰似猿猴金锁脱', '自归山洞去来游']),
    38: dict(poem=['月照天书静处期', '忽遭云雾又昏迷', '宽心祈待云霞散', '此时更改好施为'], jie='家道忧凶。人口有灾。祈福保庆。犹恐破财。'),
    40: dict(poem=['红轮西坠兔东升', '阴长阳消百事亨', '若是女人宜望用', '增添财禄福其心']),
    41: dict(shiyi='此卦认贼作子之象。凡事认真防假。'),
    42: dict(poem=['君皇圣后总为恩', '复待祈禳无损增', '一切有情皆受用', '人间天上得期亨'], jie='天皇降恩。始终莫忘。晨昏礼佛。可宜烧香。'),
    46: dict(poem=['劝君耐守旧生涯', '把定心肠勿起歹', '直待有人轻着力', '枯枝老树再生花']),
    47: dict(jie='守旧变新。运至功成。遂平生志。尽皆是命。'),
    48: dict(poem=['昆鸟秋来化作鹏', '好游快乐喜飞腾', '翱翔万里云霄去', '余外诸禽总不能'], shiyi='此卦昆鹏兴变之象。凡事有变动大吉。'),
    49: dict(poem=['天寒地冻水成冰', '何须贪吝取功名', '只好守己静处坐', '待时兴变自然明']),
    51: dict(jie='进退莫疑。自有佳期。营谋用度。不须妄为。'),
    52: dict(poem=['水中捞月费功夫', '费尽功夫却又无', '莫说闲言并乱语', '枉劳心力强身枯'], jie='言语难思。费力劳心。宅中忧恼。待遇贵人。'),
    53: dict(poem=['失意反成得意时', '龙吟虎啸两相宜', '青天自有通霄路', '许我功名再有期'], jie='教去即去。教住即住。自有亨通。到头必利。'),
    56: dict(poem=['滩小石溪流水响', '清风明月贵人忙', '路须借问何方去', '莫取林中花草香']),
    58: dict(poem=['直言说话君须记', '莫在他乡求别艺', '切须守己旧生涯', '除此其余都不利'], shiyi='此卦守旧待时之象。凡事守旧则吉也。'),
    60: dict(jie='有千般计。不如莫动。一旦相惹。恐祸归身。'),
    62: dict(poem=['晨昏全赖佛扶持', '须是逢危却不危', '若得贵人相引处', '那时财帛亦相随'], jie='平平稳稳。四方名显。改旧从新。亦无凶险。'),
    64: dict(poem=['游鱼却在碧波池', '撞遭罗网四边围', '思量无计翻身出', '事到头来惹事非']),
    66: dict(poem=['路险马嬴人行急', '失群军卒困相当', '滩高风浪船棹破', '日暮花残天降霜'], jie='守旧待时。安静无咎。不用求谋。自在悠游。'),
    67: dict(poem=['一条金线秤君心', '无减无增无重轻', '为人平生心正直', '文章全具艺光明']),
    71: dict(poem=['认知苍龙下九衢', '女子当年嫁二夫', '自是一弓架两箭', '欲恐龙马不安居']),
    72: dict(poem=['养蜂须用求他蜜', '只怕遭触尾上针', '须是眼前有异路', '暗里深如荆棘林']),
    74: dict(shiyi='此卦似鹄投笼之象。凡事多虚少实也。', jie='进身不得。退步为难。低头直去。悉在其中。'),
    75: dict(poem=['恰如抱虎过高山', '战战竞竞胆碎寒', '不觉忽然从好事', '切须保守一身安'], shiyi='此卦抱虎过山之象。凡事险凶惊恐也。'),
    76: dict(shiyi='此卦鱼龙未变之象。凡事待时至可也。'),
    77: dict(poem=['梦中说得是多财', '声名云外总虚来', '水远山遥难信实', '贵人指点笑颜开']),
    79: dict(shiyi='此卦信实莫信虚之象。凡事守旧之兆也。'),
    81: dict(jie='心中取事。天必从之。营谋用事。尽可施为。'),
    86: dict(poem=['春来花发映阳台', '万里车来进宝财', '若得禹门三级浪', '恰如平地一声雷']),
    89: dict(jie='如石藏玉。贵人指示。得祗称心。欢怀得意。'),
    93: dict(poem=['鸾凤翔毛雨淋漓', '当时却被雀儿欺', '终教一日云开达', '依旧还君整羽衣']),
    94: dict(poem=['君子莫体小人为', '事若差池惹是非', '琴鸣须用知音听', '守常安静得依稀']),
    97: dict(poem=['当风点烛空疏影', '恍惚铺成镜里花', '累被儿童求收拾', '怎知只是幻浮槎']),
    98: dict(poem=['出入求谋事宜迟', '只恐闲愁惹是非', '如鸟飞入罗网里', '相逢能有几多时'], from_b=True),
    99: dict(poem=['勒马持鞭直过来', '半有忧危半有灾', '恰似遭火焚烧屋', '天降时雨荡成灰'], from_b=True),
    100: dict(poem=['佛神灵通与君知', '痴人说事转昏迷', '老人求得灵签去', '不如守旧待时来'], from_b=True,
              note='此是满签。诸事不利。大作福力。可保平安。'),
}

NOTE = re.compile(r'[（(][^）)]*[）)]')


def first_sentences(s, n=4):
    """Keep the first n '。'-separated phrases; A sometimes appends a second version."""
    parts = [p for p in s.split('。') if p]
    return '。'.join(parts[:n]) + '。' if parts else ''


def clean(s):
    s = NOTE.sub('', s or '')
    for tag in ('另作：', '此签'):
        if tag in s and not s.startswith(tag):
            s = s[:s.index(tag)]
    return s.replace(',', '。').strip()


def main():
    both = json.load(open(sys.argv[1]))
    A, B = both['nl'], both['d5']
    out = []
    for a, b in zip(A, B):
        n = a['n']
        fx = FIX.get(n, {})
        poem = fx.get('poem') or (a['poem2'][:4] if len(a['poem2']) >= 4 else a['poem'][:4])
        src = b if fx.get('from_b') else a
        shiyi = fx.get('shiyi') or clean(src['shiyi'])
        jie = fx.get('jie') or first_sentences(clean(src['jie']))
        xj_src = b['xianji'] if fx.get('from_b') else a['xianji']
        xianji = []
        for k, v in xj_src:
            k = k.replace('移徒', '移徙')
            if k == 'ww' or not re.fullmatch(r'[一-鿿]{2}', k):
                continue
            v = re.sub(r'[。.\s\xa0]', '', NOTE.sub('', v))
            xianji.append([k, v or '—'])
        lot = dict(n=n, title=a['title'], level=LEVEL.get(n, a['level']), gong=a['gong'],
                   poem=poem, shiyi=shiyi, jie=jie, xianji=xianji)
        assert len(poem) == 4 and all(len(p) == 7 for p in poem), (n, poem)
        if fx.get('note'):
            lot['note'] = fx['note']
        assert shiyi and jie and (len(xianji) >= 14 or lot.get('note')), (n, shiyi, jie, xianji)
        out.append(lot)
    assert [x['n'] for x in out] == list(range(1, 101))
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
