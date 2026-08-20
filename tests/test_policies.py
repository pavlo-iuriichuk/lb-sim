from lb_sim.domain import Instance
from lb_sim.policies import (
    LeastConnectionsPolicy,
    PickTwoRandomThenLeastLoadedPolicy,
    RoundRobinPolicy,
)


def test_round_robin_cycles_instances():
    instances = [
        Instance(name="a", capacity=10.0),
        Instance(name="b", capacity=10.0),
        Instance(name="c", capacity=10.0),
    ]
    policy = RoundRobinPolicy()

    assert policy.select(instances, {}) == instances[0]
    assert policy.select(instances, {}) == instances[1]
    assert policy.select(instances, {}) == instances[2]
    assert policy.select(instances, {}) == instances[0]


def test_least_connections_prefers_less_loaded_instance():
    instances = [
        Instance(name="a", capacity=10.0, current_connections=5),
        Instance(name="b", capacity=10.0, current_connections=1),
        Instance(name="c", capacity=10.0, current_connections=3),
    ]
    policy = LeastConnectionsPolicy()

    assert policy.select(instances, {}) == instances[1]


def test_pick_two_random_then_least_loaded_uses_sampled_pair():
    instances = [
        Instance(name="a", capacity=10.0, estimated_load=2.0),
        Instance(name="b", capacity=10.0, estimated_load=7.0),
        Instance(name="c", capacity=10.0, estimated_load=9.0),
        Instance(name="d", capacity=10.0, estimated_load=1.0),
    ]
    policy = PickTwoRandomThenLeastLoadedPolicy(rng_seed=7)

    selected = policy.select(instances, {})
    assert selected.name in {"a", "d"}


def test_instance_failure_rate_can_mark_unhealthy():
    instance = Instance(name="failing", capacity=10.0, failure_rate=1.0)

    instance.update_health()

    assert instance.is_healthy is False


def test_policy_skips_unhealthy_instances():
    healthy = Instance(name="healthy", capacity=10.0)
    unhealthy = Instance(name="unhealthy", capacity=10.0, is_healthy=False)
    policy = LeastConnectionsPolicy()

    selected = policy.select([healthy, unhealthy], {})

    assert selected == healthy
