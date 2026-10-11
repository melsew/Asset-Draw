from worker.celery_app import celery_app, ping


def test_ping_task_registered_and_runs():
    assert "system.ping" in celery_app.tasks
    assert ping.apply().get() == "pong"
