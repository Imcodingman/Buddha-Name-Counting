(function () {
  'use strict';

  var SUTRA_URL = 'data/dizang.json';
  var STORE_KEY = 'nianfo-record-v1';
  var NAMES0 = ['南无阿弥陀佛', '南无地藏王菩萨', '南无观世音菩萨', '南无本师释迦牟尼佛'];
  var ITEMS0 = [
    { id: 'xj', name: '心经', target: 7, unit: '遍' },
    { id: 'dzj', name: '地藏经', target: 1, unit: '部', sutra: true }
  ];
  var GOALS = [108, 1080, 3000, 10000];
  var WK = ['日', '一', '二', '三', '四', '五', '六'];

  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function dkey(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function addDays(d, n) { return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n); }
  function sumObj(o) { var s = 0; if (o) { for (var k in o) { s += o[k] || 0; } } return s; }
  function dayLabel(d) { return (d.getMonth() + 1) + '月' + d.getDate() + '日 周' + WK[d.getDay()]; }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function loadSaved() {
    try { var s = window.localStorage.getItem(STORE_KEY); return s ? JSON.parse(s) : null; } catch (e) { return null; }
  }

  var saved = loadSaved() || {};
  var S = {
    tab: 'count',
    names: saved.names || NAMES0.slice(),
    cur: saved.cur || 0,
    goal: saved.goal || 1080,
    items: saved.items || ITEMS0.map(function (x) { return Object.assign({}, x); }),
    rec: saved.rec || {},
    ch: saved.ch || 0,
    fs: saved.fs || 19,
    sutra: null, sutraErr: false, sutraLoading: false, toc: false,
    addingName: false, newName: '',
    editHw: false, hwName: '', hwTarget: '7', hwUnit: '遍',
    selDay: null, monthOff: 0, pulse: 0, credited: false
  };

  var view = document.getElementById('view');
  var scrollEl = document.getElementById('scroll');
  var tabsEl = document.getElementById('tabs');

  function persist() {
    try {
      window.localStorage.setItem(STORE_KEY, JSON.stringify({
        names: S.names, cur: S.cur, goal: S.goal, items: S.items, rec: S.rec, ch: S.ch, fs: S.fs
      }));
    } catch (e) {}
  }

  function set(patch) {
    for (var k in patch) S[k] = patch[k];
    persist();
    render();
  }

  function toTop() { scrollEl.scrollTop = 0; }

  function toast(msg) {
    var t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 2200);
  }

  function bump(kind, id, delta) {
    var k = dkey(new Date());
    var rec = Object.assign({}, S.rec);
    var old = rec[k] || { c: {}, h: {} };
    var day = { c: Object.assign({}, old.c), h: Object.assign({}, old.h) };
    day[kind][id] = Math.max(0, (day[kind][id] || 0) + delta);
    rec[k] = day;
    var next = { rec: rec };
    if (kind === 'c' && delta > 0) next.pulse = S.pulse + 1;
    set(next);
  }

  function loadSutra() {
    if (S.sutra || S.sutraLoading) return;
    S.sutraLoading = true; S.sutraErr = false;
    var xhr = new XMLHttpRequest();
    xhr.open('GET', SUTRA_URL, true);
    xhr.onload = function () {
      S.sutraLoading = false;
      try {
        if (xhr.status >= 200 && xhr.status < 300) { S.sutra = JSON.parse(xhr.responseText); }
        else S.sutraErr = true;
      } catch (e) { S.sutraErr = true; }
      render();
    };
    xhr.onerror = function () { S.sutraLoading = false; S.sutraErr = true; render(); };
    xhr.send();
  }

  function isFull(day) {
    if (!day || !S.items.length) return false;
    return S.items.every(function (it) { return ((day.h || {})[it.id] || 0) >= it.target; });
  }
  function hasAny(day) { return !!day && (sumObj(day.c) > 0 || sumObj(day.h) > 0); }

  function header(title, right) {
    return '<div class="head"><div class="col"><span class="date">' + dayLabel(new Date()) +
      '</span><h1 class="title">' + title + '</h1></div>' + (right || '') + '</div>';
  }

  /* ============ 念佛 ============ */
  function viewCount() {
    var tk = dkey(new Date());
    var today = S.rec[tk] || { c: {}, h: {} };
    var curName = S.names[S.cur] || S.names[0];
    var curCount = today.c[curName] || 0;
    var ratio = Math.min(1, curCount / S.goal);
    var deg = Math.round(ratio * 360);
    var pulseCls = S.pulse === 0 ? '' : (S.pulse % 2 ? ' pa' : ' pb');

    var h = '<div class="page">';
    h += header('念佛', '<div class="col r"><span class="date">今日合计</span><span class="serif num" style="font-size:22px;font-weight:600">' + sumObj(today.c) + '</span></div>');

    h += '<div class="hscroll">';
    S.names.forEach(function (n, i) {
      h += '<button class="chip' + (i === S.cur ? ' on' : '') + '" data-act="pick" data-v="' + i + '">' + esc(n) + '</button>';
    });
    h += '<button class="chip add" data-act="toggleAddName">' + (S.addingName ? '收起' : '+ 自定义') + '</button></div>';

    if (S.addingName) {
      h += '<div class="row-add"><label class="field">新佛号' +
        '<input class="input" data-in="newName" value="' + esc(S.newName) + '" placeholder="如：南无药师琉璃光如来" maxlength="30"></label>' +
        '<button class="btn-accent" data-act="confirmName">添加</button></div>';
    }

    h += '<div class="ring-wrap"><div class="ring" style="background:conic-gradient(var(--accent) ' + deg + 'deg, var(--line) 0deg)">' +
      '<button class="tap' + pulseCls + '" data-act="tap" aria-label="念一声，计数加一">' +
      '<span class="nm">' + esc(curName) + '</span>' +
      '<span class="ct num">' + curCount + '</span>' +
      '<span class="gl">目标 ' + S.goal + ' 声 · ' + Math.floor(ratio * 100) + '%</span></button></div></div>';
    h += '<p class="hint">念一声，点一下圆盘</p>';

    h += '<div class="grid3">' +
      '<div class="tile"><span class="k">念珠</span><span class="v">' + Math.floor(curCount / 108) + ' <small>串</small></span></div>' +
      '<div class="tile"><span class="k">本串</span><span class="v">' + (curCount % 108) + '<small> / 108</small></span></div>' +
      '<button class="tile ghost" data-act="undo"><span class="k">点错了</span><span class="act">撤销一声</span></button></div>';

    h += '<button class="bar-btn" data-act="cycleGoal"><span>每日目标</span><span class="a">' + S.goal + ' 声 · 切换</span></button>';
    h += '</div>';
    return h;
  }

  /* ============ 功课 ============ */
  function viewHw() {
    var tk = dkey(new Date());
    var today = S.rec[tk] || { c: {}, h: {} };
    var done = 0;
    var cards = S.items.map(function (it) {
      var n = today.h[it.id] || 0, ok = n >= it.target, unit = it.unit || '遍';
      if (ok) done++;
      var c = '<div class="card"><div class="card-h"><div class="col"><span class="nm">' + esc(it.name) +
        '</span><span class="date">每日 ' + it.target + ' ' + esc(unit) + '</span></div>';
      if (ok && !S.editHw) c += '<span class="seal s">圆满</span>';
      if (S.editHw) c += '<button class="small-btn" data-act="removeHw" data-v="' + esc(it.id) + '">删除</button>';
      c += '</div>';
      if (it.target <= 21) {
        c += '<div class="dots">';
        for (var j = 0; j < it.target; j++) c += '<span class="dot' + (j < n ? ' on' : '') + '"></span>';
        c += '</div>';
      } else {
        c += '<div class="prog"><i style="width:' + Math.min(100, Math.round(n * 100 / it.target)) + '%"></i></div>';
      }
      c += '<div class="stepper"><button class="minus" data-act="hwDec" data-v="' + esc(it.id) + '" aria-label="减一">−</button>' +
        '<div class="mid"><b class="num">' + n + '</b><span> / ' + it.target + ' ' + esc(unit) + '</span></div>' +
        '<button class="plus btn-accent" data-act="hwInc" data-v="' + esc(it.id) + '">记一' + esc(unit) + '</button></div>';
      if (it.sutra && !S.editHw) c += '<button class="link" data-act="go" data-v="read">打开经文读诵 →</button>';
      c += '</div>';
      return c;
    });

    var h = '<div class="page tight">';
    h += header('每日功课', '<button class="pill" data-act="toggleEditHw">' + (S.editHw ? '完成' : '管理') + '</button>');
    h += '<div class="summary"><span>今日已完成 <strong>' + done + '</strong> / ' + S.items.length + ' 项</span>' +
      (S.items.length > 0 && done === S.items.length ? '<span class="seal">功课圆满</span>' : '') + '</div>';
    h += cards.join('');
    if (!S.items.length && !S.editHw) h += '<p class="hint">还没有功课，点右上角「管理」添加。</p>';
    if (S.editHw) {
      h += '<div class="card dash"><span style="font-size:15px;font-weight:500">添加一项功课</span>' +
        '<label class="field">功课名称<input class="input" data-in="hwName" value="' + esc(S.hwName) + '" placeholder="如：大悲咒、往生咒" maxlength="20"></label>' +
        '<div class="grid2"><label class="field">每日数量<input class="input" type="number" inputmode="numeric" min="1" data-in="hwTarget" value="' + esc(S.hwTarget) + '"></label>' +
        '<label class="field">单位<input class="input" data-in="hwUnit" value="' + esc(S.hwUnit) + '" placeholder="遍" maxlength="4"></label></div>' +
        '<button class="btn-accent block-btn" data-act="addHw">添加</button></div>';
    }
    h += '</div>';
    return h;
  }

  /* ============ 经文 ============ */
  function viewRead() {
    loadSutra();
    var chs = S.sutra || [];
    var idx = Math.min(S.ch, Math.max(0, chs.length - 1));
    var ch = chs[idx];
    var dzj = S.items.filter(function (x) { return x.sutra; })[0];
    var isLast = chs.length > 0 && idx === chs.length - 1;

    var h = '<div class="reader"><div class="reader-bar">' +
      '<button class="pill" data-act="toggleToc">' + (S.toc ? '返回经文' : '目录') + '</button>' +
      '<span class="date">第 ' + (idx + 1) + ' / ' + (chs.length || 13) + ' 品</span>' +
      '<div style="display:flex;gap:6px"><button class="round" style="font-size:14px" data-act="fsDown" aria-label="字号减小">A−</button>' +
      '<button class="round" style="font-size:18px" data-act="fsUp" aria-label="字号增大">A+</button></div></div>';

    if (S.toc) {
      h += '<div class="toc">';
      chs.forEach(function (c, i) {
        h += '<button class="' + (i === idx ? 'cur' : '') + '" data-act="pickCh" data-v="' + i + '"><span class="n">' + (i + 1) + '</span><span>' + esc(c.title) + '</span></button>';
      });
      if (!chs.length) h += '<p class="msg">' + (S.sutraErr ? '目录暂时没有加载出来。' : '加载中…') + '</p>';
      h += '</div></div>';
      return h;
    }

    h += '<div class="ch-head"><span class="sutra">地藏菩萨本愿经</span><h2>' + esc(ch ? ch.title : '地藏菩萨本愿经') + '</h2>' +
      (idx === 0 ? '<span class="by">唐 于阗国三藏沙门 实叉难陀 译</span>' : '') + '</div>';

    if (!S.sutra && !S.sutraErr) h += '<p class="msg">经文加载中…</p>';
    if (S.sutraErr) h += '<p class="msg">经文暂时没有加载出来。<br><button class="link" style="align-self:center" data-act="retrySutra">点此重试</button></p>';

    if (ch) {
      ch.paras.forEach(function (p) {
        h += '<p class="para ' + (p.v ? 'verse' : 'prose') + '" style="font-size:' + S.fs + 'px">' + esc(p.t) + '</p>';
      });
    }

    h += '<div class="reader-foot">';
    if (isLast && dzj && !S.credited) h += '<button class="finish btn-accent" data-act="finishSutra">读诵圆满 · 记入今日功课</button>';
    if (isLast && dzj && S.credited) {
      var tk = dkey(new Date());
      h += '<p class="credited">已记入今日功课：' + esc(dzj.name) + ' ' + ((S.rec[tk] && S.rec[tk].h[dzj.id]) || 0) + ' ' + esc(dzj.unit || '部') + '</p>';
    }
    h += '<div class="grid2"><button class="nav-btn" data-act="prevCh"' + (idx > 0 ? '' : ' disabled') + '>‹ 上一品</button>' +
      '<button class="nav-btn" data-act="nextCh"' + (chs.length && idx < chs.length - 1 ? '' : ' disabled') + '>下一品 ›</button></div>';
    h += '<p class="src">经文据 CBETA 电子佛典《大正藏》第 13 册 No. 412，简体转写</p></div></div>';
    return h;
  }

  /* ============ 统计 ============ */
  function viewStats() {
    var now = new Date(), tk = dkey(now);
    function getDay(k) { return S.rec[k] || null; }

    var allTotal = 0;
    for (var k in S.rec) allTotal += sumObj(S.rec[k].c);
    var streak = 0;
    for (var si = isFull(getDay(tk)) ? 0 : 1; si < 3650; si++) {
      if (isFull(getDay(dkey(addDays(now, -si))))) streak++; else break;
    }

    var vals = [], maxV = 1;
    for (var bi = 6; bi >= 0; bi--) {
      var bd = addDays(now, -bi), bdy = getDay(dkey(bd)), v = sumObj(bdy && bdy.c);
      vals.push({ d: bd, v: v, today: bi === 0 });
      if (v > maxV) maxV = v;
    }

    var h = '<div class="page tight">' + header('统计');
    h += '<div class="grid3">' +
      '<div class="tile"><span class="k">今日佛号</span><span class="v num">' + sumObj((S.rec[tk] || {}).c) + '</span></div>' +
      '<div class="tile"><span class="k">累计佛号</span><span class="v num">' + allTotal + '</span></div>' +
      '<div class="tile"><span class="k">功课连续圆满</span><span class="v">' + streak + ' <small>天</small></span></div></div>';

    h += '<div class="card"><span style="font-size:15px;font-weight:500">近七日佛号</span><div class="chart">';
    vals.forEach(function (x) {
      var lb = x.v >= 1000 ? (x.v / 1000).toFixed(1) + 'k' : String(x.v);
      var bh = x.v ? Math.max(4, Math.round(x.v / maxV * 100)) : 0;
      h += '<div class="c' + (x.today ? ' today' : '') + '"><span class="lb num">' + lb + '</span><div class="b" style="height:' + bh + 'px"></div><span class="d">' + (x.today ? '今' : WK[x.d.getDay()]) + '</span></div>';
    });
    h += '</div></div>';

    var base = new Date(now.getFullYear(), now.getMonth() + S.monthOff, 1);
    var lead = (base.getDay() + 6) % 7;
    var dim = new Date(base.getFullYear(), base.getMonth() + 1, 0).getDate();
    var selKey = S.selDay || tk;
    h += '<div class="card" style="gap:12px"><div class="cal-h"><button data-act="monthPrev" aria-label="上个月">‹</button>' +
      '<span>' + base.getFullYear() + '年' + (base.getMonth() + 1) + '月</span>' +
      '<button data-act="monthNext" aria-label="下个月"' + (S.monthOff < 0 ? '' : ' disabled') + '>›</button></div>' +
      '<div class="wk"><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span></div><div class="cal">';
    for (var li = 0; li < lead; li++) h += '<span></span>';
    for (var dn = 1; dn <= dim; dn++) {
      var cd = new Date(base.getFullYear(), base.getMonth(), dn), ck = dkey(cd);
      var future = cd > now, cday = getDay(ck), full = isFull(cday), any = hasAny(cday);
      var cls = (full ? ' full' : any ? ' any' : '') + (future ? ' future' : '') + (ck === tk ? ' today' : '') + (ck === selKey ? ' sel' : '');
      h += '<button class="' + cls + '" data-act="pickDay" data-v="' + ck + '"' + (future ? ' disabled' : '') +
        ' aria-label="' + dayLabel(cd) + (full ? '，功课圆满' : any ? '，有记录' : '') + '">' + dn + '</button>';
    }
    h += '</div><div class="legend"><span><i class="f"></i>功课圆满</span><span><i></i>有记录</span></div></div>';

    var sp = selKey.split('-');
    var selDate = new Date(+sp[0], +sp[1] - 1, +sp[2]);
    var selD = getDay(selKey);
    h += '<div class="card" style="gap:10px"><span style="font-size:15px;font-weight:500">' + dayLabel(selDate) + (selKey === tk ? ' · 今天' : '') + '</span>';
    if (!hasAny(selD)) {
      h += '<p style="font-size:14px" class="sub">这一天还没有记录。</p>';
    } else {
      for (var nm in selD.c) {
        if (selD.c[nm] > 0) h += '<div class="kv"><span>' + esc(nm) + '</span><span class="r">' + selD.c[nm] + ' 声</span></div>';
      }
      if (S.items.length) {
        h += '<div class="hr"></div>';
        S.items.forEach(function (it) {
          var n = (selD.h || {})[it.id] || 0, ok = n >= it.target;
          h += '<div class="kv"><span>' + esc(it.name) + '</span><span class="r' + (ok ? ' ok' : '') + '">' + n + ' / ' + it.target + ' ' + esc(it.unit || '遍') + (ok ? ' · 圆满' : '') + '</span></div>';
        });
      }
    }
    h += '</div>';

    h += '<div class="card" style="gap:10px"><span style="font-size:15px;font-weight:500">数据备份</span>' +
      '<p class="note">记录只保存在本机浏览器里。清理微信缓存或换手机前，请先「复制备份」，把内容发给自己保存；之后可用「恢复备份」粘贴回来。</p>' +
      '<div class="data-row"><button data-act="exportData">复制备份</button><button data-act="importData">恢复备份</button></div></div>';
    h += '</div>';
    return h;
  }

  function render() {
    var fn = { count: viewCount, hw: viewHw, read: viewRead, stats: viewStats }[S.tab];
    view.innerHTML = fn();
    var btns = tabsEl.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
      btns[i].className = btns[i].getAttribute('data-v') === S.tab ? 'on' : '';
    }
  }

  function copyText(text) {
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
      document.body.appendChild(ta);
      ta.select();
      ta.setSelectionRange(0, text.length);
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) {}
      document.body.removeChild(ta);
      return ok;
    }
    if (fallback()) { toast('备份已复制，请粘贴发给自己保存'); return; }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { toast('备份已复制，请粘贴发给自己保存'); },
        function () { window.prompt('请长按全选并复制以下内容：', text); });
    } else {
      window.prompt('请长按全选并复制以下内容：', text);
    }
  }

  var actions = {
    go: function (v) { set({ tab: v, toc: false }); toTop(); },
    pick: function (v) { set({ cur: +v }); },
    toggleAddName: function () { set({ addingName: !S.addingName }); },
    confirmName: function () {
      var v = (S.newName || '').trim();
      if (!v) return;
      var names = S.names.slice(), at = names.indexOf(v);
      if (at < 0) { names.push(v); at = names.length - 1; }
      set({ names: names, cur: at, newName: '', addingName: false });
    },
    tap: function () {
      bump('c', S.names[S.cur] || S.names[0], 1);
      try { if (navigator.vibrate) navigator.vibrate(12); } catch (e) {}
    },
    undo: function () { bump('c', S.names[S.cur] || S.names[0], -1); },
    cycleGoal: function () { var gi = GOALS.indexOf(S.goal); set({ goal: GOALS[(gi + 1) % GOALS.length] }); },

    toggleEditHw: function () { set({ editHw: !S.editHw }); },
    hwInc: function (v) { bump('h', v, 1); },
    hwDec: function (v) { bump('h', v, -1); },
    removeHw: function (v) {
      var it = S.items.filter(function (x) { return x.id === v; })[0];
      if (it && !window.confirm('删除功课「' + it.name + '」？已有的记录不会被删除。')) return;
      set({ items: S.items.filter(function (x) { return x.id !== v; }) });
    },
    addHw: function () {
      var nm = (S.hwName || '').trim(), tg = parseInt(S.hwTarget, 10);
      if (!nm) { toast('请填写功课名称'); return; }
      if (!(tg > 0)) { toast('每日数量需大于 0'); return; }
      var item = { id: 'h' + Date.now(), name: nm, target: Math.min(tg, 9999), unit: (S.hwUnit || '遍').trim() || '遍' };
      if (nm.indexOf('地藏') >= 0 && !S.items.some(function (x) { return x.sutra; })) item.sutra = true;
      set({ items: S.items.concat([item]), hwName: '', hwTarget: '7', hwUnit: '遍', editHw: false });
    },

    toggleToc: function () { set({ toc: !S.toc }); toTop(); },
    pickCh: function (v) { set({ ch: +v, toc: false, credited: false }); toTop(); },
    fsUp: function () { set({ fs: Math.min(27, S.fs + 2) }); },
    fsDown: function () { set({ fs: Math.max(15, S.fs - 2) }); },
    prevCh: function () { if (S.ch > 0) { set({ ch: S.ch - 1, credited: false }); toTop(); } },
    nextCh: function () { if (S.sutra && S.ch < S.sutra.length - 1) { set({ ch: S.ch + 1, credited: false }); toTop(); } },
    retrySutra: function () { S.sutraErr = false; render(); },
    finishSutra: function () {
      var dzj = S.items.filter(function (x) { return x.sutra; })[0];
      if (!dzj) return;
      S.credited = true;
      bump('h', dzj.id, 1);
    },

    monthPrev: function () { set({ monthOff: S.monthOff - 1 }); },
    monthNext: function () { if (S.monthOff < 0) set({ monthOff: S.monthOff + 1 }); },
    pickDay: function (v) { set({ selDay: v }); },
    exportData: function () {
      copyText(JSON.stringify({ app: 'nianfo', v: 1, names: S.names, cur: S.cur, goal: S.goal, items: S.items, rec: S.rec, ch: S.ch, fs: S.fs }));
    },
    importData: function () {
      var txt = window.prompt('请粘贴之前复制的备份内容：', '');
      if (!txt) return;
      var d;
      try { d = JSON.parse(txt.trim()); } catch (e) { d = null; }
      if (!d || d.app !== 'nianfo' || typeof d.rec !== 'object' || !Array.isArray(d.names) || !Array.isArray(d.items)) {
        toast('备份内容无法识别');
        return;
      }
      if (!window.confirm('恢复备份会覆盖本机当前的全部记录，确定吗？')) return;
      set({ names: d.names, cur: d.cur || 0, goal: d.goal || 1080, items: d.items, rec: d.rec, ch: d.ch || 0, fs: d.fs || 19, selDay: null });
      toast('已恢复备份');
    }
  };

  document.addEventListener('click', function (e) {
    var el = e.target.closest ? e.target.closest('[data-act]') : null;
    if (!el || el.disabled) return;
    var fn = actions[el.getAttribute('data-act')];
    if (fn) fn(el.getAttribute('data-v'));
  });

  view.addEventListener('input', function (e) {
    var key = e.target.getAttribute && e.target.getAttribute('data-in');
    if (key) S[key] = e.target.value;
  });

  view.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter') return;
    var key = e.target.getAttribute && e.target.getAttribute('data-in');
    if (key === 'newName') actions.confirmName();
    else if (key) actions.addHw();
  });

  // Refresh when returning to the page (e.g. the date changed overnight).
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden && !document.querySelector('input:focus')) render();
  });

  render();
})();
