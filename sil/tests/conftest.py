"""Shared pytest fixtures for UC-05."""
import pytest

from sil.firmware.mc import MotorControllerFW
from sil.harness import Harness
from sil.nodes import RiderInputModel, SimulatedHmiNode
from sil.plant import VehicleDynamics
from sil.stub import SensorGpioStub


@pytest.fixture
def stub():
    return SensorGpioStub()


@pytest.fixture
def rider(stub):
    return RiderInputModel(stub=stub)


@pytest.fixture
def hmi():
    return SimulatedHmiNode()


@pytest.fixture
def plant():
    return VehicleDynamics()


@pytest.fixture
def fw():
    return MotorControllerFW()


@pytest.fixture
def harness(fw, rider, stub, plant, hmi):
    return Harness(fw=fw, rider=rider, stub=stub, plant=plant, hmi=hmi)
