# `reference-library-builder` 技能

[English](README_EN.md)

![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![deps](https://img.shields.io/badge/deps-none%20(stdlib)-brightgreen)
![tests](https://img.shields.io/badge/tests-18%20passing-brightgreen)

一句话：把一串 DOI 变成**可核查的综述文献库**——元数据来自 Crossref 而不是手打，合法开放获取的 PDF 自动下载，RIS / EndNote ENW / BibTeX 三种引用文件一次生成，最后逐篇校验"下载到的 PDF 真的是这篇文献"。

它专门解决两件最常见的事故：库里一堆 PDF，但没人能把引用写对；以及参考文献表里的元数据是手输的，错在哪都不知道。

## 适合用它做什么

- 写综述前建立这篇综述的文献库：一个 DOI 列表进，`pdf/ + cite/ + index.csv` 出。
- 导出 RIS / ENW / BibTeX 给 Zotero、EndNote 或 LaTeX 直接用。
- 批量核对参考文献：哪些有开放获取版本、哪些必须走机构权限、哪些 DOI 是错的。
- 投稿前抽查"我引用的这篇，PDF 是不是真的这篇"。

不适合：把文献插进正文的引用标注（那是引用类 skill 的活）；核对已有参考文献表的字段一致性（那是文献校验类 skill 的活）。本 skill 只负责把库建对、验真，并把 `index.csv` 交出去。

## 四条底线

元数据一律以 Crossref 记录为准，不猜、不补、不"顺手修正"。只下载开放获取位置报告的合法 PDF。绝不绕过付费墙、登录、代理或出版社限制——没有合法副本时，这条文献就记为 `manual`，由作者用自己机构的权限去取。批量查询必须带联系邮箱并按默认 0.5 秒节流，别把公开接口当爬虫用。

## 用法

```bash
# 建库：解析元数据 + 写引用文件 + 下载开放获取 PDF
python3 scripts/refs.py build --input dois.txt --out 文献库 \
  --email you@example.com --pdf --formats ris,enw,bib

# 验真：确认每个 PDF 就是它声称的那篇
python3 scripts/refs.py verify --dir 文献库

# 只重建索引
python3 scripts/refs.py index --dir 文献库
```

真实运行结果（完整输出见 [examples/demo-library.md](examples/demo-library.md)）：

```text
library at 文献库: 5 references, 2 open PDF(s)
2 reference(s) need your own access:
  - 10.1038/nnano.2016.300  "Water-evaporation-induced electricity with nanostructured ca"
  - 10.1038/s41586-020-2010-9  "Power generation from ambient humidity using protein nanowir"

$ python3 scripts/refs.py verify --dir 文献库
OK       wu-2020-a-new-coronavirus-associated-with-human
OK       shan-2021-n-protein-presents-early-in-blood-dried
checked 2, mismatched 0, unverifiable 0
```

同一批里还故意放了一个错误 DOI 和一个 404：错误 DOI 只产生一行 `error`，不会中断其余文献的解析。

## 产出结构

```text
文献库/
|-- index.csv                机器可读状态表，一行一篇
|-- index.md                 同样的内容，肉眼可读
|-- library.ris              全库合并导入文件
|-- library.bib              全库合并 BibTeX
|-- cite/                    每篇一份 .ris / .enw / .bib
|-- meta/                    每篇的 Crossref 记录与开放获取位置
`-- pdf/                     开放获取 PDF
```

文件键稳定：`第一作者姓-年份-标题短句`，重跑同一 DOI 不会在 Zotero 里产生重复条目。`index.csv` 的 `oa_status` 只有 `open` / `manual` / `error` 三种，其中 `manual` 不是失败，而是"需要你自己的机构权限"。

## 关于合法性

只走 Unpaywall 报告的开放获取位置：出版社开放获取、机构库或作者自存档、预印本。付费墙论文一律留在 `manual` 状态并附 DOI 链接，由作者用机构订阅、馆际互借或向作者索取。这个 skill 不会去任何版权不明的镜像站找替代品，也不会把预印本当正式版本用。

## 安装

```bash
git clone https://github.com/HUC-he/reference-library-builder.git \
  ~/.codex/skills/reference-library-builder
```

或在 Codex 里说"用 `$skill-installer` 安装 `HUC-he/reference-library-builder`"，等价命令：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo HUC-he/reference-library-builder --path . --name reference-library-builder
```

## 依赖

零第三方依赖即可建库（只用标准库）。PDF 文本校验需要 `pymupdf`；装了它 `verify` 才能读 PDF 正文，没装会明确提示而不是假装校验通过。如果运行环境缺少 CA 证书，脚本会自动优先用 `certifi` 的证书链。

## 目录结构

```text
reference-library-builder/
|-- SKILL.md                            主入口：工作流、格式、合法性与红线
|-- references/
|   |-- sources-and-compliance.md       元数据/开放获取来源与合规边界
|   `-- library-layout.md               文件夹契约、命名与索引列
|-- scripts/refs.py                     build / verify / index
|-- tests/test_refs.py                  18 项离线测试（含真实 Crossref 记录夹具）
|-- examples/demo-library.md            真实 DOI 的完整运行实录
|-- manifest.yaml                       按阶段加载依赖的声明
`-- agents/openai.yaml                  UI 元数据
```

## 红线

绝不从付费墙、盗版镜像或来源不明的站点下载；绝不虚构 Crossref 没有给出的元数据；绝不在没校验、或校验失败时把文献标成 verified；绝不把 API key、令牌或代理凭据写进文献库、脚本或索引；绝不把预印本冒充正式版本（反之亦然）。

## 联系与关键词

作者 UUNICE（GitHub [@HUC-he](https://github.com/HUC-he)）。问题与改进建议：shiyuhe1@163.com。

关键词：文献库、批量下载文献、参考文献 PDF、导出 RIS、EndNote ENW、BibTeX、Zotero、DOI 校验、Crossref、Unpaywall、开放获取、综述文献管理、literature library、reference manager export。

## 许可

MIT，见 [LICENSE](LICENSE)。
