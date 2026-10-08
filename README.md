# 念佛计数

手机网页工具，微信里可直接打开：念佛计数、每日功课、《地藏菩萨本愿经》读诵、修行统计。

在线地址（开启 GitHub Pages 后）：https://imcodingman.github.io/Buddha-Name-Counting/

## 功能

- **念佛**：点圆盘计数，可切换 / 自定义佛号，按 108 颗念珠换算串数，每日目标 108 / 1080 / 3000 / 10000 可切换，支持撤销。
- **功课**：心经、地藏经等每日功课打卡，可增删功课、自定义数量和单位。
- **经文**：《地藏菩萨本愿经》十三品全文，目录跳转、字号调节；读到最后一品可一键记入当日功课。
- **统计**：今日 / 累计佛号、功课连续圆满天数、近七日柱状图、月历回看每一天的记录。
- **备份**：记录保存在本机浏览器（localStorage），可「复制备份」后发给自己，换手机或清缓存后「恢复备份」。
- 跟随系统自动切换深色模式。

## 部署到 GitHub Pages

纯静态页面，无需构建。仓库 **Settings → Pages → Build and deployment**：

- Source 选 **Deploy from a branch**
- Branch 选 `main`（或当前开发分支），目录选 `/ (root)`，保存

一两分钟后即可通过上面的地址访问，把链接发到微信里点开即可使用。

## 文件

- `index.html` / `style.css` / `app.js`：页面与逻辑，无第三方依赖
- `data/dizang.json`：经文数据，据 CBETA 电子佛典《大正藏》第 13 册 No. 412（[cbeta-org/xml-p5](https://github.com/cbeta-org/xml-p5)）转为简体
