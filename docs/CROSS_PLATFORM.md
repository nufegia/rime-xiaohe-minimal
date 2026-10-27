# 跨平台 3/10 分页

1.2.0 的目标：首屏最多3项且无可见编号；后续每屏最多10项，前置编号1—9、0，并可按对应数字选择。所有平台使用同一份固定码表和切片算法。候选不足时显示实际数量。

## 实现与边界

原生 menu/page_size 固定为10。Lua 过滤器只向原生菜单提供当前逻辑页：第0页取 [0,3)，第n页取 [3+(n-1)*10, 3+n*10)。预取一项判断是否还有下一页。处理器拦截 Tab／Shift+Tab、Page Down／Page Up、=／- 和数字选词，修改会话属性后刷新组合。

鼠须管沿用已确认正常的 comment 前缀显示数字。小狼毫、Fcitx5、IBus 则读取 menu.select_keys：首屏是十个空格，后续是1234567890。这个字段来自每个 Schema 实例的 select_keys；不是修改共享的 ConfigData。不得改为动态设置 menu/alternative_select_labels：两个会话会共享这个列表，导致窗口间标签串页。平台补丁将显式标签设为空列表，使前端使用 select_keys。Lua 单独处理实际数字选择，候选文本及提交文本不加编号。

首屏空格标签可能保留占位宽度；Linux 最终排版由具体桌面面板决定。Linux 配置只提供输入逻辑，不覆盖面板主题或全局字体。数字、分号、单引号和空格都已通过真实 librime API 测试；使用者确认本次 Windows 小狼毫实机测试通过，候选字号为 14；字体覆盖及 emoji 回退尚未逐项记录，Linux 原生窗口外观尚未验证。

Rime 原生页号仍为0，原生菜单认为自己只有一页。滚轮或面板翻页按钮若直接调用 change_page，不会进入本方案的 Lua 逻辑，因而不支持。请用上述键盘翻页。鼠标直接点击当前候选仍使用真实的当前页索引，但没有做目标平台 UI 验收。

## 简体／繁體开关（1.3.0）

四种平台共用 switches/traditional 开关，默认简体。方案菜单通常由 Ctrl+` 打开，实际热键沿用现有全局配置；本项目不抢占额外快捷键。原生 simplifier@traditional 使用 OpenCC s2t.json，位于 uniquifier 和逻辑分页之前；转换提示设为 none。

整句候选在繁体模式保留 luna_pinyin 原有繁体，简体模式才执行原有 t2s 转换；固定表与手工短语由原生过滤器转换。原码表不改写。转换导致的一简多繁可以增加候选，转换后同字合并则减少候选。Lua 缓冲会使原生 uniquifier 暂时看不到尚未 yield 的候选，因此分页过滤器也在计算偏移前按候选文字去重，保持连续页。简繁状态参与页签名，切换后立即刷新到首屏。

不会转换已经上屏的文字。通用繁体不等同于台湾地区词语本地化；本方案没有自动启用 s2twp。转换使用当前候选的字词上下文，不能替代全文语义判断。1.3.1 移除了 traditional 的 reset: 0，并将 traditional 追加到全局 switcher/save_options（保留原列表），因此通过方案菜单选择后，切换方案、新输入会话以及重新启动引擎会恢复上次简繁状态；首次使用为简体。选项值由 Rime 写入 user.yaml，这属于运行状态而非配置备份，不应删除。

## 安装路径

| 前端 | 安装参数 | 默认目录 |
|---|---|---|
| macOS 鼠须管 | --platform macos（可自动识别） | ~/Library/Rime |
| Windows 小狼毫 | --platform windows（可自动识别） | %APPDATA%\Rime |
| Linux Fcitx5 | --platform fcitx5 | ${XDG_DATA_HOME:-~/.local/share}/fcitx5/rime |
| Linux IBus | --platform ibus | ~/.config/ibus/rime |

Linux 显式选择前端；不根据文件夹存在与否猜测正在使用哪一个。上游 IBus Rime 当前硬编码 HOME/.config，不能直接套用 XDG_CONFIG_HOME。用户自定义、沙盒发行版或旧版目录不同，请先确认并传 --user-dir PATH。

安装器保留原方案和学习数据库、生成可回退备份。安装后通过前端菜单重新部署，再用 doctor --platform 对应平台检查编译结果。不要用 Linux Python 自动修改 Windows 的输入法目录。

## 可重复的逻辑测试

先安装 requirements.txt。tests/engine_probe.cpp 需要 librime 的 rime_api.h、librime 和 librime-lua；实际链接路径随安装方式不同。macOS 上使用系统已安装鼠须管的库时，可按以下示例构建（RIME_HEADERS 指向含 rime_api.h 的开发头文件目录）：

```sh
c++ -O2 -std=c++17 -I"$RIME_HEADERS" tests/engine_probe.cpp \
  '/Library/Input Methods/Squirrel.app/Contents/Frameworks/librime.1.dylib' \
  '/Library/Input Methods/Squirrel.app/Contents/Frameworks/rime-plugins/librime-lua.dylib' \
  -Wl,-rpath,'/Library/Input Methods/Squirrel.app/Contents/Frameworks' \
  -Wl,-rpath,'/Library/Input Methods/Squirrel.app/Contents/Frameworks/rime-plugins' \
  -o /tmp/xiaohe-engine-probe
python tests/check_pager_engine.py --probe /tmp/xiaohe-engine-probe \
  --shared-data '/Library/Input Methods/Squirrel.app/Contents/SharedSupport' \
  --work-dir /tmp/xiaohe-engine-check-new
```

--work-dir 必须为空，防止污染既有文件。脚本通过安装器生成四种平台配置，并生成一个关闭分页的原方案基准；部署后运行全页顺序、所有 hs／kr 数字选择、边界、编辑、日期、emoji 和双会话隔离检查。h 仅用于退格后的首屏检查，不把探针截断的2000项结果称为全部候选。报告保存在指定目录的 report.json。本次逻辑结果见 [engine-regression-1.3.0.json](engine-regression-1.3.0.json)。

安装器检查：python -m unittest discover -s tests -v。CI 在 macOS、Windows、Ubuntu 执行安装器测试；当前不安装原生输入法，也不将引擎探针测试混称为三系统原生 UI 测试。

## 官方源码依据

- [librime 上下文导出](https://github.com/rime/librime/blob/master/src/rime_api_impl.h)：select_keys 取自 Schema；显式 alternative_select_labels 优先。
- [librime Schema](https://github.com/rime/librime/blob/master/src/rime/schema.h)：select_keys 是 Schema 实例字段。
- [小狼毫](https://github.com/rime/weasel/blob/master/RimeWithWeasel/RimeWithWeasel.cpp)：没有显式标签时使用 select_keys；label_format 使用 %s，空格不会生成数字或句点。
- [Fcitx5 候选列表](https://github.com/fcitx/fcitx5-rime/blob/master/src/rimecandidate.cpp)：优先显式标签，然后 select_keys，最后数字回退。
- [IBus 候选表](https://github.com/rime/ibus-rime/blob/master/rime_engine.c)：同样的标签回退次序。
- [IBus 用户目录](https://github.com/rime/ibus-rime/blob/master/rime_main.c) 与 [Fcitx5 数据目录](https://github.com/fcitx/fcitx5-rime/blob/master/src/rimeengine.cpp)。

以上源码检查结合共同引擎测试支持当前逻辑实现；目标机上的具体前端版本、桌面面板和字体仍需要实际使用时确认。
