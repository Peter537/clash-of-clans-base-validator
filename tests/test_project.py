import copy
from contextlib import contextmanager
import csv
import json
from pathlib import Path
import subprocess
import sys
import shutil
import uuid
import unittest
import xml.etree.ElementTree as ET

from coc_base.io import changed_types, current_rules_path, digest, footprint, load_bundle, read_json
from coc_base.profiles import max_profile
from coc_base.validate import copy_link_info, validate
from coc_base.render import render, svg
from coc_base.export import export
from coc_base.docs import generated_docs

ROOT = Path(__file__).resolve().parents[1]
RULES = read_json(current_rules_path())


@contextmanager
def temporary_directory():
    # Inherit workspace ACLs: Windows mkdtemp's private DACL excludes sandbox tokens.
    path = ROOT/".test-work"/uuid.uuid4().hex
    path.mkdir(parents=True)
    assert path.resolve().is_relative_to(ROOT/".test-work")
    try:
        yield path
    finally:
        assert path.resolve().is_relative_to(ROOT/".test-work")
        shutil.rmtree(path)
        try:
            path.parent.rmdir()
        except OSError:
            pass


def inventory_fixture(th):
    """Flat, fixed test shelves exercise inventory; they are not name-base designs."""
    profile = max_profile(RULES, th, bob_unlocked=th >= 10)
    profile.pop("level_inventory")
    slots = {1:[(x,34+y) for y in range(2) for x in range(44)],
             2:[(x,30+y) for y in (0,2) for x in range(0,44,2)],
             3:[(x,y) for y in range(12,30,3) for x in range(0,42,3)],
             4:[(x,8) for x in range(0,44,4)],
             "wall":[(x,y) for y in range(8) for x in range(44)]}
    cursor = {k:0 for k in slots}
    objects = []
    heroes = ["king","queen","warden","champion"]
    for kind,n in profile["inventory"].items():
        spec = RULES["objects"][kind]
        shelf = "wall" if kind == "wall" else spec["width"]
        for i in range(n):
            x,y = slots[shelf][cursor[shelf]]; cursor[shelf] += 1
            obj = {"id":f"{kind}-{i+1:03}","type":kind,"x":x,"y":y,"level":spec["max_levels"][str(th)]}
            settings = {k:values[0] for k,values in spec.get("settings",{}).items()}
            if kind == "hero_banner": settings["hero"] = heroes[i]
            if kind == "crafting_station":settings={"variant":"hero_hunter","modules":{"hp":0,"attack":0,"effect":0}}
            if settings: obj["settings"]=settings
            objects.append(obj)
    return {"schema_version":1,"name":"inventory fixture","town_hall":th,"village":"HV","ruleset_id":RULES["id"],"objects":objects},profile


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.layout,self.profile = inventory_fixture(18)
        self.rules = copy.deepcopy(RULES)

    def codes(self,layout=None,rules=None,profile=None):
        return {d["code"] for d in validate(layout or self.layout,rules or self.rules,profile or self.profile)["diagnostics"]}

    def obj(self,kind):
        return next(o for o in self.layout["objects"] if o["type"]==kind)

    def test_public_example_independent_tile_audit(self):
        for th in (3, 4, 18):
            with self.subTest(th=th):
                if th == 3:
                    l,r,p=load_bundle(ROOT/"examples/th3-hi/layout.json")
                else:
                    l,p=inventory_fixture(th);r=RULES
                result=validate(l,r,p)
                self.assertEqual(result["status"],"PASS",result["diagnostics"])
                self.assertEqual(result["placed_counts"]["wall"],p["inventory"]["wall"])
                # Independent tile-set audit avoids relying only on the production overlap result.
                tiles=[]
                for o in l["objects"]:
                    x,y,w,h=footprint(o,r);self.assertGreaterEqual(min(x,y),0)
                    self.assertLessEqual(x+w,44);self.assertLessEqual(y+h,44)
                    tiles.extend((xx,yy) for xx in range(x,x+w) for yy in range(y,y+h))
                self.assertEqual(len(tiles),len(set(tiles)))
                self.assertEqual(result["placed_counts"],p["inventory"])

    def test_every_current_th_and_wall_shortage(self):
        expected=[0,25,50,75,100,125,175,225,250,275,300,300,300,325,325,325,325,325]
        for th in range(1,19):
            with self.subTest(th=th):
                l,p=inventory_fixture(th);result=validate(l,RULES,p)
                self.assertEqual(result["status"],"PASS",result["diagnostics"])
                self.assertEqual(p["inventory"].get("wall",0),expected[th-1])
                wall=next((o for o in l["objects"] if o["type"]=="wall"),None)
                if wall:
                    l["objects"].remove(wall);self.assertIn("INVENTORY",self.codes(l,RULES,p))
                else:
                    l["objects"].append({"id":"wall-extra","type":"wall","x":43,"y":43,"level":1})
                    self.assertIn("AVAILABILITY",self.codes(l,RULES,p))

    def test_missing_and_excess(self):
        self.layout["objects"].pop(); self.assertIn("INVENTORY",self.codes())
        extra=copy.deepcopy(self.obj("wall"));extra["id"]="extra";self.layout["objects"].append(extra)
        self.assertIn("INVENTORY",self.codes()); self.assertIn("OVERLAP",self.codes())

    def test_duplicate_ids_and_integer_coordinates(self):
        self.layout["objects"][1]["id"]=self.layout["objects"][0]["id"]
        self.assertIn("DUPLICATE_ID",self.codes())
        for value in (1.0,True,"3",None):
            with self.subTest(value=value):
                self.obj("town_hall")["x"]=value;self.assertIn("COORDINATE",self.codes())

    def test_edge_and_unequal_footprints(self):
        l,p=inventory_fixture(18)
        for o in l["objects"]:
            if o["type"]=="town_hall":target=o;break
        target["x"],target["y"]=40,40
        self.assertNotIn("BOUNDARY",self.codes(l,RULES,p))
        target["x"]=41;self.assertIn("BOUNDARY",self.codes(l,RULES,p))
        target["x"]=-1;self.assertIn("BOUNDARY",self.codes(l,RULES,p))
        self.assertEqual((RULES["objects"]["army_camp"]["width"],RULES["objects"]["clan_castle"]["width"]),(4,3))
        target["x"],target["y"]=0,34
        self.assertIn("OVERLAP",self.codes(l,RULES,p))

    def test_obstacles_and_reservations(self):
        o=self.obj("town_hall")
        area={"x":o["x"],"y":o["y"],"width":1,"height":1,"label":"test tree"}
        self.profile["blocked_areas"]=[area];self.assertIn("BLOCKED",self.codes())
        self.profile["blocked_areas"]=[];self.layout["reserved_areas"]=[area];self.assertIn("BLOCKED",self.codes())
        area["allow_types"]=["town_hall"];self.assertNotIn("BLOCKED",self.codes())
        area["width"]=0;self.assertIn("AREA_SCHEMA",self.codes())

    def test_levels_and_mixed_walls(self):
        self.obj("wall")["level"]=18;self.assertEqual(validate(self.layout,self.rules,self.profile)["status"],"PASS")
        self.obj("wall")["level"]=20;self.assertIn("LEVEL",self.codes())
        self.obj("town_hall")["level"]=17;self.assertIn("LEVEL",self.codes())

    def test_mergers_and_optional_bob(self):
        self.profile["inventory"]["cannon"]=1;self.assertIn("MERGER",self.codes())
        self.profile["inventory"].pop("cannon");self.profile["inventory"]["super_wizard_tower"]=3
        self.assertIn("MERGER",self.codes());self.assertIn("INVENTORY_CAP",self.codes())
        self.profile["bob_unlocked"]=False;self.assertIn("BOB",self.codes())

    def test_purchased_huts_bob_and_gear_prerequisites(self):
        l,p=inventory_fixture(2)
        p["inventory"]["builders_hut"]=2
        l["objects"]=[o for o in l["objects"] if not (o["type"]=="builders_hut" and int(o["id"].split('-')[-1])>2)]
        self.assertEqual(validate(l,RULES,p)["status"],"PASS")
        p["inventory"]["builders_hut"]=0
        self.assertIn("INVENTORY_MIN",self.codes(l,RULES,p))
        p["inventory"]["bobs_hut"]=1;p["bob_unlocked"]=True
        self.assertIn("INVENTORY_CAP",self.codes(l,RULES,p))
        cannon=next(o for o in l["objects"] if o["type"]=="cannon")
        cannon["settings"]={"geared":True}
        self.assertIn("SETTINGS_LEVEL",self.codes(l,RULES,p))
        cannon["settings"]["geared"]=1
        self.assertIn("SETTINGS",self.codes(l,RULES,p))

    def test_seasonal_variants_and_modules(self):
        station=self.obj("crafting_station")
        for variant in [*self.rules["crafted_phase"]["variants"],"inactive"]:
            station["settings"]["variant"]=variant;self.assertNotIn("SEASONAL_VARIANT",self.codes())
        station["settings"]["variant"]="roaster";self.assertIn("SEASONAL_VARIANT",self.codes())
        station["settings"]["variant"]="hot_candle";station["settings"]["modules"]["hp"]=10
        self.assertIn("SEASONAL_MODULE",self.codes())
        self.profile["crafted_phase"]="old";self.assertIn("SEASONAL_PHASE",self.codes())

    def test_hero_and_settings_prerequisites(self):
        self.obj("spell_tower")["level"]=1;self.obj("spell_tower")["settings"]["spell"]="earthquake"
        self.assertIn("SETTINGS_LEVEL",self.codes())
        banners=[o for o in self.layout["objects"] if o["type"]=="hero_banner"]
        banners[1]["settings"]["hero"]="king";self.assertIn("HERO_DUPLICATE",self.codes())
        l,p=inventory_fixture(4);banner=next(o for o in l["objects"] if o["type"]=="hero_banner")
        banner["settings"]["hero"]="queen";self.assertIn("HERO_AVAILABILITY",self.codes(l,RULES,p))

    def test_unknowns_are_not_passes(self):
        self.rules["objects"]["wall"]["status"]="unverified"
        result=validate(self.layout,self.rules,self.profile);self.assertEqual(result["status"],"UNRESOLVED")
        self.rules["objects"]["wall"]["status"]="reviewed"
        self.rules["uncertainties"].append({"blocks_validation":True,"types":["wall"],"description":"unknown wall cap"})
        self.assertIn("UNKNOWN_RULE",self.codes())
        self.layout["ruleset_id"]="old";self.assertIn("RULESET_ID",self.codes())

    def test_copy_link_format_does_not_authenticate(self):
        url="https://link.clashofclans.com/jp?action=OpenLayout&id=TH12%3AHV%3AAAAACgAAAAGePSBQZE-TPdsN4ymce7yw"
        info=copy_link_info(url);self.assertEqual(info["town_hall"],12);self.assertEqual(info["authenticity"],"unconfirmed")
        for bad in [url.replace("https:","http:"),url.replace("link.clashofclans.com","evil.test"),url+"&id=other",url.replace("OpenLayout","Other")]:
            with self.assertRaises(ValueError):copy_link_info(bad)
        self.layout["copy_link"]=url;self.assertIn("COPY_LINK",self.codes())

    def test_json_roundtrip_and_portable_export(self):
        self.assertEqual(json.loads(json.dumps(self.layout)),self.layout)
        with temporary_directory() as d:
            export(self.layout,self.rules,self.profile,d); l,r,p=load_bundle(Path(d)/"layout.json", historical=True)
            self.assertEqual(l["objects"],self.layout["objects"]);self.assertEqual(r,self.rules);self.assertEqual(p,self.profile)
            self.assertEqual(validate(l,r,p)["status"],"PASS")
            with (Path(d)/"coordinates.csv").open(encoding="utf-8") as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),len(l["objects"]))
            byid={o["id"]:o for o in l["objects"]}
            for row in rows:
                o=byid[row["id"]];self.assertEqual(tuple(int(row[k]) for k in ("x","y","width","height")),footprint(o,r))

    def test_svg_footprints_identical_and_invalid_visible(self):
        for iso in (True,False):
            tree=ET.fromstring(svg(self.layout,self.rules,self.profile,validate(self.layout,self.rules,self.profile),iso))
            placed=[g for g in tree.iter() if "data-id" in g.attrib]
            self.assertEqual(len(placed),len(self.layout["objects"]))
            byid={o["id"]:o for o in self.layout["objects"]}
            for g in placed:self.assertEqual(tuple(int(g.attrib[k]) for k in ("data-x","data-y","data-width","data-height")),footprint(byid[g.attrib["data-id"]],self.rules))
        self.obj("town_hall")["x"]=-2
        with temporary_directory() as d:
            out=Path(d)/"bad.html";render(self.layout,self.rules,self.profile,out)
            text=out.read_text(encoding="utf-8");self.assertIn('data-x="-2"',text);self.assertIn("#ff776d",text);self.assertIn("INVALID",text)

    def test_rules_change_identifies_affected_types(self):
        new=copy.deepcopy(self.rules);new["objects"]["clan_castle"]["width"]=4
        self.assertEqual(changed_types(self.rules,new),["clan_castle"])

    def test_cli_all_interfaces(self):
        with temporary_directory() as d:
            commands=[["validate","examples/th3-hi/layout.json","--json",str(Path(d)/"v.json")],
                      ["render","examples/th3-hi/layout.json","--output",str(Path(d)/"p.html")],
                      ["export","examples/th3-hi/layout.json","--output",str(Path(d)/"bundle")],
                      ["profile","create","--town-hall","3","--inventory","examples/th3-hi/inventory.json","--output",str(Path(d)/"account.json")],
                      ["docs","--output",str(Path(d)/"docs")]]
            for args in commands:
                result=subprocess.run([sys.executable,"-m","coc_base",*args],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual((Path(d)/"docs/catalogue.md").read_text(encoding="utf-8"),generated_docs(RULES))
            newer=copy.deepcopy(RULES);newer["id"]="reviewed-future-fixture"
            newer["objects"]["wall"]["max_levels"]["3"]=4
            rules_path=Path(d)/"newer.json";rules_path.write_text(json.dumps(newer),encoding="utf-8")
            report_path=Path(d)/"migration.json"
            result=subprocess.run([sys.executable,"-m","coc_base","validate","examples/th3-hi/layout.json","--ruleset",str(rules_path),"--json",str(report_path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,2,result.stdout+result.stderr)
            migration=read_json(report_path)["migration"]
            self.assertEqual(migration["changed_types"],["wall"])
            self.assertEqual(len(migration["affected_objects"]),50)
            (Path(d)/"bundle/profile.json").write_text('[]',encoding="utf-8")
            result=subprocess.run([sys.executable,"-m","coc_base","validate",str(Path(d)/"bundle/layout.json")],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,3)
            self.assertNotIn("Traceback",result.stderr)

    def test_duplicate_json_keys_rejected(self):
        with temporary_directory() as d:
            path=Path(d)/"duplicate.json";path.write_text('{"x":1,"x":2}',encoding="utf-8")
            with self.assertRaises(ValueError):read_json(path)

    def test_skill_and_docs_consistency(self):
        from tools.check_docs import check
        self.assertEqual(check(ROOT),[])


if __name__ == "__main__":
    unittest.main()
