# 开发与 CLI

本页面向手动运行、开发和打包。普通用户从[README](../../../README.md)进入，让Codex完成环境准备和报告生成；Agent的流程入口见[操作指南](agent-guide.md)。

## 环境

Python 3.11+、Node.js 20+，以及中文字体。Windows可使用已安装的雅黑/Arial；Linux/macOS建议Noto Sans CJK。安装依赖需联网，原表里程与本地素材齐备后可离线渲染。

以下命令均从仓库根目录执行：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r plugins/flight-atlas/requirements.txt
npm ci --prefix plugins/flight-atlas --no-audit --no-fund
```

macOS/Linux将`.venv/Scripts/python`换成`.venv/bin/python`。插件缓存不可写时使用可写工作副本，不安装到全局Python环境。

## 合成演示

```powershell
.venv/Scripts/python plugins/flight-atlas/scripts/generate_report.py --input plugins/flight-atlas/examples/sample.csv --config plugins/flight-atlas/examples/config.json --output reports/demo
```

样例全部为合成数据，配置为`diagnostic`，用于开发预览。它不代表真实航班或已补齐素材的正式报告。

## 真实报告

先由Agent完成选项、护照字段和必要资料/素材确认，存入私人配置。CSV为主输入，XLS仅辅助核对：

```powershell
.venv/Scripts/python plugins/flight-atlas/scripts/preflight_report.py --input /private/export.csv --config /private/confirmed-config.json --output /private/preflight-new.json
.venv/Scripts/python plugins/flight-atlas/scripts/generate_report.py --input /private/export.csv --config /private/confirmed-config.json --output /private/reports/new
```

输出两张PNG、两张SVG、统计/里程/时长/地图核验及素材署名JSON。原表不修改；新输出目录默认不覆盖已有报告。

详细参数见[字段与配置](../skills/flight-report/references/input-and-options.md)。常用项：

| 选项 | 含义 |
| --- | --- |
| `--distance-source export` | 采用主CSV公里值 |
| `--distance-source tpm` | 全部航段使用城市TPM |
| `--distance-source export-then-tpm` | 保留原值，仅空里程回退TPM |
| `--tpm-cache PATH` / `--online-tpm` | 有来源的缓存 / 经用户同意在线查询缺失城市对 |
| `--bar-min` / `--airport-bar-min` / `--airline-bar-min` | 共用或分别设置柱图最低次数 |
| `--route-min` | 单向常飞航线最低次数，往返分开 |
| `--include-repeated` / `--no-include-repeated` | 重复机体栏目 |
| `--include-retired` / `--no-include-retired` | 永久退出客运栏目 |
| `--svg-only` | 跳过最终PNG转换，地图仍需Node/ECharts |

默认时长策略是原表实际值优先、缺失时取同一行表定时长；不会在该策略下用当地时刻重算。正式报告需要已确认的共享主号、航司LOGO和相关照片；具体处理见[Agent指南](agent-guide.md)。

## 测试与打包

### 增量更新 CLI

成功生成后，报告目录中的 `flight-history.json` 保留源报告字段（未转换成TPM值），`report-config.json` 保留选项和已确认本地素材路径。新导出只需新增范围，按客户端当前日期运行：

```powershell
.venv/Scripts/python plugins/flight-atlas/scripts/make_increment_prompt.py --from 2026-10-01 --through 2026-10-31 --output /private/increment-prompt.txt
.venv/Scripts/python plugins/flight-atlas/scripts/merge_increment.py --history /private/reports/previous/flight-history.json --input /private/new-flights.csv --config /private/reports/previous/report-config.json --report-date 2026-10-05 --output /private/update-work
.venv/Scripts/python plugins/flight-atlas/scripts/preflight_report.py --input /private/update-work/flight-history.json --config /private/update-work/report-config.json --output /private/preflight-update.json
.venv/Scripts/python plugins/flight-atlas/scripts/generate_report.py --input /private/update-work/flight-history.json --config /private/update-work/report-config.json --output /private/reports/updated
```

冲突时合并命令退出2，只写 `increment-audit.json`，不会输出可采纳历史。用户确认后使用 `--resolutions` 在新目录重跑；决定结构见[增量流程](../skills/flight-report/references/incremental-update.md)。旧报告没有历史文件时，`--history` 可以指定上次完整CSV。它不从PNG或累计总数重建航段。

### 回归测试与发布包

README效果图由现有渲染器生成，演示构建脚本重新生成240条虚构记录，只可选参考输入表的加扰机型频率，不复制行程。中间CSV、配置和下载素材留在`.local/readme-demo`，公开目录仅存PNG及素材来源清单。更新示例：

```powershell
.venv/Scripts/python scripts/build_readme_demo.py --render
```

首次运行需要联网获取Commons素材；已缓存后无需重复下载。两张效果图许可与代码许可分开记录。

```powershell
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest tests -q
.venv/Scripts/python scripts/package_release.py
```

测试使用合成数据；私人回归留在`.local`。打包脚本使用白名单，排除私人数据、报告、依赖目录和工作簿，输出ZIP、SHA256及逐文件清单。它不执行上传或发布。

代码MIT；第三方图标、国旗、地图及教程截图见[素材说明](../ASSET_NOTICES.md)。内置28族飞机图标、三大联盟标志，运行时不需要生成飞机图标。国内图使用pyecharts几何，含台湾及南海附图；它不是带审图号标准地图，公开印刷另核验地图要求。
