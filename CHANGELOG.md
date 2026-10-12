# Changelog

## 0.1.0-alpha.1

- Single-player quest window (F7 / world context menu), chapters, details and prerequisite states.
- Manual, inventory and skill objectives; periodic rechecks and manual refresh.
- Stable quest IDs and separate world / character completion records using native game saves.
- Up to three tracked quests; no notification sounds.
- Core, Starter Journal and Alpharius Rebuild distributed as separate local modules.
- Chinese/English UI; initial authored task content is Chinese.
- JSON-to-Lua build tool, structural validation, Lua 5.1 tests and publication allowlist audit.
- Local installer backs up configuration before enabling the new modules.

Known limits: no item rewards, network authority, graph editor, complete EPR or RV adapter. Normal game saving is required for persistence; forced termination may lose unsaved progress. Only carried inventory is checked. Conditions in separate quests can use the same held items because this release never consumes them.
