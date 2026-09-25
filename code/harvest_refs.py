# -*- coding: utf-8 -*-
"""Fetch and verify every DOI reference: Crossref metadata for the citation, and the
abstract (Crossref, else Semantic Scholar, else PubMed) so each citation can be checked
against the claim it is attached to. Titles starting 'WITHDRAWN' are rejected.

    python harvest_refs.py
"""
import html
import io
import json
import re
import time

import requests

UA = {"User-Agent": "pabhs-refcheck (mailto:sandler.leon@gmail.com)"}
DOIS = {
    "bibel1992": "10.1115/1.2929252",
    "zhu2018": "10.1115/1.4040421",
    "zhu2019": "10.1115/pvp2019-93062",
    "brown2010": "10.1115/pvp2010-25772",
    "kumakura2003": "10.1115/pvp2003-1867",
    "nassar2007speed": "10.1115/1.2749290",
    "nassar2007angle": "10.1115/1.2821388",
    "omiya2016": "10.1115/pvp2016-63720",
    "sawa2003": "10.1115/pvp2003-1875",
    "abid2013": "10.1115/pvp2013-97863",
    "persson2021": "10.4271/2021-01-5073",
    "ma2023": "10.1115/pvp2023-107648",
    "berry2019": "10.1115/pvp2019-93136",
    "horstmeyer2025": "10.1115/pvp2025-153394",
    "vakil2012": "10.1016/j.jlp.2011.12.002",
    "nozu2018": "10.1109/aim.2018.8452338",
    "yibang2023": "10.1007/s00170-023-11597-6",
    "ali2018": "10.1007/s00170-018-3133-0",
    "martinez2020": "10.1007/s00170-020-05695-y",
    "shukla2016a": "10.1016/j.robot.2015.09.012",
    "shukla2016b": "10.1016/j.robot.2015.09.013",
    "arakelian2016": "10.1080/01691864.2015.1090334",
    "singh2023": "10.1007/978-981-99-2516-2",
    "ovatman2016": "10.1007/s10270-014-0448-7",
    "liu2013": "10.1016/j.eswa.2012.08.010",
    "negahban2014": "10.1016/j.jmsy.2013.12.007",
    "zhuang2021": "10.1016/j.jmsy.2020.05.011",
}


def initials(given):
    return "".join(p[0] for p in re.split(r"[\s\-.]+", given) if p)


def clean(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    return re.sub(r"\s+", " ", t).strip()


def main():
    refs, abstracts = {}, {}
    for tag, doi in DOIS.items():
        m = requests.get("https://api.crossref.org/works/" + doi, headers=UA, timeout=40).json()["message"]
        title = clean(m["title"][0])
        assert not title.upper().startswith("WITHDRAWN"), (tag, title)
        au = []
        for a in m.get("author", []):
            if "family" in a:
                fam = a["family"]
                fam = fam.title() if fam.isupper() else fam
                au.append("%s %s" % (fam.replace("*", "").strip(), initials(a.get("given", ""))))
            elif "name" in a:
                au.append(a["name"])
        cont = clean((m.get("container-title") or [""])[0])
        # the volume year (print) is what a citation needs; 'issued' is often online-first
        yr = ((m.get("published-print") or m.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        refs[tag] = {"doi": doi.lower(), "authors": au, "title": title, "container": cont,
                     "year": yr, "volume": m.get("volume"), "issue": m.get("issue"),
                     "page": m.get("page") or m.get("article-number"), "type": m.get("type"),
                     "publisher": m.get("publisher"),
                     "event": clean((m.get("event") or {}).get("name", ""))}
        ab = clean(m.get("abstract", ""))
        if not ab:
            try:
                s = requests.get("https://api.semanticscholar.org/graph/v1/paper/DOI:" + doi,
                                 params={"fields": "abstract,tldr"}, timeout=40).json()
                ab = clean(s.get("abstract") or (s.get("tldr") or {}).get("text") or "")
            except Exception:
                pass
            time.sleep(1.1)
        abstracts[tag] = ab
        print("%-16s %s | %s | %s %s | abstract %d chars"
              % (tag, ", ".join(au[:2]), title[:60], cont[:30], yr, len(ab)))
        time.sleep(0.3)
    io.open("_refs.json", "w", encoding="utf-8").write(json.dumps(refs, indent=1, ensure_ascii=False))
    io.open("_abstracts.txt", "w", encoding="utf-8").write(
        "\n\n".join("## %s  (%s)\n%s" % (k, refs[k]["title"], v or "[no abstract available]")
                    for k, v in abstracts.items()))


if __name__ == "__main__":
    main()
