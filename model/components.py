from mesa import Agent
from enum import Enum
import random


# ---------------------------------------------------------------
class Infra(Agent):
    """
    Base class for all infrastructure components

    Attributes
    __________
    vehicle_count : int
        the number of vehicles that are currently in/on (or totally generated/removed by)
        this infrastructure component

    length : float
        the length in meters
    ...

    """

    def __init__(self, unique_id, model, length=0,
                 name='Unknown', road_name='Unknown'):
        super().__init__(unique_id, model)
        self.length = length
        self.name = name
        self.road_name = road_name
        self.vehicle_count = 0

    def step(self):
        pass

    def __str__(self):
        return type(self).__name__ + str(self.unique_id)


# ---------------------------------------------------------------
class Bridge(Infra):
    """
    Creates delay time

    Attributes
    __________
    condition:
        condition of the bridge

    delay_time: int
        the delay (in ticks) caused by this bridge
    ...

    """

    def __init__(self, unique_id, model, length=0,
                 name='Unknown', road_name='Unknown', condition='Unknown'):
        super().__init__(unique_id, model, length, name, road_name)

        self.condition = condition
        self.collapse_chance = self.model.collapse_dict[self.condition]
        self.collapsed = False
        #self.in_repair = False

        # TODO
        self.delay_time = 0
        # print(self.delay_time)

    # TODO
    def get_delay_time(self):
        if self.collapsed:
            if self.length > self.model.long_length_threshold:
                self.delay_time = self.random.triangular(60, 240, 120)
            elif self.length > self.model.medium_length_threshold:
                self.delay_time = self.random.uniform(45, 90)
            elif self.length > self.model.short_length_threshold:
                self.delay_time = self.random.uniform(15, 60)
            else:
                self.delay_time = self.random.uniform(10, 20)
        else:
            self.delay_time = 0
        return self.delay_time

    # def get_repair_time(self):
    #     self.repair_time = 24 * 60
    #     return self.repair_time

    def get_name(self):
        """
        Retrieve bridges name to choose between L/R bridge
        """
        return self.name

    # def change_condition(self, new_condition: str):
    #     """Change the condition of a bridge to another condition"""
    #     self.condition = new_condition
    #     return self.condition

    def collapse(self):
        """A bridge collapses according to its chance of collapsing."""
        if not self.collapsed and self.collapse_chance > self.random.random():
            self.collapsed = True
            self.model.collapsed_dict[self.condition] += 1
        else:
            pass
        return

    def step(self):
        # first, the bridge has a chance to collapse. This is done in the collapse function.
        self.collapse()

# ---------------------------------------------------------------
class Link(Infra):
    pass


# ---------------------------------------------------------------
class Intersection(Infra):
    pass


# ---------------------------------------------------------------
class Sink(Infra):
    """
    Sink removes vehicles

    Attributes
    __________
    vehicle_removed_toggle: bool
        toggles each time when a vehicle is removed
    ...

    """
    vehicle_removed_toggle = False

    def remove(self, vehicle):
        self.model.schedule.remove(vehicle)
        self.vehicle_removed_toggle = not self.vehicle_removed_toggle
        #print(str(self) + ' REMOVE ' + str(vehicle))


# ---------------------------------------------------------------

class Source(Infra):
    """
    Source generates vehicles

    Class Attributes:
    -----------------
    truck_counter : int
        the number of trucks generated by ALL sources. Used as Truck ID!

    Attributes
    __________
    generation_frequency: int
        the frequency (the number of ticks) by which a truck is generated

    vehicle_generated_flag: bool
        True when a Truck is generated in this tick; False otherwise
    ...

    """

    truck_counter = 0
    generation_frequency = 5
    vehicle_generated_flag = False

    def step(self):
        if self.model.schedule.steps % self.generation_frequency == 0:
            self.generate_truck()
        else:
            self.vehicle_generated_flag = False

    def generate_truck(self):
        """
        Generates a truck, sets its path, increases the global and local counters
        """
        try:
            agent = Vehicle('Truck' + str(Source.truck_counter), self.model, self)
            if agent:
                self.model.schedule.add(agent)
                agent.set_path()
                Source.truck_counter += 1
                self.vehicle_count += 1
                self.vehicle_generated_flag = True
                #print(str(self) + " GENERATE " + str(agent))
        except Exception as e:
            print("Oops!", e.__class__, "occurred.")


# ---------------------------------------------------------------
class SourceSink(Source, Sink):
    """
    Generates and removes trucks
    """

    pass



