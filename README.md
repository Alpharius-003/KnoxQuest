# Knox Quest（暂定名）

A data-driven, single-player quest journal for Project Zomboid.

面向《僵尸毁灭工程》的通用任务框架。首个配套任务包为 **《诺克斯重建手册》 / Alpharius Rebuild**，服务 Alpharius 单人整合包。

## 当前状态

**0.1.0-alpha.1：首个单人测试版。** 已实现游戏内章节列表、任务详情、前置关系、手动确认、背包物品与技能检测、最多三个任务追踪，以及游戏原生 ModData 进度保存。可选适配器缺失会明确显示不可用。

当前没有物资奖励、可视化任务树、任务编辑器或联机支持。首批内容为中文；通用界面提供简体中文和英文。游戏验证情况见 [测试记录](docs/TESTING.md)。

开发与测试目标为 **Build 42.21.x 单人环境**，不承诺整个 B42 系列兼容。

**Viewpoint 已知问题：** 测试配置直接进入 3D 后，窗口背景可能遮住文字。测试中切到游戏原生俯视视角，再切回 3D 可恢复显示；也可在原生视角查看任务。此兼容问题尚未根治，模组不会自动更改你的视角或图形设置。关闭汉化没有消除该现象。

## 安装与游玩

1. 退出游戏，将 `mods/KnoxQuest` 放到游戏用户目录的 `mods` 中。
2. 同时安装并启用 `KnoxQuestDemo`（5 个教学任务）或 `KnoxQuestAlpharius`（14 个重建任务）。两者可以同时启用。
3. 旧档需要在该存档的模组列表中启用 Core 与内容包，随后重新进入游戏。
4. 按 **F7** 或在世界右键菜单选择 **Knox Quest** 打开任务手册。
5. 手动目标点击确认；物品与技能通常在约 1.5 秒内更新，也可点击“重新检测”。物品只检查角色背包及随身容器，不消耗物品。
6. 正常保存并退出后，任务完成与追踪记录随存档保留。强制结束进程时，尚未保存的游戏和任务进度可能丢失。

也可使用带配置备份的安装工具（在项目目录运行；按实际目录替换占位路径）：

```sh
python tools/install_local.py --profile "YOUR_PZ_PROFILE" --save "Sandbox/YOUR_SAVE" --dry-run
python tools/install_local.py --profile "YOUR_PZ_PROFILE" --save "Sandbox/YOUR_SAVE"
```

不指定 `--save` 时只更新新游戏的默认模组列表。安装器默认启用 Core 和 Alpharius 内容包，`--demo` 额外启用教学包。配置和已有的本项目模组会先备份到该配置目录的 `KnoxQuest-backups`；地图与角色文件不作修改。

## 项目边界

- **Knox Quest Core**：章节、任务关系、条件判定、进度、界面、翻译和内容注册。
- **Vanilla Demo**：不依赖第三方模组的最小教学任务包，也是核心回归测试入口。
- **Alpharius Rebuild**：据点、运输、房车远征、修复电网、恢复供水与长期经营。
- **可选适配器**：连接 EPR、房车及其他模组。第三方依赖失效时显示原因，不伪造任务完成。

核心不会硬编码西西小屋、某座电站、整合包专用沙盒参数或光影组件。已安装内容通过任务包与适配器接入。

## 本地检查

需要 Python 3.10 或更新版本；内容构建与校验无额外依赖，Lua 测试使用 lupa。在本项目目录运行：

```sh
python -m pip install -r requirements-dev.txt
python tools/validate_content.py
python tools/build_content.py --check
python -m unittest discover -s tests -v
```

编辑 JSON 后运行 `python tools/build_content.py` 生成随模组分发的 Lua 任务数据。游戏端不需要 Python，也不直接读取任务 JSON。界面调用游戏现有 UI 与纹理 API，不分发游戏资源。

## 阅读顺序

1. [产品与架构](docs/ARCHITECTURE.md)
2. [任务数据约定](docs/CONTENT_FORMAT.md)
3. [版本路线与发布验收](docs/ROADMAP.md)
4. [整合包任务设计](docs/ALPHARIUS_REBUILD.md)
5. [贡献指南](CONTRIBUTING.md)

## 开源与发布

本仓库新增的原创代码、文档和任务示例采用 [MIT](LICENSE)。仓库不分发游戏文件、第三方模组、光影、字体或整合包存档；它们的名称仅用于兼容描述，授权由原作者决定。

源码仓库：[Alpharius-003/KnoxQuest](https://github.com/Alpharius-003/KnoxQuest)。工坊发布尚未进行。仓库根目录仅为 KnoxQuest 独立项目目录，发布前使用 `python tools/audit_repository.py` 检查 Git 索引的文件白名单、文件类型和敏感路径。

任务交互参考 [FTB Quests](https://github.com/FTBTeam/FTB-Quests) 的章节、依赖与奖励概念；独立编写实现及素材，不复制其代码或资源。
