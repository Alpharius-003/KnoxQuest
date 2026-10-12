"""Run the actual shipped core with Lua 5.1, not a Python reimplementation."""
from pathlib import Path
import json
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "mods/KnoxQuest/42/media/lua/shared"


class LuaCoreTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().sourcePath = SHARED.as_posix()
        self.lua.execute('package.path=sourcePath.."/?.lua;"..package.path; require "KnoxQuest/Core"')
        for name in ("KnoxQuestDemo", "KnoxQuestAlpharius"):
            self.lua.execute((ROOT / f"mods/{name}/42/media/lua/shared/{name}_Content.lua").read_text(encoding="utf8"))
        self.lua.execute('K=KnoxQuest; c={world=K.newState(),character=K.newState(),questCount=100}')

    def run_lua(self, source):
        self.lua.execute(source)

    def test_generated_text_survives_byte_based_lexer(self):
        for name, filename in (("KnoxQuestDemo", "vanilla-demo"), ("KnoxQuestAlpharius", "alpharius-rebuild")):
            source = (ROOT / f"mods/{name}/42/media/lua/shared/{name}_Content.lua").read_text(encoding="ascii")
            self.assertNotIn("\x00", source)
            pack = json.loads((ROOT / f"content/{filename}.json").read_text(encoding="utf8"))
            loaded = self.lua.globals().KnoxQuest.packs[pack["packId"]]
            self.assertEqual(pack["title"], loaded.title)
            for index, quest in enumerate(pack["quests"], 1):
                self.assertEqual(quest["title"], loaded.quests[index].title)
                self.assertEqual(quest["description"], loaded.quests[index].description)

    def test_manual_completion_and_gating(self):
        self.run_lua('''
            assert(not K.confirm("vanilla_demo:shelter",c))
            assert(K.confirm("vanilla_demo:welcome",c))
            assert(K.isCompleted("vanilla_demo:welcome",c))
            assert(not K.confirm("vanilla_demo:welcome",c))
            assert(K.inspect("vanilla_demo:basic_tools",c).status=="unavailable")
        ''')

    def test_missing_adapter_never_completes(self):
        self.run_lua('''
            c.character.completed["alpharius_rebuild:power_skills"]=true
            K.evaluate(c)
            assert(K.inspect("alpharius_rebuild:power_plant",c).status=="unavailable")
            assert(not K.isCompleted("alpharius_rebuild:power_plant",c))
        ''')

    def test_detector_failure_isolated(self):
        self.run_lua('''
            K.confirm("vanilla_demo:welcome",c)
            K.detectors.item=function() error("test failure") end
            K.evaluate(c)
            assert(K.inspect("vanilla_demo:basic_tools",c).status=="error")
            assert(not K.isCompleted("vanilla_demo:basic_tools",c))
            K.detectors.item=function() return true end
            assert(K.inspect("vanilla_demo:basic_tools",c).status=="error")
        ''')

    def test_retroactive_detection_and_sticky_completion(self):
        self.run_lua('''
            K.detectors.item=function() return {status="met"} end
            K.evaluate(c)
            assert(not K.isCompleted("vanilla_demo:basic_tools",c))
            K.confirm("vanilla_demo:welcome",c)
            assert(K.isCompleted("vanilla_demo:basic_tools",c))
            assert(K.isCompleted("vanilla_demo:first_aid",c))
            K.detectors.item=function() return {status="unmet"} end
            K.evaluate(c)
            assert(K.isCompleted("vanilla_demo:basic_tools",c))
        ''')

    def test_world_and_character_scopes(self):
        self.run_lua('''
            K.confirm("alpharius_rebuild:welcome",c)
            K.confirm("vanilla_demo:welcome",c)
            local nextCharacter={world=c.world,character=K.newState()}
            assert(K.isCompleted("alpharius_rebuild:welcome",nextCharacter))
            assert(not K.isCompleted("vanilla_demo:welcome",nextCharacter))
        ''')

    def test_saved_records_restore_without_replaying(self):
        self.run_lua('''
            K.confirm("alpharius_rebuild:welcome",c)
            K.toggleTracked("alpharius_rebuild:shelter",c)
            local function clone(value)
                if type(value)~="table" then return value end
                local result={};for k,v in pairs(value) do result[k]=clone(v) end;return result
            end
            local restored={world=clone(c.world),character=clone(c.character)}
            assert(K.isCompleted("alpharius_rebuild:welcome",restored))
            assert(restored.character.tracked[1]=="alpharius_rebuild:shelter")
            assert(not K.confirm("alpharius_rebuild:welcome",restored))
        ''')

    def test_tracking_limit_and_toggle(self):
        self.run_lua('''
            assert(K.toggleTracked("vanilla_demo:welcome",c))
            assert(K.toggleTracked("vanilla_demo:basic_tools",c))
            assert(K.toggleTracked("vanilla_demo:first_aid",c))
            assert(not K.toggleTracked("vanilla_demo:shelter",c))
            assert(K.toggleTracked("vanilla_demo:welcome",c))
            assert(#c.character.tracked==2)
        ''')

    def test_future_save_not_overwritten(self):
        self.run_lua('''
            c.world.saveVersion=2
            local changed,err=K.evaluate(c)
            assert(not changed and err)
            assert(c.world.saveVersion==2)
            assert(next(c.world.completed)==nil)
        ''')

    def test_cycle_registration_is_atomic(self):
        self.run_lua('''
            local pack={schemaVersion=1,packId="bad",chapters={{id="bad:c"}},quests={}}
            pack.quests[1]={id="bad:q",chapterId="bad:c",scope="world",dependencyMode="all",dependsOn={"bad:q"},tasks={{id="m",type="manual"}},rewards={}}
            assert(not pcall(K.registerPack,pack))
            assert(K.packs.bad==nil and K.quests["bad:q"]==nil)
        ''')

    def test_all_shipped_lua_parses_as_lua51(self):
        parser = self.lua.eval('function(s) local f,e=loadstring(s);return f~=nil,e end')
        for path in (ROOT / "mods").rglob("*.lua"):
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                ok, error = parser(path.read_text(encoding="utf8"))
                self.assertTrue(ok, error)

    def test_runtime_inventory_and_identity(self):
        self.run_lua('''
            next=nil -- PZ's Kahlua does not expose Lua 5.1's global next().
            Events=setmetatable({}, {__index=function(t,k) local v={Add=function() end};rawset(t,k,v);return v end})
            store={};ModData={getOrCreate=function() return store end}
            function isClient() return false end;function isServer() return false end
            function getTimestampMs() return 12345 end;function ZombRand() return 7 end
            Perks={Electricity="electricity",MetalWelding="welding"}
            function instanceof(item,name) return item.isBag==true end
            function array(items) return {size=function() return #items end,get=function(_,i) return items[i+1] end} end
            local function item(name) return {getFullType=function() return name end} end
            nested={getItems=function() return array({item("Base.Bandage"),item("Base.RippedSheets")}) end}
            bag={isBag=true,getFullType=function() return "Base.Bag" end,getInventory=function() return nested end}
            inventory={getItems=function() return array({bag,item("Base.Hammer")}) end}
            pd={}
            player={getInventory=function() return inventory end,getModData=function() return pd end,getPerkLevel=function(_,perk) return 7 end}
            function getPlayer() return player end
        ''')
        self.lua.execute((ROOT / "mods/KnoxQuest/42/media/lua/client/KnoxQuest/Runtime.lua").read_text(encoding="utf8"))
        self.run_lua('''
            K.start()
            assert(K.runtime.ready)
            K.confirmQuest("vanilla_demo:welcome")
            assert(K.isCompleted("vanilla_demo:basic_tools",K.getContext()))
            assert(K.isCompleted("vanilla_demo:first_aid",K.getContext()))
            assert(K.detectors.item({items={"Base.Hammer"},count=1},K.getContext()).current==1)
            local identity=pd.KnoxQuestCharacterId
            K.start()
            assert(pd.KnoxQuestCharacterId==identity)
            assert(K.isCompleted("vanilla_demo:welcome",K.getContext()))
            pd={};function getTimestampMs() return 22222 end
            K.start()
            assert(pd.KnoxQuestCharacterId~=identity)
            assert(not K.isCompleted("vanilla_demo:welcome",K.getContext()))
        ''')


if __name__ == "__main__":
    unittest.main()
