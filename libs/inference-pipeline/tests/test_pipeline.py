from lr_frameflow_inference_pipeline import run_default_stub, run_pipeline


def test_run_default_stub_marks_stages():
    out = run_default_stub({"schema_version": "edit-request-v1"})
    assert out["stage"] == "normalized"
    assert "features" in out
    assert "confidence" in out


def test_custom_steps_injection():
    def only_norm(ctx: dict) -> dict:
        return {**ctx, "ok": True}

    out = run_pipeline((only_norm,), {"a": 1})
    assert out["ok"] is True
