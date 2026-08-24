#!/usr/bin/env python3
"""Voegt beweging toe aan de gegenereerde CED-presentatie:
- fade-overgang tussen alle slides (fade-through-black op donkere slides 1 en 10)
- automatisch infadende elementen per slide (gestaffeld, geen klik nodig)
Werkt direct op het .pptx-bestand (in-place).
"""
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from defusedxml import ElementTree as DET

NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
DARK_SLIDES = {1, 10}  # fade-through-black
STAGGER_MS = 180
FADE_MS = 700


def shape_ids(slide_xml: str):
    """IDs van de directe kinderen van spTree (sp, pic, graphicFrame, grpSp)."""
    root = DET.fromstring(slide_xml)
    sp_tree = root.find(f".//{{{NS_P}}}cSld/{{{NS_P}}}spTree")
    ids = []
    for child in sp_tree:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag not in ("sp", "pic", "graphicFrame", "grpSp"):
            continue
        cnvpr = child.find(f".//{{{NS_P}}}cNvPr")
        if cnvpr is not None:
            ids.append(cnvpr.get("id"))
    return ids


def effect_xml(next_id: int, spid: str, delay: int):
    a, b, c, e = next_id, next_id + 1, next_id + 2, next_id + 3
    return next_id + 4, (
        f'<p:par><p:cTn id="{a}" fill="hold"><p:stCondLst><p:cond delay="{delay}"/></p:stCondLst>'
        f'<p:childTnLst><p:par><p:cTn id="{b}" presetID="10" presetClass="entr" presetSubtype="0" '
        f'fill="hold" grpId="0" nodeType="withEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
        f'<p:childTnLst>'
        f'<p:set><p:cBhvr><p:cTn id="{c}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/>'
        f'</p:stCondLst></p:cTn><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'
        f'<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
        f'<p:to><p:strVal val="visible"/></p:to></p:set>'
        f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{e}" dur="{FADE_MS}"/>'
        f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect>'
        f'</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>'
    )


def motion_xml(slide_no: int, ids):
    thru = ' thruBlk="1"' if slide_no in DARK_SLIDES else ""
    transition = f'<p:transition spd="slow"><p:fade{thru}/></p:transition>'

    next_id, effects = 4, []
    for i, spid in enumerate(ids):
        next_id, xml = effect_xml(next_id, spid, i * STAGGER_MS)
        effects.append(xml)
    bldps = "".join(f'<p:bldP spid="{s}" grpId="0"/>' for s in ids)

    timing = (
        '<p:timing><p:tnLst><p:par>'
        '<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
        '<p:seq concurrent="1" nextAc="seek">'
        '<p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        '<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
        f'<p:childTnLst>{"".join(effects)}</p:childTnLst></p:cTn></p:par>'
        '</p:childTnLst></p:cTn>'
        '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
        '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
        '</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>'
        f'<p:bldLst>{bldps}</p:bldLst></p:timing>'
    )
    return transition + timing


def main(pptx_path: str):
    src = Path(pptx_path)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "unpacked"
        with zipfile.ZipFile(src) as zf:
            names = zf.namelist()
            zf.extractall(tmp)

        for name in names:
            m = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", name)
            if not m:
                continue
            slide_no = int(m.group(1))
            path = tmp / name
            xml = path.read_text(encoding="utf-8")
            if "<p:transition" in xml or "<p:timing" in xml:
                continue
            ids = shape_ids(xml)
            insert = motion_xml(slide_no, ids)
            assert xml.rstrip().endswith("</p:sld>")
            xml = xml.replace("</p:sld>", insert + "</p:sld>")
            path.write_text(xml, encoding="utf-8")
            print(f"slide{slide_no}: overgang + {len(ids)} infadende elementen")

        out = src.with_suffix(".tmp.pptx")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in names:  # oorspronkelijke volgorde behouden
                zf.write(tmp / name, name)
        shutil.move(out, src)
    print(f"Klaar: {src}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "CED-directiepresentatie-voorbeeld.pptx")
