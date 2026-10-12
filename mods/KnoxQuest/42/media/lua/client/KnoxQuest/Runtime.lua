require "KnoxQuest/Core"
local K = KnoxQuest
K.runtime = K.runtime or {ready=false, revision=0}

function K.text(chinese, english)
    return getText("UI_KQ_Language")=="zh" and chinese or english
end

function K.getContext()
    return K.runtime.context
end

local function inventoryCounts(container, counts, seen)
    if not container or seen[container] then return end
    seen[container] = true
    local items = container:getItems()
    for index=0, items:size()-1 do
        local item = items:get(index)
        local fullType = item:getFullType()
        counts[fullType] = (counts[fullType] or 0) + 1
        if instanceof(item, "InventoryContainer") then inventoryCounts(item:getInventory(),counts,seen) end
    end
end

K.detectors.item = function(task, context)
    context.inventoryCounts = context.inventoryCounts or {}
    if not context.inventoryScanned then
        inventoryCounts(context.player:getInventory(),context.inventoryCounts,{})
        context.inventoryScanned = true
    end
    local count = 0
    for _, fullType in ipairs(task.items) do count=count+(context.inventoryCounts[fullType] or 0) end
    return {status=count>=task.count and "met" or "unmet", current=count, target=task.count}
end

K.detectors.skill = function(task, context)
    local perk = task.skill=="electrical" and Perks.Electricity or task.skill=="metalworking" and Perks.MetalWelding or nil
    if not perk then return {status="unavailable",detail=task.skill} end
    local level = context.player:getPerkLevel(perk)
    return {status=level>=task.level and "met" or "unmet",current=level,target=task.level}
end

-- Mutations already live in native ModData tables, serialized by normal game saves.
-- ModData has no public save() method in B42.21. Do not promise crash durability.
function K.flush()
    if not K.runtime.ready then return false end
    K.runtime.dirty = true
    return true
end

function K.refresh()
    local context = K.getContext()
    if not context then return end
    context.inventoryScanned, context.inventoryCounts = false, nil
    local changed, err = K.evaluate(context)
    if err then K.runtime.error=err; return end
    if changed then K.flush() end
    K.runtime.revision = K.runtime.revision+1
end

function K.confirmQuest(id)
    local context = K.getContext()
    if not context then return false end
    local changed = K.confirm(id,context)
    if changed then K.flush() end
    K.refresh()
    return changed
end

function K.trackQuest(id)
    local context = K.getContext()
    if not context then return false end
    local changed = K.toggleTracked(id,context)
    if changed then K.flush(); K.runtime.revision=K.runtime.revision+1 end
    return changed
end

function K.start()
    K.runtime.ready, K.runtime.context = false, nil
    if isClient() or isServer() then
        print("[KnoxQuest] alpha.1 supports single-player only")
        return
    end
    local player = getPlayer()
    if not player then return end
    local store = ModData.getOrCreate("KnoxQuest")
    local empty=true
    for _ in pairs(store) do empty=false;break end
    if empty then
        store.saveVersion, store.world, store.characters = 1, K.newState(), {}
    end
    if store.saveVersion~=1 or not K.validateState(store.world) or type(store.characters)~="table" then
        K.runtime.error="Unsupported or damaged save data; preserved without overwrite"
        print("[KnoxQuest] "..K.runtime.error)
        return
    end
    local playerData = player:getModData()
    if playerData.KnoxQuestCharacterId==nil then
        playerData.KnoxQuestCharacterId=tostring(getTimestampMs()).."-"..tostring(ZombRand(100000000))
    end
    local id = playerData.KnoxQuestCharacterId
    if store.characters[id]==nil then store.characters[id]=K.newState() end
    if not K.validateState(store.characters[id]) then
        K.runtime.error="Unsupported character progress; preserved without overwrite"
        return
    end
    local count=0
    for _ in pairs(K.quests) do count=count+1 end
    K.runtime.context={player=player,world=store.world,character=store.characters[id],questCount=count}
    K.runtime.ready, K.runtime.error = true, nil
    K.refresh()
    print("[KnoxQuest] Ready "..K.version.." packs="..#K.packOrder.." quests="..count)
end

Events.OnGameStart.Add(K.start)
Events.OnCreatePlayer.Add(function(index, player)
    if index==0 and K.runtime.ready and K.runtime.context.player~=player then K.start() end
end)
Events.OnPlayerUpdate.Add(function(player)
    if not K.runtime.ready or player~=getPlayer() then return end
    local now=getTimestampMs()
    if now-(K.runtime.lastPoll or 0)<1500 then return end
    K.runtime.lastPoll=now
    K.refresh()
end)
return K
