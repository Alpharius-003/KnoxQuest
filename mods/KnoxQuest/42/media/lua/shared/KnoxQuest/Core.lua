-- Original Knox Quest code. No game API dependencies in this module.
KnoxQuest = KnoxQuest or {}
local K = KnoxQuest
K.version = "0.1.0-alpha.1"
K.packs = K.packs or {}
K.packOrder = K.packOrder or {}
K.quests = K.quests or {}
K.detectors = K.detectors or {}

function K.newState()
    return {saveVersion=1, completed={}, manual={}, tracked={}}
end

function K.validateState(state)
    if type(state) ~= "table" or state.saveVersion ~= 1 then return false end
    return type(state.completed)=="table" and type(state.manual)=="table" and type(state.tracked)=="table"
end

function K.registerPack(pack)
    assert(type(pack)=="table" and pack.schemaVersion==1, "Unsupported quest schema")
    assert(type(pack.packId)=="string" and not K.packs[pack.packId], "Duplicate or invalid pack id")
    local ids, chapters = {}, {}
    for _, chapter in ipairs(pack.chapters) do
        assert(type(chapter.id)=="string" and not chapters[chapter.id], "Invalid chapter id")
        chapters[chapter.id] = true
    end
    for _, quest in ipairs(pack.quests) do
        assert(type(quest.id)=="string" and not ids[quest.id] and not K.quests[quest.id], "Duplicate quest id")
        assert(chapters[quest.chapterId], "Unknown chapter")
        assert(quest.scope=="world" or quest.scope=="character", "Unknown scope")
        assert(quest.dependencyMode=="all" or quest.dependencyMode=="any", "Unknown dependency mode")
        assert(type(quest.dependsOn)=="table" and type(quest.tasks)=="table" and #quest.tasks>0, "Invalid quest tasks")
        assert(type(quest.rewards)=="table" and #quest.rewards==0, "Rewards are not supported in alpha.1")
        local taskIds = {}
        for _, task in ipairs(quest.tasks) do
            assert(type(task.id)=="string" and not taskIds[task.id], "Duplicate task id")
            assert(task.type=="manual" or task.type=="item" or task.type=="skill" or task.type=="adapter", "Unknown task type")
            taskIds[task.id] = true
        end
        ids[quest.id] = quest
    end
    local visiting, visited = {}, {}
    local function visit(id)
        assert(ids[id], "Missing same-pack dependency")
        assert(not visiting[id], "Cyclic quest dependency")
        if visited[id] then return end
        visiting[id] = true
        for _, dep in ipairs(ids[id].dependsOn) do visit(dep) end
        visiting[id], visited[id] = nil, true
    end
    for id in pairs(ids) do visit(id) end
    K.packs[pack.packId] = pack
    table.insert(K.packOrder, pack.packId)
    for id, quest in pairs(ids) do
        quest.packId = pack.packId
        K.quests[id] = quest
    end
end

function K.stateFor(quest, context)
    if quest.scope == "world" then return context.world end
    return context.character
end

function K.isCompleted(id, context)
    local quest = K.quests[id]
    return quest ~= nil and K.stateFor(quest, context).completed[id] == true
end

function K.isUnlocked(quest, context)
    if #quest.dependsOn==0 then return quest.dependencyMode=="all" end
    local count = 0
    for _, id in ipairs(quest.dependsOn) do
        if K.isCompleted(id, context) then count = count + 1 end
    end
    if quest.dependencyMode=="any" then return count>0 end
    return count==#quest.dependsOn
end

function K.checkTask(quest, task, context)
    if task.type=="manual" then
        local confirmed = K.stateFor(quest, context).manual[quest.id]
        return {status=(confirmed and confirmed[task.id]==true) and "met" or "unmet"}
    end
    local key = task.type=="adapter" and task.capability or task.type
    local detector = K.detectors[key]
    if not detector then return {status="unavailable", detail=key} end
    local ok, result = pcall(detector, task, context)
    if not ok then return {status="error", detail=tostring(result)} end
    if type(result)~="table" or (result.status~="met" and result.status~="unmet" and result.status~="unavailable" and result.status~="error") then
        return {status="error", detail="Invalid detector result: "..key}
    end
    return result
end

function K.inspect(id, context)
    local quest = K.quests[id]
    if not quest then return {status="unavailable", tasks={}} end
    if K.isCompleted(id, context) then return {status="completed", tasks={}} end
    local results, status, met = {}, "available", 0
    for _, task in ipairs(quest.tasks) do
        local result = K.checkTask(quest, task, context)
        table.insert(results, result)
        if result.status=="met" then met=met+1 end
        if result.status=="unavailable" and status~="error" then status="unavailable" end
        if result.status=="error" then status="error" end
    end
    if not K.isUnlocked(quest, context) then status="locked" end
    return {status=status, tasks=results, met=met, total=#quest.tasks}
end

function K.evaluate(context)
    if not K.validateState(context.world) or not K.validateState(context.character) then
        return false, "Unsupported or damaged progress format"
    end
    local changed = false
    -- Bounded fixed point allows out-of-order definitions and retroactive facts.
    for _=1, context.questCount or 1000 do
        local passChanged = false
        for _, packId in ipairs(K.packOrder) do
            for _, quest in ipairs(K.packs[packId].quests) do
                if not K.isCompleted(quest.id, context) and K.isUnlocked(quest, context) then
                    local result = K.inspect(quest.id, context)
                    if result.status=="available" and result.met==result.total then
                        K.stateFor(quest, context).completed[quest.id] = true
                        changed, passChanged = true, true
                    end
                end
            end
        end
        if not passChanged then break end
    end
    return changed
end

function K.confirm(id, context)
    if not K.validateState(context.world) or not K.validateState(context.character) then return false end
    local quest = K.quests[id]
    if not quest or K.isCompleted(id, context) or not K.isUnlocked(quest, context) then return false end
    local state, changed = K.stateFor(quest, context), false
    for _, task in ipairs(quest.tasks) do
        if task.type=="manual" then
            state.manual[id] = state.manual[id] or {}
            if not state.manual[id][task.id] then
                state.manual[id][task.id], changed = true, true
            end
        end
    end
    K.evaluate(context)
    return changed
end

function K.toggleTracked(id, context)
    if not K.validateState(context.world) or not K.validateState(context.character) then return false end
    if not K.quests[id] then return false end
    local tracked = context.character.tracked
    for index, value in ipairs(tracked) do
        if value==id then table.remove(tracked,index); return true end
    end
    if #tracked>=3 then return false end
    table.insert(tracked,id)
    return true
end

return K
