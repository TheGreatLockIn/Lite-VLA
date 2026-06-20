from litevla_edge.action_schema import parse_model_output


def test_discrete_action():
    command = parse_model_output("TURN_LEFT")
    assert command.valid
    assert command.linear_x == 0.0
    assert command.angular_z == 0.4


def test_extra_text_still_extracts_action():
    command = parse_model_output("I choose MOVE_FORWARD.")
    assert command.valid
    assert command.action == "MOVE_FORWARD"


def test_invalid_output_stops():
    command = parse_model_output("banana")
    assert not command.valid
    assert command.action == "STOP"
    assert command.linear_x == 0.0
    assert command.angular_z == 0.0


def test_json_command_is_clamped():
    command = parse_model_output('{"linear_x": 9, "angular_z": -9}')
    assert command.valid
    assert command.linear_x == 0.2
    assert command.angular_z == -0.6


def test_json_stop():
    command = parse_model_output('{"linear_x": 0.1, "angular_z": 0.1, "stop": true}')
    assert command.valid
    assert command.action == "STOP"
