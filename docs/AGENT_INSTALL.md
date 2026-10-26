# 智能体安装指南

本指南用于帮助当前用户在本机安装，不授权上传本地资料、公开私人词库或改变其他输入方案。用户要求安装本仓库时，可以在其授权范围内检查依赖、备份、导入码表和部署；系统权限弹窗交由用户处理。

## 1. 确认环境

1. 识别 macOS / Windows / Linux，Linux 进一步确认 Fcitx5 或 IBus，使用该系统的原生 Python 3.10+。优先建立虚拟环境并安装 requirements.txt。
2. 检查鼠须管 / 小狼毫 / fcitx5-rime / ibus-rime 是否存在及其版本。如果缺失，使用官方发行渠道：https://rime.im/download/ 。不要替换成未经核实的第三方二进制。
3. 找到实际用户目录：macOS 通常为 ~/Library/Rime；Windows 通常为 %APPDATA%\Rime，但小狼毫允许自定义，需查看输入法菜单「用户文件夹」或已安装配置。Linux：Fcitx5 通常为 ~/.local/share/fcitx5/rime，IBus 通常为 ~/.config/ibus/rime，Fcitx5 遵循 XDG_DATA_HOME，上游 IBus Rime 当前直接使用 HOME/.config，不遵循 XDG_CONFIG_HOME；Flatpak 等特殊打包须先确认实际目录。
4. 检查 librime-lua、luna_pinyin 词典和 OpenCC 的 t2s.json、s2t.json 及其字词典。不能只凭文件复制成功就断言支持 Lua。缺少 luna_pinyin 可参照 Rime 官方配方 https://github.com/rime/rime-luna-pinyin 安装，并保留它的许可；不要盲目替换 DLL 或占用中的输入法程序。

## 2. 码表与字体

1. 先检查当前用户是否已有兼容码表。完整复现必须使用同一份表，不要静默换成其他“小鹤”表。不要扫描无关私人文件。
2. 本仓库附带当前使用的码表，但原始来源及再分发授权未核实。先让用户看到 README 的来源和许可说明，不把码表宣称为 GPL 数据。若无同名本地表，默认安装附带表；有同名表则保留，替换前比较差异。用户也可提供另一份有权使用的表。不要擅自将本地私人表上传仓库。
3. 兼容独立 Rime 词典名为 loginput_xiaohe_fixed；纯文本格式见 README。导入器不会自动识别二进制 .bin 码表，不尝试反编译。
4. 当前配置使用 MiSans Regular + 同系列 MiSans L3 扩展。先检测字体是否已安装，避免重复安装。从 https://hyperos.mi.com/font/zh/download/ 查看许可并原样安装。不把字体提交到 Git、镜像到公开仓库或修改合并字体文件。
5. 许可要求在软件中注明 MiSans，本仓库已在配置和 README 注明；使用者仍需遵守官网其余条款。若用户不愿安装该字体，明确告知更换字体会改变外观及生僻字覆盖。

## 3. 安装并部署

1. 阅读 scripts/manage.py；先使用 install --dry-run --table PATH [--user-dir PATH] 预览；使用附带表时省略 --table。该工具不访问网络、不上传资料。
2. Linux 所有 install / doctor 命令须加 --platform fcitx5 或 --platform ibus。正式执行 install，记录其返回的备份位置。它保留原有方案列表、无关补丁及兼容的手工短语，覆盖本方案的主题设置；不触碰其他方案的全局主题。
3. 若现有自定义文件会覆盖学习设置，或私人 op 绑定与日期模板冲突，工具会停下。此时检查冲突、备份后按用户意图合并，不要直接删掉其自定义文件。
4. macOS：用系统已安装鼠须管的 --reload 或菜单重新部署。
5. Windows：用小狼毫托盘「重新部署」，或先确认本机 WeaselDeployer.exe 的真实位置与 /deploy 用法再调用。不要硬编码某个版本的安装路径。
6. Linux：通过对应前端的 Rime 菜单部署；配置不会修改 Fcitx5／IBus 全局面板主题或全局字体。若需要 MiSans，在前端或桌面设置中配置；emoji 用系统字体回退。
7. 启用并选择「小鹤音形」。系统首次启用可能需要用户手动操作；不要声称已绕过系统设置。

## 4. 验收与交付

1. 执行 doctor；核对 build/loginput_xiaohe.schema.yaml 中 translator/enable_user_dict、enable_encoder、encode_commit_history 都为 false。各平台 menu/page_size 为 10，同时必须有 xiaohe_pager_keys 处理器和 xiaohe_pager_filter 过滤器；实际显示为首屏3项、后续10项。Windows／Linux 还需确认 xiaohe_pager/native_labels=true 且 menu/alternative_select_labels 为空列表；不要给共享配置动态设置标签。
2. 输入 nihcuijp，确认能组成「你好世界」；使用用户熟悉的至少三个固定形码核对候选原顺序。无表模式不得声称通过此项。
3. 输入 op：按当前本地时间显示五种格式；; 二选、' 三选；Tab 翻页到后两种日期。检查普通文本候选及标点。
4. 验证首屏三项无编号、后续每屏最多十项且显示 1—9、0，编号不进入提交文字；输入新编码回到首屏。Windows／Linux 编号应在候选文字前，分别检查两个窗口停在不同逻辑页时标签互不影响。所有平台使用键盘翻页；面板按钮和滚轮暂不支持逻辑页。Linux 外观取决于桌面面板。按系统实际明暗主题核对。macOS 外层系统阴影不属于可配置的主题阴影，不要承诺完全没有阴影。
5. 打开方案菜单，检查「简体／繁體」开关。默认简体，输入 hjyu 为「汉语」，切换后候选和提交为「漢語」；tf 为「頭髮」，favj 为「發展」。切换时当前页回到首屏；繁体候选仍保持3/10分页且无重复项。检查编译结果的 traditional/option_name=traditional、opencc_config=s2t.json，以及 engine/filters 中 simplifier@traditional 位于 uniquifier 和分页过滤器之前。
6. 检查「你好」「𥥈」「𣎑」及 `oh` 的「🔴」实际字形。emoji 应回退到 macOS 的 Apple Color Emoji 或 Windows 的 Segoe UI Emoji；字体由系统提供，不打包、不替换系统字体。字体缺字与码表缺少编码是不同问题；不能把“查不到形码”说成字体问题。
7. 通过可用的本机 Rime 引擎或原生输入测试，反复选择非首选，再检查排序和学习数据库行为。没有对应平台实机条件时，明示未验证，不能将静态配置检查当成实机验收。
8. 报告安装目录、完整/无表模式、备份位置、部署及验证结果、未完成项和回退命令。不要上传用户备份或词库。

## 5. 回退

用 manage.py restore --backup PATH，还原成功后重新部署。若安装后有新编辑，工具会保护文件而拒绝覆盖，请比较备份后人工合并。不要删除无关方案或全局学习数据。
