from visa_mock.test.mock_instruments.instruments import Mocker1, Mocker2


def test_base():
    mocker = Mocker1()
    mocker.send(":INSTR:CHANNEL1:VOLT 12")
    mocker.send(":INSTR:CHANNEL2:VOLT 13.4")

    voltage = mocker.send(":INSTR:CHANNEL1:VOLT?")
    assert voltage == "12.0"

    voltage = mocker.send(":INSTR:CHANNEL2:VOLT?")
    assert voltage == "13.4"


def test_two_of_same_kind():

    mocker1 = Mocker1()
    mocker2 = Mocker1()

    mocker1.send(":INSTR:CHANNEL1:VOLT 12")
    voltage = mocker1.send(":INSTR:CHANNEL1:VOLT?")
    assert voltage == "12.0"

    mocker2.send(":INSTR:CHANNEL1:VOLT 13.4")
    voltage = mocker2.send(":INSTR:CHANNEL1:VOLT?")
    assert voltage == "13.4"


def test_one_of_each_kind():
    mocker1 = Mocker1()
    mocker2 = Mocker2()

    mocker1.send(":INSTR:CHANNEL1:VOLT 12")
    voltage = mocker1.send(":INSTR:CHANNEL1:VOLT?")
    assert voltage == "12.0"

    mocker2.send(":INSTR:CHANNEL1:VOLT 13.4")
    voltage = mocker2.send(":INSTR:CHANNEL1:VOLT?")
    assert voltage == "26.8"
