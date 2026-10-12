# 任务数据约定 v1（草案）

作者格式采用 JSON，通过 `tools/build_content.py` 生成 Lua 定义，随对应内容模组加载。游戏无需 Python。schemaVersion 仍为 1，新增兼容的 item 类型；旧的任务 ID 保持不变。

## 包字段

`schemaVersion` 固定为整数 1；`packId` 为小写字母开头的命名空间；`packVersion` 为三段数字版本；`title` 为非空说明；`chapters` 和 `quests` 为非空数组。

章节：`id`、`title`。任务：`id`、`chapterId`、`title`、`description`、`scope`、`dependsOn`、`dependencyMode`、`tasks`、`rewards`。

章节和任务 ID 必须以 `packId:` 开头。任务依赖目前仅支持同包任务；暂不承诺跨包依赖。依赖图必须无环，不能指向自身、重复引用或引用不存在的任务。

`scope` 是 `world` 或 `character`。`dependencyMode` 是 `all` 或 `any`；空依赖只允许 `all`。一个任务的所有 `tasks` 条件都必须满足。条件 ID 在任务内唯一且发布后稳定。

## 条件类型

| 类型 | 字段 | 含义 |
|---|---|---|
| `manual` | `id`, `type`, `prompt` | 玩家主动确认，必须在 UI 标注 |
| `skill` | `id`, `type`, `skill`, `level` | 草案支持 `electrical` / `metalworking`，等级 1–10；游戏名称映射待验证 |
| `item` | `id`, `type`, `items`, `count` | 按 fullType 列出可替代物品，汇总角色背包及随身容器数量；只检测、不扣除 |
| `adapter` | `id`, `type`, `capability`, `params` | 请求可选适配器。缺失能力返回 unavailable，绝不自动完成 |

`capability` 使用小写点分名称。`params` 是对象，其业务语义由未来对应适配器校验。离线校验器只验证结构、关系及当前约定，不能验证设施是否存在、技能 API 是否正确或模组兼容。

物品计数每件物品记 1，不按液体体积或剩余耐久计数。多个独立任务可由同一件物品满足；不支持消耗式交付。位置和事件条件后续扩展，校验器拒绝未知类型。

## 奖励

alpha.1 只接受空数组 `rewards: []`，本次范围为界面、判定与保存。奖励契约、账本和中断恢复在后续版本实现后再扩展格式。

## 版本规则

不兼容的数据变更提升 schemaVersion 并提供迁移。内容增补提升 packVersion。已经发布的 ID 不能复用。修改目标含义时必须定义旧玩家如何补认，不能默认重置。

格式目前使用内联文案；实现阶段统一提取为 PZ 翻译键，并保留稳定 ID。中文和英文文本不能用作进度键。
