from collections import defaultdict
from visa_mock.base.base_mocker import BaseMocker, scpi


class Mocker1(BaseMocker):
    """
    A mocker class mocking a multi channel voltage source.
    Voltages are zero by default
    """

    def __init__(self) -> None:
        self._voltage = defaultdict(lambda: 0.0)

    @scpi(r":INSTR:CHANNEL(.*):VOLT (.*)")
    def _set_voltage(self, channel: int, value: float) -> None:
        self._voltage[channel] = value

    @scpi(r":INSTR:CHANNEL(.*):VOLT\?")
    def _get_voltage(self, channel: int) -> float:
        return self._voltage[channel]


class Mocker2(BaseMocker):
    """
    A mocker class mocking a multi channel voltage source.
    Voltages are zero by default
    """

    def __init__(self):
        self._voltage = defaultdict(lambda: 0.0)

    @scpi(r":INSTR:CHANNEL(.*):VOLT (.*)")
    def _set_voltage(self, channel: int, value: float) -> None:
        self._voltage[channel] = value

    @scpi(r":INSTR:CHANNEL(.*):VOLT\?")
    def _get_voltage(self, channel: int) -> float:
        return 2 * self._voltage[channel]


resources = {
    "MOCK0::mock1::INSTR": Mocker1(),
    "MOCK0::mock2::INSTR": Mocker2(),
}
