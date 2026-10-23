import os

from llm_guard_proxy.cli import main


def test_cli_sets_runtime_options(monkeypatch) -> None:
    captured = {}

    def mock_run(app, **kwargs):
        captured["app"] = app
        captured.update(kwargs)

    monkeypatch.setattr("llm_guard_proxy.cli.uvicorn.run", mock_run)

    main([
        "--host", "0.0.0.0",
        "--port", "9000",
        "--upstream", "http://model.test:8080",
        "--policy", "school",
        "--reload",
    ])

    assert captured == {
        "app": "llm_guard_proxy.main:app",
        "host": "0.0.0.0",
        "port": 9000,
        "reload": True,
    }
    assert os.environ["GUARD_UPSTREAM_BASE_URL"] == "http://model.test:8080"
    assert os.environ["GUARD_POLICY_PATH"] == "school"
