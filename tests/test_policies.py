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
