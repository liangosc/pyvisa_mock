from visa_mock.test.mock_instruments.instruments import Mocker1
import time


def test_delay_on_instrument():
    call_delay = 1
    mocker = Mocker1()

    # At first, there is no delay:
    t0 = time.time()
    mocker.send(":INSTR:CHANNEL1:VOLT?")
    call_time0 = time.time() - t0
    assert 0 <= call_time0 < 0.1

    # Now, to introduce the delay to the whole instrument
    mocker.set_call_delay(call_delay)

    # all the commands will have the same delay:
    t1 = time.time()
    mocker.send(":INSTR:CHANNEL1:VOLT 12")
    call_time1 = time.time() - t1
    assert 0 <= (call_time1 - call_time0 - call_delay) < 0.1

    t2 = time.time()
    voltage = mocker.send(":INSTR:CHANNEL1:VOLT?")
    call_time2 = time.time() - t2
    assert 0 <= (call_time2 - call_time0 - call_delay) < 0.1
    assert voltage == "12.0"


def test_delay_on_command():
    call_delay = 2
    mocker = Mocker1()

    cmd = ":INSTR:CHANNEL(.*):VOLT (.*)"

    # To introduce delay to one cmd only:
    mocker.set_call_delay(call_delay, cmd)
    assert mocker.__scpi_dict__[cmd].call_delay == call_delay
    t0 = time.time()
    mocker.send(":INSTR:CHANNEL1:VOLT 12")
    t1 = time.time()
    assert call_delay <= (t1 - t0) < call_delay + 0.1

    # Other commands should not have any delay:
    voltage = mocker.send(":INSTR:CHANNEL1:VOLT?")
    t0 = time.time()
    assert 0 <= (time.time() - t0) < 0.1
    assert voltage == "12.0"
