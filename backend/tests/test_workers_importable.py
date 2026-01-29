def test_worker_modules_import():
    import backend.jobs.hydration_worker  # noqa: F401
    import backend.jobs.queue_worker  # noqa: F401
    import backend.jobs.event_projector_worker  # noqa: F401
