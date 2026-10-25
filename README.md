# 小鹤音形 · 极简 Rime 配置

固定音形码表优先，小鹤双拼整句补充；不学习、不调频。支持 macOS 鼠须管与 Windows 小狼毫，适合以盲打为主、偶尔查看候选的使用者。

这是第三方配置项目，与小鹤官方、落格输入法和 Rime 官方没有隶属关系。

**仓库附带当前使用的完整音形码表（41,685 条），默认即可安装；字体不打包。** 码表基于使用者搜集的公开流传版本，经自定义修改并转换为 Rime 格式，原始来源和再分发授权尚未核实。配置/代码的 GPL 许可不覆盖码表数据，公开可下载不等于全部材料都获得开源授权。详见[码表来源说明](tables/PROVENANCE.md)及[授权调查](docs/LICENSING.md)。

## 交给智能体的一句话

> 请帮我安装 https://github.com/nufegia/rime-xiaohe-minimal ，先阅读 README 和 docs/AGENT_INSTALL.md，识别 Windows 或 macOS，备份并保留现有 Rime 方案，配置对应平台主题和 MiSans 同系列字体，使用仓库附带码表（已有同名本地码表则先保留并比较），保持不学习不调频，重新部署并验证日期、快捷选词和回退；若缺少依赖、字体或需要系统手动启用输入法，请明确告诉我，不要静默覆盖已有词库或声称未验证的步骤已经成功。

## 输入体验

- 固定码表精确候选保持码表顺序；双拼整句作为补充。
- 空格上屏，不启用四码自动上屏。
- `;` 选择当前页第二项，`'` 选择当前页第三项。
- `Tab` / `Shift+Tab`，以及 `=` / `-` 翻页。
- `op` 实时生成五种日期：`20261025`、`2026-10-25`、`2026.10.25`、`2026-10-25 17:26`、`2026年10月25日17时26分`（此处时间仅作示例）。每页三项，后两项在下一页。
- 禁用自动学习、用户词频排序和自动造词；仍支持由内置词典进行整句组词。
- 三候选、横排、无编号、无编码注释，中性灰极简样式，明暗配色跟随系统。
- 使用 **MiSans 字体及同系列 MiSans L3 生僻字扩展**。不保证覆盖所有 Unicode 汉字。

macOS：主题绘制阴影为零，但鼠须管 1.1.2 仍固定启用 macOS 外层窗口阴影。Windows：独立设置 `shadow_radius: 0` 和透明阴影色。两平台使用相近风格，不承诺像素一致。

## 安装

前置条件：已安装支持 librime-lua 的鼠须管或小狼毫，具备 `luna_pinyin` 词典、`t2s.json` 转换资源，Python 3.10+ 和依赖。本仓库不替代系统输入法安装器。

```sh
git clone https://github.com/nufegia/rime-xiaohe-minimal.git
cd rime-xiaohe-minimal
python3 -m venv .venv
# macOS
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/manage.py install
```

Windows PowerShell（建议使用 Windows 原生 Python，不要用 WSL 的 Python 修改 Windows 输入法）：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/manage.py install
```

默认安装仓库附带码表。若目标电脑已有兼容同名表，默认保留；要明确替换，可加 `--table PATH`。也支持现有、独立的 `loginput_xiaohe_fixed.dict.yaml`，会保留其字词、权重和排序。纯文本格式必须为 UTF-8 的 `文字<TAB>编码[<TAB>权重]`；纯文本导入时按每个编码下的原行序赋权，而非采用第三列的历史频率。

若用户目录已经有兼容的固定词典，可以省略 `--table`；安装器只在本机读取，不上传。用户另行提供的私人码表与导入产物请放在仓库外或 `local/` 下。

无音形码表，仅体验小鹤双拼整句：

```sh
python scripts/manage.py install --phonetic-only
```

安装器默认写入 macOS 的 `~/Library/Rime` 或 Windows 的 `%APPDATA%\Rime`。小狼毫可使用自定义用户目录，请先通过输入法菜单确认，用 `--user-dir PATH` 指定。`--dry-run` 可以提前查看修改计划。

安装后必须重新部署：macOS 用菜单「重新部署」，或运行 `/Library/Input Methods/Squirrel.app/Contents/MacOS/Squirrel --reload`；Windows 用小狼毫托盘菜单「重新部署」。系统首次添加输入法可能需要手动完成。

```sh
python scripts/manage.py doctor
```

`doctor` 检查生成后的禁用学习设置和每页数量，不代表 Lua、字体或候选窗口都经过实机验证。还需按[智能体安装指南](docs/AGENT_INSTALL.md)测试实际输入。

## 备份与回退

安装器只安装本方案文件，并向方案菜单追加本方案；不覆盖整个用户文件夹，不修改其他方案的全局外观。安装前会保存被修改文件和清单到用户目录下 `.xiaohe-backups/时间/`。

```sh
python scripts/manage.py restore --backup "/安装时显示的备份目录"
```

然后重新部署。若文件在安装后又改过，回退工具会拒绝覆盖，要求人工合并。旧学习数据库不会删除；本方案禁用其读取和学习，因此旧调频不参与候选排序。备份可能含私人配置，请勿公开。

## 授权、字体与测试状态

- 配置和程序采用 GPL-3.0-or-later；双拼拼写规则参考 Rime 官方小鹤双拼，保留来源说明，见 [NOTICE](NOTICE)。
- 附带码表及外部导入码表不受本仓库 GPL 许可证重新授权；附带表的来源和再分发授权未核实，第三方权利保留。[授权调查与发布边界](docs/LICENSING.md)
- MiSans 需注明使用；署名不能替代其他许可条件。请从[小米官网](https://hyperos.mi.com/font/zh/download/)取得 MiSans Regular 与 MiSans L3，原样安装，不向本仓库上传字体。
- macOS 已验证本机 Rime 引擎输入、码表导入及字体覆盖；Windows 外观按小狼毫官方配置和代码适配。安装器自动测试覆盖 macOS / Windows；原生 Windows 候选窗口与字体显示仍需实机验收。详见 [测试说明](docs/TESTING.md)。

原项目名称、版权和商标均归各自权利人所有。本项目不是官方“小鹤音形”发布版。
