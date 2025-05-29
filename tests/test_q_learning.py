# veriies with epsilon = 0, returns action w/ highest q, and for ep = 1 on prev unseen state returns random valid action

import sys
import pytest

sys.path.insert(0, "src")

from agents.learning.rewards import QTable

def test_choose_max_q_action():
    qt = QTable(actions=['stop','go','slow'], epsilon=0.0)
    qt.Q['state1'] = [1.0, 5.0, 2.0]
    assert qt.choose_action('state1') == 'go'

@pytest.mark.parametrize("state", ['foo', 'bar', 'baz'])
def test_choose_random_on_unknown(state):
    qt = QTable(actions=['stop','go','slow'], epsilon=1.0)  # force explore
    assert qt.choose_action(state) in ['stop','go','slow']
