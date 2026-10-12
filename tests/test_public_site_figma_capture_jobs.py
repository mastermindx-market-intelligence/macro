from tools.figma.public_site_baseline.capture_reference_matrix import build_capture_jobs


def test_build_capture_jobs_covers_all_canonical_states_in_order() -> None:
    jobs = build_capture_jobs()

    assert len(jobs) == 36
    assert [job.index for job in jobs] == list(range(36))
    assert jobs[0].page == "homepage"
    assert jobs[0].state == "1440-en"
    assert jobs[0].kind == "static"
    assert jobs[0].width == 1440
    assert jobs[0].language == "en"
    assert jobs[0].full_page is True
    assert jobs[19].page == "market-dashboards"
    assert jobs[19].state == "390-zh"
    assert jobs[20].page == "homepage"
    assert jobs[20].state == "observe"
    assert jobs[20].kind == "motion"
    assert jobs[20].wait_ms == 900
    assert jobs[-1].page == "market-dashboards"
    assert jobs[-1].state == "hold"
    assert jobs[-1].wait_ms == 6500


def test_capture_jobs_use_stable_filenames_and_query_modes() -> None:
    jobs = build_capture_jobs()
    static = jobs[3]
    motion = jobs[20]

    assert static.filename == "homepage-390-en.png"
    assert static.query == {"still": "1", "lang": "en"}
    assert motion.filename == "homepage-hero-observe.png"
    assert motion.query == {"lang": "en"}
