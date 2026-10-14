from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "ops/systemd/mastermind-earnings-worker.service"
TIMER = ROOT / "ops/systemd/mastermind-earnings-worker.timer"
BOOTSTRAP = ROOT / "ops/bootstrap_earnings_worker_linux.sh"


def test_linux_service_reuses_existing_worker_and_inference_owner():
    text = SERVICE.read_text()
    for required in (
        "User=longr",
        "WorkingDirectory=/opt/mastermind-earnings/macro",
        "Slice=mastermind-inference.slice",
        "CPUWeight=10",
        "IOWeight=10",
        "Nice=10",
        "IOSchedulingClass=idle",
        "After=network-online.target mastermind-inference-guard.service",
        "run_with_env.sh /etc/mastermind/earnings-worker.env",
        "run_earnings_worker.sh",
        "ProtectSystem=strict",
        "NoNewPrivileges=true",
        "ReadWritePaths=/opt/mastermind-earnings/macro /var/lib/mastermind-earnings /run/lock",
    ):
        assert required in text


def test_linux_timer_is_primary_ten_minutes_before_mac_fallback():
    text = TIMER.read_text()
    for when in ("17:35:00", "20:35:00", "23:35:00"):
        assert f"OnCalendar=*-*-* {when}" in text
    assert text.count("OnCalendar=") == 3
    assert "Persistent=true" in text
    assert "Unit=mastermind-earnings-worker.service" in text


def test_bootstrap_reuses_plane_without_embedding_secrets():
    text = BOOTSTRAP.read_text()
    for required in (
        "/etc/mastermind/earnings-worker.env",
        "ops/launchd/run_earnings_worker.sh",
        "ops/launchd/run_with_env.sh",
        "ops/earnings_worker_requirements.txt",
        "mastermind-inference-guard.service",
        "systemctl enable --now",
        "--ff-only",
    ):
        assert required in text
    assert "git push" not in text
    assert "git commit" not in text


def test_units_contain_no_secret_values_or_second_router():
    combined = SERVICE.read_text() + TIMER.read_text()
    for token in ("R2_SECRET_ACCESS_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "MOONSHOT_API_KEY"):
        assert token not in combined
    assert "ollama serve" not in combined
    assert "11434" not in combined
    assert "11435" not in combined