# ---------------------------------------------------------------
class Vehicle(Agent):
    """

    Attributes
    __________
    speed: float
        speed in meter per minute (m/min)

    step_time: int
        the number of minutes (or seconds) a tick represents
        Used as a base to change unites

    state: Enum (DRIVE | WAIT)
        state of the vehicle

    location: Infra
        reference to the Infra where the vehicle is located

    location_offset: float
        the location offset in meters relative to the starting point of
        the Infra, which has a certain length
        i.e. location_offset < length

    path_ids: Series
        the whole path (origin and destination) where the vehicle shall drive
        It consists the Infras' uniques IDs in a sequential order

    location_index: int
        a pointer to the current Infra in "path_ids" (above)
        i.e. the id of self.location is self.path_ids[self.location_index]

    waiting_time: int
        the time the vehicle needs to wait

    generated_at_step: int
        the timestamp (number of ticks) that the vehicle is generated

    removed_at_step: int
        the timestamp (number of ticks) that the vehicle is removed
    ...

    """

    # 48 km/h translated into meter per min
    speed = 48 * 1000 / 60
    # One tick represents 1 minute
    step_time = 1

    class State(Enum):
        DRIVE = 1
        WAIT = 2

    def __init__(self, unique_id, model, generated_by,
                 location_offset=0, path_ids=None):
        super().__init__(unique_id, model)
        self.generated_by = generated_by
        self.generated_at_step = model.schedule.steps
        self.location = generated_by
        self.location_offset = location_offset
        self.pos = generated_by.pos
        self.path_ids = path_ids
        # default values
        self.state = Vehicle.State.DRIVE
        self.location_index = 0
        self.waiting_time = 0
        self.waited_at = None
        self.removed_at_step = None
        # set an attribute 'next_infra_name' to distinguish the L and R bridge
        self.next_infra_name = None
        self.driving_time = 0
        self.travel_distance = 0

    def __str__(self):
        return "Vehicle" + str(self.unique_id) + \
               " +" + str(self.generated_at_step) + " -" + str(self.removed_at_step) + \
               " " + str(self.state) + '(' + str(self.waiting_time) + ') ' + \
               str(self.location) + '(' + str(self.location.vehicle_count) + ') ' + str(self.location_offset)

    def set_path(self):
        """
        Set the origin destination path of the vehicle
        """
        random_route = self.model.get_route(self.generated_by.unique_id)
        self.path_ids = random_route[0]
        self.travel_distance = random_route[1]
        # print("path:", self.path_ids, "distance", self.travel_distance)
    def step(self):
        """
        Vehicle waits or drives at each step
        """
        if self.state == Vehicle.State.WAIT:
            self.waiting_time = max(self.waiting_time - 1, 0)
            if self.waiting_time == 0:
                self.waited_at = self.location
                self.state = Vehicle.State.DRIVE

        if self.state == Vehicle.State.DRIVE:
            self.drive()

        """
        To print the vehicle trajectory at each step
        """
        #print(self)

    def drive(self):

        # the distance that vehicle drives in a tick
        # speed is global now: can change to instance object when individual speed is needed
        distance = Vehicle.speed * Vehicle.step_time
        distance_rest = self.location_offset + distance - self.location.length

        if distance_rest > 0:
            # go to the next object
            self.drive_to_next(distance_rest)
        else:
            # remain on the same object
            self.location_offset += distance

    def drive_to_next(self, distance):
        """
        vehicle shall move to the next object with the given distance
        """

        self.location_index += 1
        next_id = self.path_ids[self.location_index]
        next_infra = self.model.schedule._agents[next_id]  # Access to protected member _agents

        if isinstance(next_infra, Sink):
            # arrive at the sink
            self.arrive_at_next(next_infra, 0)
            self.removed_at_step = self.model.schedule.steps
            self.driving_time = self.removed_at_step - self.generated_at_step
            self.net_speed = (self.travel_distance / 1000) / (self.driving_time / 60)
            self.model.driving_time_of_trucks.append(self.driving_time)
            self.model.speed_of_trucks.append(self.net_speed)
            # print(self.net_speed, self.travel_distance, self.driving_time, self.generated_at_step, self.removed_at_step)
            self.location.remove(self)
            return
        elif isinstance(next_infra, Bridge):
            # Get bridge name to check for L and R side
            bridge_name = next_infra.get_name()
            # Get location of current object
            prev_x_loc = self.location.pos[0]
            # Get location of next objec
            next_x_loc = next_infra.pos[0]
            # Check if the bridge is L and if the next location is more east than the current location
            if bridge_name[-2:] == '(L' and prev_x_loc < next_x_loc:
                # Skip L bridge
                self.drive_to_next(distance)
            # Check if the bridge is R and if the next location is more west than the current location
            elif bridge_name[-2:] == '(R' and prev_x_loc > next_x_loc:
                # Skip R bridge
                self.drive_to_next(distance)
            else:
                # If this bridge shouldn't be skipped, continue
                pass
            self.waiting_time = next_infra.get_delay_time()
            if self.waiting_time > 0:
                # arrive at the bridge and wait
                self.arrive_at_next(next_infra, 0)
                self.state = Vehicle.State.WAIT
                return
            # else, continue driving

        if next_infra.length > distance:
            # stay on this object:
            self.arrive_at_next(next_infra, distance)
        else:
            # drive to next object:
            self.drive_to_next(distance - next_infra.length)

    def arrive_at_next(self, next_infra, location_offset):
        """
        Arrive at next_infra with the given location_offset
        """
        self.location.vehicle_count -= 1
        self.location = next_infra
        self.location_offset = location_offset
        self.location.vehicle_count += 1

# EOF -----------------------------------------------------------
