from aiogram.fsm.state import State, StatesGroup


class LocationFlow(StatesGroup):
    waiting_for_location = State()


class PreparePrayFlow(StatesGroup):
    waiting_for_minutes = State()


class JumaTimeFlow(StatesGroup):
    waiting_for_time = State()
