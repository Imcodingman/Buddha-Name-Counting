"""Build data/lingqian-detail.json: plain-language readings for each 观音灵签.

Usage: python3 tools/build_lingqian_detail.py PAGES_DIR data/lingqian-detail.json
PAGES_DIR holds nl/{1..100}.html (www.nongli.com/item5/guanyin/N.html) and
d5/{1..100}.html (3g.d5168.com/chouqian/guanyin/4/N/). nongli is the base; a
section missing there is taken from d5168 (lots 51, 62, 98).

Output per lot: {n, summary: [...], essence, topics: [[name, [lines]]], stories: [[title, [paras]]]}
"""
import html
import json
import re
import sys

TOPICS = ['凡事做事', '爱情婚姻', '工作求职 创业事业', '经商生意', '投资理财', '考试竞赛 升迁竞选',
          '房地交易', '治病健康', '求孕求子', '转换变更', '官司诉讼', '寻人寻物', '远行出国']
LABEL = {'工作求职 创业事业': '工作事业', '考试竞赛 升迁竞选': '考试升迁', '经商生意': '经商生意',
         '投资理财': '投资理财', '凡事做事': '凡事总论'}
STOPS = set(TOPICS) | {'整体解译', '本签精髓', '签诗故事一', '签诗故事二', '签诗故事', '治国理民', '政局前途',
                       '上一篇：', '典故', '观音灵签白话详解如下：', '诗文解译'}


def lines(path):
    s = open(path, encoding='utf-8-sig', errors='replace').read()
    s = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S | re.I)
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    t = html.unescape(re.sub(r'<[^>]+>', '\n', s))
    t = re.sub(r'本文来[^\n]*?网', '', t)
    out = []
    for l in t.split('\n'):
        l = l.replace('　', ' ').replace('\xa0', ' ').strip()
        l = re.sub(r'^观音灵签\d+:\s*', '', l)
        if l:
            out.append(l)
    return out


def section(L, head):
    if head not in L:
        return []
    out = []
    for l in L[L.index(head) + 1:]:
        if l in STOPS or l.startswith('（占卜问卦') or re.match(r'观音灵签第\d+签$', l):
            break
        out.append(l)
    return out


def stories(L):
    res = []
    for head in ('签诗故事一', '签诗故事二', '签诗故事'):
        body = section(L, head)
        if body:
            title = body[0].lstrip('◇').strip() if body[0].startswith('◇') else ''
            paras = body[1:] if title else body
            res.append([title, paras])
    return res


def build(n, base):
    nl, d5 = lines(f'{base}/nl/{n}.html'), lines(f'{base}/d5/{n}.html')

    def pick(head):
        return section(nl, head) or section(d5, head)
    summary = pick('整体解译')
    essence = ''.join(pick('本签精髓'))
    topics = []
    for t in TOPICS:
        body = pick(t)
        if body:
            topics.append([LABEL.get(t, t), body])
    st = stories(nl)
    if not st:
        dg = section(d5, '典故')
        if dg:
            st = [['', dg]]
    return dict(n=n, summary=summary, essence=essence, topics=topics, stories=st)


def main():
    base, dest = sys.argv[1], sys.argv[2]
    out = [build(n, base) for n in range(1, 101)]
    for x in out:
        assert x['summary'] and x['essence'] and len(x['topics']) >= 8 and x['stories'], x['n']
    with open(dest, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
