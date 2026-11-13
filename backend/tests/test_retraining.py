from app.retraining.workflow import decide

CFG = {"min_roc_auc": 0.7, "min_improvement": 0.0}
GOOD = {"roc_auc": 0.84, "f1": 0.60}


def test_decide_floor_only_when_no_champion():
    assert decide(GOOD, None, CFG)[0] is True
    ok, why = decide({"roc_auc": 0.6, "f1": 0.5}, None, CFG)
    assert not ok and "floor" in why


def test_decide_requires_beating_champion_on_f1_and_auc():
    assert decide(GOOD, {"roc_auc": 0.80, "f1": 0.55}, CFG)[0] is True
    ok, why = decide(GOOD, {"roc_auc": 0.80, "f1": 0.65}, CFG)
    assert not ok and "f1" in why
    ok, why = decide(GOOD, {"roc_auc": 0.90, "f1": 0.50}, CFG)
    assert not ok and "roc_auc" in why


def test_decide_margin_can_be_tolerance():
    assert decide(GOOD, {"roc_auc": 0.85, "f1": 0.61}, {**CFG, "min_improvement": -0.02})[0] is True


def test_drift_trigger_skips_without_confirmed_drift(client, trained):
    client.put("/api/settings", json={"values": {"min_current_rows": 100000}})  # force "insufficient data"
    before = client.get("/api/models").json()
    run = client.post("/api/retraining/run", json={"trigger": "drift"}).json()
    assert run["status"] == "skipped" and run["drift_detected"] is None
    assert client.get("/api/models").json() == before  # nothing trained, nothing changed
    client.put("/api/settings", json={"values": {"min_current_rows": 50}})


def test_candidate_that_cannot_beat_champion_is_rejected_and_champion_untouched(client, trained):
    champ = client.get("/api/models").json()["champion_version"]
    client.put("/api/settings", json={"values": {"min_improvement": 0.2}})
    run = client.post("/api/retraining/run", json={"trigger": "manual", "dataset_id": trained["id"]}).json()
    assert run["status"] == "rejected" and run["champion_version"] == champ
    assert run["champion_metrics"] and run["candidate_metrics"]
    models = client.get("/api/models").json()
    assert models["champion_version"] == champ
    assert next(m for m in models["versions"] if m["version"] == run["candidate_version"])["status"] == "rejected"
    client.put("/api/settings", json={"values": {"min_improvement": 0.0}})


def test_good_candidate_is_promoted_previous_preserved_and_rollback_works(client, trained):
    old = client.get("/api/models").json()["champion_version"]
    client.put("/api/settings", json={"values": {"min_improvement": -0.2, "min_roc_auc": 0.5}})
    run = client.post("/api/retraining/run", json={"trigger": "manual", "dataset_id": trained["id"]}).json()
    assert run["status"] == "promoted", run
    new = run["candidate_version"]
    models = client.get("/api/models").json()
    assert models["champion_version"] == new
    assert next(m for m in models["versions"] if m["version"] == old)["status"] == "previous"
    assert client.post("/api/models/rollback").json()["champion_version"] == old
    assert client.get("/api/models").json()["champion_version"] == old
    client.put("/api/settings", json={"values": {"min_improvement": 0.0, "min_roc_auc": 0.7}})


def test_history_and_activity_are_recorded(client, trained):
    hist = client.get("/api/retraining/history").json()
    assert {"skipped", "rejected", "promoted"} <= {h["status"] for h in hist}
    events = {a["event"] for a in client.get("/api/activity?limit=200").json()}
    assert {"training.completed", "model.promoted", "model.rollback", "retraining.promoted"} <= events


def test_scheduler_setting_toggles_job(client):
    from app.retraining import scheduler
    scheduler._scheduler.start()
    try:
        r = client.put("/api/settings", json={"values": {"schedule_hours": 6}}).json()
        assert r["scheduler"]["enabled"] is True and r["scheduler"]["next_run"]
        r = client.put("/api/settings", json={"values": {"schedule_hours": 0}}).json()
        assert r["scheduler"]["enabled"] is False
    finally:
        scheduler.stop()
