# pyvisa_mock

pyvisa-mock aims to provide similar functionality as [pyvisa-sim](https://pyvisa-sim.readthedocs.io/en/latest/), however, instead of a static YAML file providing query/response items, a dynamic python object is responsible for handling queries. 

## Example

```python
from visa_mock.base.base_mocker import BaseMocker, scpi
from visa_mock.base.register import register_resource

class Mocker(BaseMocker):
    """
    A mocker class mocking a multi channel voltage source.
    Voltages are zero by default
    """

    def __init__(self):
        self._voltage = defaultdict(lambda: 0)

    @scpi("\*IDN\?")
    def idn(self): 
        """
        'vendor', 'model', 'serial', 'firmware'
        """
        return "Mocker,testing,00000,0.01"

    # Lets define handler functions. Notice how we can be 
    # lazy in our regular expressions (using ".*"). The 
    # typehints will be used to cast strings to the 
    # required types
    
    @scpi(r":INSTR:CHANNEL(.*):VOLT (.*)")
    def _set_voltage(self, channel: int, value: float) -> None:
        self._voltage[channel] = value

    @scpi(r":INSTR:CHANNEL(.*):VOLT\?")
    def _get_voltage(self, channel: int) -> float:
        return self._voltage[channel]
        
 
register_resource("MOCK0::mock1::INSTR", Mocker())

rc = ResourceManager(visa_library="@mock")
res = rc.open_resource("MOCK0::mock1::INSTR")
res.write(":INSTR:CHANNEL1:VOLT 2.3")
reply = res.query(":INSTR:CHANNEL1:VOLT?")  # This should return '2.3'
```
