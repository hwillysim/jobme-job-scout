import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout

import job_scout as js

CFG = {"weights": {"experience_match": 0.5, "target_fit": 0.5}, "constraint_cutoff": 0.75}


class Tests(unittest.TestCase):
    def test_location_filter(self):
        for ok in ("Sydney", "Sydney, NSW", "Remote", "APAC", "Brisbane, QLD, au, Remote", "Melbourne or Remote"):
            self.assertTrue(js.location_ok(ok), ok)
        for bad in ("San Francisco, CA", "Remote within United States", "Singapore", "London, UK", ""):
            self.assertFalse(js.location_ok(bad), bad)

    def test_combine_weights_and_constraints(self):
        answers = {"experience_match": {"type": "score", "score": 4, "confidence": 0.9},
                   "target_fit": {"type": "score", "score": 2, "confidence": 0.7},
                   "matches_avoid": {"type": "noul", "noul": 0.9}, "wrong_level": {"type": "noul", "noul": 0.1}}
        score, conf, excluded, detail = js.combine(answers, CFG)
        self.assertEqual(score, 75.0)
        self.assertEqual(conf, 80)
        self.assertEqual(excluded, ["matches_avoid"])
        self.assertEqual(detail["experience_match"], 100)

    def test_combine_rejects_missing_score(self):
        with self.assertRaises(ValueError):
            js.combine({"experience_match": {"type": "score", "score": 3}}, CFG)

    def test_starter_config_is_blank_and_fully_explained(self):
        cfg = js.load("config.json")
        self.assertEqual(cfg["exclude_employers"], [])
        self.assertTrue(set(cfg["weights"]) <= set(js.DIMENSIONS))
        self.assertTrue(set(cfg["weights"]) <= set(js.LABELS))
        self.assertAlmostEqual(sum(cfg["weights"].values()), 1.0)
        agents = (js.ROOT / "AGENTS.md").read_text()
        for k, w in cfg["weights"].items():  # the table shown to the person matches the defaults
            self.assertIn(f"| {round(w * 100)}% |", agents)
        self.assertFalse((js.ROOT / "profile.json").exists(), "the starter must not ship anyone's profile")

    def test_questions_follow_weights(self):
        q = js.jev_questions(CFG)
        self.assertEqual({k for k, v in q.items() if v["type"] == "score"}, set(CFG["weights"]))
        self.assertTrue(all(q[k]["type"] == "noul" for k in js.CONSTRAINTS))

    def test_example_profile_covers_every_field_the_questions_read(self):
        profile = json.loads((js.ROOT / "profile.example.json").read_text())
        text = json.dumps(js.DIMENSIONS) + json.dumps(js.CONSTRAINTS)
        import re
        for field in set(re.findall(r"candidate\.(\w+)", text)):
            self.assertIn(field, profile)

    def test_detect_ats(self):
        self.assertEqual(js.detect_ats("https://job-boards.greenhouse.io/stripe/jobs/123")[:2], ("greenhouse", "stripe"))
        self.assertEqual(js.detect_ats("https://jobs.lever.co/cxnpl/abc")[:2], ("lever", "cxnpl"))
        self.assertIsNone(js.detect_ats("https://www.seek.com.au/job/1"))

    def test_check_reports_in_plain_words(self):
        orig = js.call_jev, js.fetch_greenhouse
        try:
            js.call_jev = lambda body, key: {"answers": {}}
            js.fetch_greenhouse = lambda src: iter([{}] * 3)
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(js.check(), 0)
            self.assertIn("JEV: working", out.getvalue())

            def denied(body, key):
                raise RuntimeError("JEV HTTP 401: unauthorised")
            js.call_jev = denied
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(js.check(), 1)
            self.assertIn("API key isn't saved", out.getvalue())

            def offline(body, key):
                raise RuntimeError("JEV connection failed: tunnel refused")
            js.call_jev = offline
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(js.check(), 1)
            self.assertIn("internet access", out.getvalue())
        finally:
            js.call_jev, js.fetch_greenhouse = orig

    def test_report_uses_current_weights(self):
        with tempfile.TemporaryDirectory() as d:
            orig = js.DB_PATH, js.REPORTS, js.load
            js.DB_PATH, js.REPORTS = pathlib.Path(d) / "jobs.sqlite", pathlib.Path(d) / "reports"
            cfg = {**orig[2]("config.json"), "weights": {"experience_match": 0.5, "community_impact": 0.5}}
            js.load = lambda name: cfg if name == "config.json" else orig[2](name)
            try:
                c = js.db()
                for i, (exp, impact, stored) in enumerate([(90, 90, 50.0), (40, 40, 99.0)]):
                    js.upsert(c, {"id": f"gh:a:{i}", "company": "Acme", "title": f"Role {i}", "location": "Sydney",
                                  "url": f"https://x/{i}", "description": "", "source": "greenhouse"}, js.now())
                    h = c.execute("select hash from jobs where id=?", (f"gh:a:{i}",)).fetchone()[0]
                    c.execute("insert into assessments values(?,?,?,?,?,?,?,?)",
                              (f"gh:a:{i}", h, js.now(), "m", stored, 80, "",
                               json.dumps({"experience_match": exp, "community_impact": impact})))
                c.commit()
                with redirect_stdout(io.StringIO()):
                    md = js.report(c).read_text()
            finally:
                js.DB_PATH, js.REPORTS, js.load = orig
        self.assertIn("Role 0 — Acme](https://x/0) — 90%", md)  # stored 50% is rescored with today's weights
        self.assertNotIn("Role 1", md)                          # stored 99% is really 40%

    def test_top_up_only_asks_roles_that_could_reach_threshold(self):
        cfg = {"weights": {"experience_match": 0.5, "community_impact": 0.5}, "shortlist_threshold": 65}
        self.assertEqual(js.missing_dims({"experience_match": 80}, cfg), ["community_impact"])
        self.assertEqual(js.rescore({"experience_match": 80, "community_impact": 40}, cfg), 60.0)

    def test_dismiss_marks_roles_reported(self):
        c = js.sqlite3.connect(":memory:"); c.row_factory = js.sqlite3.Row
        c.execute("create table jobs(id text, hash text)")
        c.execute("create table reported(job_id text, hash text, reported text, primary key(job_id, hash))")
        c.execute("insert into jobs values('web:1','h1')")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(js.dismiss(c, ["web:1"]), 1)

    def test_no_personal_details_go_to_jev(self):
        profile = {"name": "Jane Citizen", "email": "jane@example.com", "phone": "0412 345 678",
                   "summary": "Ops lead. Contact jane.c@gmail.com, +61 412 345 678, linkedin.com/in/janec, https://jane.dev",
                   "experience": ["Team Leader, a big four bank (2018-2020): $25m in savings, 8 staff, (02) 9876 5432"],
                   "location": "Sydney, hybrid", "extra": {"referees": "Bob 0400 000 000", "note": "kept"}}
        job = {"company": "Acme", "title": "Ops", "location": "Sydney", "description": "d"}
        sent = json.dumps(js.payload(profile, job, js.load("config.json")))
        for leak in ("Jane Citizen", "jane@example.com", "jane.c@gmail.com", "412 345 678", "linkedin.com", "jane.dev",
                     "9876 5432", "Bob", "referees"):
            self.assertNotIn(leak, sent)
        for kept in ("Ops lead", "2018-2020", "$25m", "8 staff", "Sydney, hybrid", "kept"):
            self.assertIn(kept, sent)

    def test_key_file_is_read_and_never_committed(self):
        import os
        orig, env = js.KEY_FILE, {k: os.environ.pop(k) for k in ("JEV_API_KEY", "TYPESAFE_API_KEY") if k in os.environ}
        try:
            with tempfile.TemporaryDirectory() as d:
                js.KEY_FILE = pathlib.Path(d) / "jev_key.txt"
                self.assertEqual(js.api_key({}), "")
                js.KEY_FILE.write_text("\ufeffabc123\n", encoding="utf-8")  # a Notepad BOM and a trailing newline
                self.assertEqual(js.api_key({}), "abc123")
        finally:
            js.KEY_FILE = orig
            os.environ.update(env)
        self.assertIn("jev_key.txt", (js.ROOT / ".gitignore").read_text().split())


if __name__ == "__main__":
    unittest.main()
