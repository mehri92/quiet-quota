import json
from pathlib import Path
import sys
import tempfile
import unittest
from quota_core import ThresholdPolicy, weekly_snapshot, validate_config, CodexReader


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"state.json"
        self.p = ThresholdPolicy(self.path)
        self.reset = 2000000000

    def check(self, used, **kwargs):
        return self.p.observe("account", {"used": used, "reset": self.reset},
                              [50, 75, 90, 95], now=1900000000, **kwargs)

    def test_first_start_silent_even_above_threshold(self):
        self.assertFalse(self.check(92))
        self.assertFalse(self.check(94))
        self.assertTrue(self.check(95))

    def test_exact_crossing_and_no_spam(self):
        self.assertFalse(self.check(49))
        self.assertTrue(self.check(50))
        for used in (50, 51, 67, 74):
            self.assertFalse(self.check(used))

    def test_restart_does_not_repeat(self):
        self.check(49)
        self.check(75)
        self.p = ThresholdPolicy(self.path)
        self.assertFalse(self.check(75))
        self.assertTrue(self.check(90))

    def test_jump_is_one_alert_and_marks_lower_levels(self):
        self.check(49)
        self.assertTrue(self.check(92))
        self.assertFalse(self.check(92))
        self.assertEqual(self.p.state["account"]["seen"], [50, 75, 90])

    def test_small_correction_never_rearms(self):
        self.check(49)
        self.check(75)
        self.assertFalse(self.check(74))
        self.reset += 60
        self.assertFalse(self.check(76))

    def test_next_cycle_rearms(self):
        self.check(49)
        self.check(75)
        self.reset += 604800
        self.assertFalse(self.check(10))
        self.assertTrue(self.check(50))

    def test_paused_alert_is_coalesced_until_resume(self):
        self.check(49)
        self.assertFalse(self.check(75, paused=True))
        self.assertFalse(self.check(92, paused=True))
        self.assertTrue(self.check(92))
        self.assertFalse(self.check(92))

    def test_corrupt_state_establishes_silent_baseline(self):
        self.path.write_text("broken")
        self.p = ThresholdPolicy(self.path)
        self.assertFalse(self.check(95))


class SchemaTests(unittest.TestCase):
    def payload(self, **changes):
        w = {"windowDurationMins": 10080, "usedPercent": 67, "resetsAt": 2000000000} | changes
        return {"rateLimitsByLimitId": {"codex": {"primary": {
            "windowDurationMins": 300, "usedPercent": 88}, "secondary": w}}}

    def test_selects_weekly_not_five_hour(self):
        self.assertEqual(weekly_snapshot(self.payload(), now=1900000000)["used"], 67)

    def test_missing_weekly_is_not_fabricated(self):
        with self.assertRaises(ValueError):
            weekly_snapshot(self.payload(windowDurationMins=300), now=1900000000)

    def test_stale_invalid_data_rejected(self):
        for changes in ({"usedPercent": float("nan")}, {"usedPercent": 101},
                        {"resetsAt": None}, {"resetsAt": 1800000000}):
            with self.assertRaises(ValueError):
                weekly_snapshot(self.payload(**changes), now=1900000000)

    def test_other_bucket_never_confused_with_general_codex(self):
        result = self.payload()
        result["rateLimitsByLimitId"]["other"] = result["rateLimitsByLimitId"].pop("codex")
        with self.assertRaises(ValueError):
            weekly_snapshot(result, now=1900000000)

    def test_legacy_single_bucket(self):
        self.assertEqual(weekly_snapshot({"rateLimits": self.payload()["rateLimitsByLimitId"]["codex"]},
                                       now=1900000000)["used"], 67)

    def test_settings_validate_and_deduplicate(self):
        self.assertEqual(validate_config({"thresholds": [90, 50, 50]})["thresholds"], [50, 90])
        for bad in ([], [101], [True], [2.5]):
            with self.assertRaises(ValueError):
                validate_config({"thresholds": bad})


class TransportTests(unittest.TestCase):
    def test_read_only_handshake_through_real_stdio(self):
        # Fail the fake service if the client tries to start any agent work.
        script = '''import json, sys, time
initialized = False
for line in sys.stdin:
 m = json.loads(line); method = m["method"]
 if method == "initialize":
  r = {"userAgent": "test"}
 elif method == "initialized":
  initialized = True; continue
 elif method == "account/read" and initialized:
  r = {"account": {"type": "chatgpt", "email": "test@example.invalid", "planType": "pro"}}
 elif method == "account/rateLimits/read" and initialized:
  r = {"rateLimits": {"limitId": "codex", "secondary": {"windowDurationMins":10080,"usedPercent":67,"resetsAt":int(time.time())+3600}}}
 else:
  sys.exit(9)
 print(json.dumps({"id":m["id"],"result":r}), flush=True)
'''
        reader = CodexReader([sys.executable, "-u", "-c", script])
        try:
            identity, snap = reader.read()
            self.assertEqual(snap["used"], 67)
            self.assertNotIn("@", identity)
            self.assertEqual(reader.read()[0], identity)
        finally:
            reader.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
