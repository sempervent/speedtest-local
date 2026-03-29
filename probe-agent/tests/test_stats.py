from probe_agent.stats import mean, successive_jitter_ms


def test_mean():
    assert mean([1.0, 2.0, 3.0]) == 2.0


def test_jitter():
    assert successive_jitter_ms([10.0, 12.0, 11.0]) > 0
