require "ISUI/ISCollapsableWindow"
require "ISUI/ISScrollingListBox"
require "ISUI/ISRichTextPanel"
require "ISUI/ISComboBox"
require "KnoxQuest/Runtime"
local K = KnoxQuest
KnoxQuestWindow = ISCollapsableWindow:derive("KnoxQuestWindow")
local W = KnoxQuestWindow

local function tr(key) return getText("UI_KQ_"..key) end
local function safe(text) return tostring(text or ""):gsub("<","["):gsub(">","]") end
local function statusName(status) return tr("State_"..status) end
local function itemLabel(task)
    local names={}
    for _,fullType in ipairs(task.items) do names[#names+1]=getItemNameFromFullType(fullType) or fullType end
    return table.concat(names," / ").." x"..task.count
end

-- Kahlua strings use Java character indices. Explicit measured line breaks
-- keep CJK paragraphs inside the detail pane even without spaces between words.
local function wrapped(value,width)
    local text=safe(value)
    local lines,line={},""
    for index=1,#text do
        local char=text:sub(index,index)
        if char=="\n" then
            lines[#lines+1]=line;line=""
        elseif line~="" and getTextManager():MeasureStringX(UIFont.Medium,line..char)>width then
            lines[#lines+1]=line;line=char
        else line=line..char end
    end
    lines[#lines+1]=line
    return table.concat(lines," <LINE> ")
end

local function drawRow(list,y,item,alt)
    if list.selected==item.index then list:drawRect(1,y,list.width-2,item.height,0.85,0.15,0.27,0.25)
    elseif alt then list:drawRect(1,y,list.width-2,item.height,0.30,0.13,0.16,0.18) end
    list:drawRectBorder(0,y,list.width,item.height,0.10,0.6,0.7,0.7)
    list:drawText(item.text,12,y+8,0.88,0.91,0.88,1,UIFont.Medium)
    return y+item.height
end

function W:createChildren()
    ISCollapsableWindow.createChildren(self)
    local margin, top = 18, self:titleBarHeight()+16
    self.packCombo=ISComboBox:new(margin,top,self.width-2*margin,32,self,W.onPack)
    self.packCombo:initialise()
    self:addChild(self.packCombo)
    for _, id in ipairs(K.packOrder) do self.packCombo:addOption(K.packs[id].title) end
    local y=top+65
    local listHeight=self.height-y-66
    local chapterWidth=math.floor(self.width*0.22)
    local questWidth=math.floor(self.width*0.29)
    self.chapters=ISScrollingListBox:new(margin,y,chapterWidth,listHeight)
    self.chapters:initialise();self.chapters:instantiate()
    self.chapters:setFont(UIFont.Medium,18);self.chapters.drawBorder=true
    self.chapters.doDrawItem=drawRow
    self.chapters:setOnMouseDownFunction(self,W.onChapter)
    self:addChild(self.chapters)
    self.quests=ISScrollingListBox:new(margin+chapterWidth+12,y,questWidth,listHeight)
    self.quests:initialise();self.quests:instantiate()
    self.quests:setFont(UIFont.Medium,18);self.quests.drawBorder=true
    self.quests.doDrawItem=drawRow
    self.quests:setOnMouseDownFunction(self,W.onQuest)
    self:addChild(self.quests)
    local detailX=self.quests:getRight()+16
    self.detail=ISRichTextPanel:new(detailX,y,self.width-detailX-margin,listHeight-98)
    self.detail:initialise();self.detail:instantiate()
    self.detail.autosetheight=false
    self.detail.defaultFont=UIFont.Medium
    self.detail.marginLeft=12;self.detail.marginRight=12
    self.detail.background=true
    self.detail.backgroundColor={r=0.065,g=0.085,b=0.09,a=0.95}
    self.detail:addScrollBars()
    self:addChild(self.detail)
    self.confirmButton=ISButton:new(detailX,y+listHeight-86,self.detail.width,34,tr("Confirm"),self,W.onConfirm)
    self.confirmButton:initialise();self:addChild(self.confirmButton)
    self.trackButton=ISButton:new(detailX,y+listHeight-44,math.floor(self.detail.width*0.55)-4,34,tr("Track"),self,W.onTrack)
    self.trackButton:initialise();self:addChild(self.trackButton)
    self.refreshButton=ISButton:new(self.trackButton:getRight()+8,y+listHeight-44,self.detail.width-self.trackButton.width-8,34,tr("Recheck"),self,W.onRefresh)
    self.refreshButton:initialise();self:addChild(self.refreshButton)
    self.listTop=y
    self:onPack()
end

function W:onPack()
    self.packId=K.packOrder[self.packCombo.selected]
    self.chapters:clear()
    self.selectedQuest=nil
    local pack=K.packs[self.packId]
    if not pack then
        self.quests:clear()
        self.detail:setText(safe(tr("NoPacks")));self.detail:paginate()
        self.confirmButton:setEnable(false);self.trackButton:setEnable(false)
        return
    end
    for _, chapter in ipairs(pack.chapters) do self.chapters:addItem(chapter.title,chapter) end
    self.chapters.selected=1
    self:onChapter(pack.chapters[1])
end

function W:onChapter(chapter)
    if not chapter then return end
    self.chapterId=chapter.id
    self.quests:clear()
    for _, quest in ipairs(K.packs[self.packId].quests) do
        if quest.chapterId==chapter.id then self.quests:addItem(quest.title,quest) end
    end
    self.quests.selected=1
    local row=self.quests.items[1]
    self.selectedQuest=row and row.item.id or nil
    self:sync()
end

function W:onQuest(quest)
    self.selectedQuest=quest.id
    self:sync()
end

function W:sync()
    local context=K.getContext()
    if not context then
        self.detail:setText(safe(K.runtime.error or tr("NotReady")));self.detail:paginate()
        self.confirmButton:setEnable(false);self.trackButton:setEnable(false)
        return
    end
    self.revision=K.runtime.revision
    for _, row in ipairs(self.quests.items) do
        local status=K.inspect(row.item.id,context).status
        row.text=(status=="completed" and "[+] " or status=="locked" and "[-] " or "[ ] ")..row.item.title
    end
    local quest=K.quests[self.selectedQuest]
    if not quest then return end
    local result=K.inspect(quest.id,context)
    local function text(value) return wrapped(value,self.detail.width-44) end
    local parts={"<H2> "..text(quest.title),"<LINE> <TEXT> "..text(statusName(result.status)),"<LINE> "..text(quest.description),"<LINE> <H2> "..tr("Objectives")}
    local canConfirm=false
    for index, task in ipairs(quest.tasks) do
        local check=result.tasks[index] or {status="met"}
        local label=task.prompt or (task.type=="skill" and (tr("Skill_"..task.skill).." "..task.level)) or (task.type=="item" and itemLabel(task)) or task.capability
        local count=check.current and (" ("..check.current.."/"..check.target..")") or ""
        table.insert(parts,"<LINE> <TEXT> "..text((check.status=="met" and "[+] " or "[ ] ")..label..count))
        if task.type=="manual" and check.status~="met" then canConfirm=true end
        if check.status=="unavailable" or check.status=="error" then
            table.insert(parts,"<LINE> "..text(statusName(check.status)..": "..tostring(check.detail)))
        end
    end
    if #quest.dependsOn>0 then
        table.insert(parts,"<LINE> <H2> "..tr("Prerequisites").." ("..quest.dependencyMode..")")
        for _, id in ipairs(quest.dependsOn) do
            table.insert(parts,"<LINE> <TEXT> "..(K.isCompleted(id,context) and "[+] " or "[ ] ")..safe(K.quests[id].title))
        end
    end
    table.insert(parts,"<LINE> <TEXT> "..text(tr("Scope_"..quest.scope)))
    table.insert(parts,"<LINE> "..text(tr("NoRewards")))
    if result.status=="unavailable" then table.insert(parts,"<LINE> "..text(tr("MissingAdapter"))) end
    local body=table.concat(parts," ")
    if body~=self.lastBody then
        local scroll=self.detail:getYScroll()
        self.detail:setText(body);self.detail:paginate()
        if self.bodyQuest==quest.id then self.detail:setYScroll(scroll) else self.detail:setYScroll(0) end
        self.lastBody,self.bodyQuest=body,quest.id
    end
    self.confirmButton:setEnable(canConfirm and result.status~="locked" and result.status~="completed")
    self.confirmButton.tooltip=tr("ConfirmHelp")
    local tracked=false
    for _, id in ipairs(context.character.tracked) do if id==quest.id then tracked=true end end
    self.trackButton:setTitle(tr(tracked and "Untrack" or "Track"))
    self.trackButton:setEnable(tracked or #context.character.tracked<3)
end

function W:onConfirm() K.confirmQuest(self.selectedQuest);self:sync() end
function W:onTrack() K.trackQuest(self.selectedQuest);self:sync() end
function W:onRefresh() K.refresh();self:sync() end

function W:prerender()
    ISCollapsableWindow.prerender(self)
    if self.revision~=K.runtime.revision then self:sync() end
    self:drawText(tr("Chapters"),18,self.listTop-26,0.55,0.78,0.69,1,UIFont.Small)
    self:drawText(tr("Quests"),self.quests.x,self.listTop-26,0.55,0.78,0.69,1,UIFont.Small)
    self:drawText(tr("Details"),self.detail.x,self.listTop-26,0.55,0.78,0.69,1,UIFont.Small)
    self:drawText(tr("SaveHelp"),18,self.height-48,0.66,0.71,0.73,1,UIFont.Small)
    self:drawText("Knox Quest "..K.version.."  |  F7",18,self.height-27,0.43,0.56,0.56,1,UIFont.Small)
end

function W:new()
    local sw,sh=getCore():getScreenWidth(),getCore():getScreenHeight()
    local width=math.floor(math.min(sw-40,math.max(1040,math.min(1600,sw*0.72))))
    local height=math.floor(math.min(sh-60,math.max(640,math.min(1000,sh*0.8))))
    local o=ISCollapsableWindow.new(self,(sw-width)/2,(sh-height)/2,width,height)
    o.title=tr("Title");o.resizable=false
    o.backgroundColor={r=0.035,g=0.055,b=0.065,a=0.98}
    o.borderColor={r=0.28,g=0.45,b=0.40,a=1}
    o.moveWithMouse=true
    return o
end

function K.openWindow()
    if isClient() or isServer() or not getPlayer() then return end
    if K.window and K.window:getIsVisible() then K.window:close();return end
    if K.window then K.window:removeFromUIManager() end
    K.window=W:new();K.window:initialise();K.window:addToUIManager();K.window:setVisible(true)
    K.window:bringToTop()
end

Events.OnKeyPressed.Add(function(key)
    if key==Keyboard.KEY_F7 then K.openWindow() end
end)
Events.OnFillWorldObjectContextMenu.Add(function(player,context,worldObjects,test)
    if test or player~=0 or not K.runtime.ready then return end
    context:addOption(tr("Title"),nil,function() K.openWindow() end)
end)

-- Tiny text-only tracker; no external textures or UI assets.
KnoxQuestTracker=ISPanel:derive("KnoxQuestTracker")
function KnoxQuestTracker:render()
    if K.window and K.window:getIsVisible() then return end
    local context=K.getContext()
    if not context or #context.character.tracked==0 then return end
    local fh=getTextManager():getFontHeight(UIFont.Small)
    self:drawRect(0,0,self.width,30+#context.character.tracked*(fh+8),0.80,0.025,0.05,0.055)
    self:drawText(tr("Tracked").."  [F7]",10,6,0.55,0.85,0.71,1,UIFont.Small)
    for index,id in ipairs(context.character.tracked) do
        local quest=K.quests[id]
        local label=quest and quest.title or id
        local done=quest and K.isCompleted(id,context)
        self:drawText((done and "[+] " or "[ ] ")..label,10,26+(index-1)*(fh+8),0.88,0.91,0.88,1,UIFont.Small)
    end
end
Events.OnGameStart.Add(function()
    if not K.runtime.ready then return end
    if K.tracker then K.tracker:removeFromUIManager() end
    K.tracker=KnoxQuestTracker:new(getCore():getScreenWidth()-390,math.min(420,getCore():getScreenHeight()-200),360,180)
    K.tracker:initialise();K.tracker.background=false;K.tracker:addToUIManager()
end)
