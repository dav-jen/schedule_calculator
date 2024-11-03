# Combined implementation of all src files with requested modifications

from dataclasses import dataclass, field
from datetime import datetime, timedelta, date, time
import itertools
from typing import Dict, List, Tuple
import logging
import os
import requests
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models
@dataclass
class Parent:
    name: str
    address: str
    availability: Dict[str, Tuple[time, time]]  # Day of week to (start_time, end_time)

@dataclass
class School:
    name: str
    address: str
    normal_start: time
    normal_end: time
    breakfast_club_start: time
    aftercare_end: time
    source: str = ""

@dataclass
class Child:
    name: str
    schools: List[School]  # Allow multiple school options
    custody_schedule: Dict[int, Dict[int, Dict[str, Parent]]]  # Week -> Day -> {'AM': Parent, 'PM': Parent}
    overnight_schedule: Dict[int, Dict[int, Parent]] = field(default_factory=dict)  # Week -> Day -> Parent

@dataclass
class ScheduleSlot:
    child: Child
    parent: Parent
    is_dropoff: bool
    time: datetime
    duration: int  # Duration in minutes for the drop-off/pick-up period

@dataclass
class DaySchedule:
    date: date
    slots: List[ScheduleSlot]
    total_journey_time: int

@dataclass
class TwoWeekSchedule:
    schedules: List[DaySchedule]
    total_journey_time: int

# Utils
class GoogleMapsClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise ValueError("Google Maps API key not found in .env file")
        self.journey_times_cache = {}
        logger.info("GoogleMapsClient initialized successfully")

    def get_journey_time(self, origin: str, destination: str, arrival_time: datetime = None) -> int:
        """Get journey time between two locations using Google Maps API."""
        try:
            cache_key = (origin, destination, arrival_time.isoformat() if arrival_time else None)
            if cache_key in self.journey_times_cache:
                logger.debug(f"Using cached journey time for {cache_key}")
                return self.journey_times_cache[cache_key]

            logger.debug(f"Fetching journey time from {origin} to {destination}")

            params = {
                'origins': origin,
                'destinations': destination,
                'key': self.api_key,
                'mode': 'driving',
                'traffic_model': 'best_guess',
                'departure_time': 'now'
            }

            if arrival_time:
                params['arrival_time'] = int(arrival_time.timestamp())

            url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            response = requests.get(url, params=params)
            data = response.json()

            if (data.get('status') == 'OK' and 
                data.get('rows') and 
                data['rows'][0].get('elements') and 
                data['rows'][0]['elements'][0].get('status') == 'OK' and
                'duration' in data['rows'][0]['elements'][0]):
                
                duration = data['rows'][0]['elements'][0]['duration']['value']
                minutes = duration // 60
                self.journey_times_cache[cache_key] = minutes
                logger.debug(f"Journey time: {minutes} minutes")
                return minutes
            else:
                logger.error(f"Invalid response format or error status: {data}")
                return 60  # Default to 60 minutes

        except Exception as e:
            logger.error(f"Error in get_journey_time: {str(e)}")
            return 60  # Default to 60 minutes in case of any error

# Optimizer
class ScheduleOptimizer:
    MAX_TRAVEL_TIME_PER_DAY = 240  # Increased to allow for the additional 15-minute periods
    MAX_TRAVEL_TIME_PER_WEEK = 1200  # Increased accordingly

    def __init__(self):
        # Load environment variables
        load_dotenv()
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise ValueError("Google Maps API key not found in environment variables")
        logger.info("API key loaded successfully")
        
        self.maps_client = GoogleMapsClient()
        self.parents = self._initialize_parents()
        self.schools = self._initialize_schools()
        self.children = self._initialize_children()
        logger.info("Initialization complete")

    def _initialize_parents(self) -> Dict[str, Parent]:
        weekday_availability = {
            day: (time(7, 0), time(19, 0))
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        }
        
        return {
            "David": Parent(
                name="David",
                address="Brighton, UK",
                availability=weekday_availability
            ),
            "Hannah": Parent(
                name="Hannah",
                address="Petworth, UK",  # Updated address
                availability=weekday_availability
            ),
            "Fi": Parent(
                name="Fi",
                address="Brighton, UK",
                availability=weekday_availability
            ),
            "Chris": Parent(
                name="Chris",
                address="Winchester, UK",
                availability=weekday_availability
            )
        }

    def _initialize_schools(self) -> Dict[str, School]:
        return {
            "St Luke's": School(
                name="St Luke's",
                address="Queens Park Rise, Brighton, BN2 9ZF",
                normal_start=time(8, 40),
                normal_end=time(15, 15),
                breakfast_club_start=time(8, 0),
                aftercare_end=time(17, 30),
                source="Information Regarding Drop-off and Collection"
            ),
            "Elm Grove": School(
                name="Elm Grove",
                address="Elm Grove, Brighton, BN2 3ES",
                normal_start=time(8, 50),
                normal_end=time(15, 15),
                breakfast_club_start=time(8, 0),
                aftercare_end=time(17, 30),
                source="School Day"
            ),
            "Lindfield": School(
                name="Lindfield",
                address="School Lane, Lindfield, Haywards Heath, RH16 2DX",
                normal_start=time(8, 45),
                normal_end=time(15, 15),
                breakfast_club_start=time(7, 0),
                aftercare_end=time(18, 30),
                source="Key Dates and Times"
            ),
            "Bedales": School(
                name="Bedales",
                address="Alton Road, Petersfield, GU32 2DR",
                normal_start=time(8, 30),
                normal_end=time(15, 30),
                breakfast_club_start=time(8, 0),
                aftercare_end=time(17, 25),
                source="Life at Bedales Pre-prep"
            )
        }

    def _initialize_children(self) -> Dict[str, Child]:
        return {
            "Fenella": Child(
                name="Fenella",
                schools=[
                    self.schools["St Luke's"],
                    self.schools["Elm Grove"],
                    self.schools["Lindfield"]
                ],
                custody_schedule=self._get_fenella_schedule()
            ),
            "Ruby": Child(
                name="Ruby",
                schools=[self.schools["Lindfield"]],
                custody_schedule=self._get_ruby_schedule()
            ),
            "Teddy": Child(
                name="Teddy",
                schools=[self.schools["Bedales"]],
                custody_schedule=self._get_teddy_schedule()
            )
        }

    def _get_fenella_schedule(self) -> Dict:
        """Create Fenella's custody schedule based on the specified constraints."""
        fenella_schedule = {}
        for week in [1, 2]:
            fenella_schedule[week] = {}
            for day in range(5):  # Monday to Friday
                if day in [0, 1]:  # Monday & Tuesday
                    am_parent = pm_parent = self.parents["David"]
                elif day in [2, 3]:  # Wednesday & Thursday
                    am_parent = pm_parent = self.parents["Hannah"]
                else:  # Friday
                    if week == 1:
                        am_parent = pm_parent = self.parents["Hannah"]  # Align with Teddy
                    else:
                        am_parent = pm_parent = self.parents["David"]  # Align with Ruby
                fenella_schedule[week][day] = {
                    'AM': am_parent,
                    'PM': pm_parent,
                    'Overnight': pm_parent  # Assume overnight with PM parent
                }
        return fenella_schedule

    def _get_ruby_schedule(self) -> Dict:
        """Create Ruby's custody schedule."""
        ruby_schedule = {}
        for week in [1, 2]:
            ruby_schedule[week] = {}
            for day in range(5):
                if week == 1:
                    am_parent = pm_parent = self.parents["Fi"]
                else:
                    am_parent = pm_parent = self.parents["David"]
                ruby_schedule[week][day] = {
                    'AM': am_parent,
                    'PM': pm_parent,
                    'Overnight': pm_parent
                }
        return ruby_schedule

    def _get_teddy_schedule(self) -> Dict:
        """Create Teddy's custody schedule."""
        teddy_schedule = {}
        for week in [1, 2]:
            teddy_schedule[week] = {}
            for day in range(5):
                if week == 1:
                    am_parent = pm_parent = self.parents["Hannah"]
                else:
                    am_parent = pm_parent = self.parents["Chris"]
                teddy_schedule[week][day] = {
                    'AM': am_parent,
                    'PM': pm_parent,
                    'Overnight': pm_parent
                }
        return teddy_schedule

    def calculate_journey_time(self, start_location: str, end_location: str, arrival_time: datetime = None) -> int:
        return self.maps_client.get_journey_time(start_location, end_location, arrival_time)

    def generate_possible_day_schedules(self, date_obj: date, week_number: int, day_of_week: int) -> List[DaySchedule]:
        """Generate possible schedules for a given day considering all children's schedules."""
        logger.info(f"Generating schedules for {date_obj}, Week {week_number}, Day {day_of_week}")
        
        possible_schedules = []
        fenella_custody = self.children["Fenella"].custody_schedule[week_number][day_of_week]
        ruby_custody = self.children["Ruby"].custody_schedule[week_number][day_of_week]
        teddy_custody = self.children["Teddy"].custody_schedule[week_number][day_of_week]
        
        # Generate schedules for each of Fenella's school options
        for school in self.children["Fenella"].schools:
            slots = []
            
            # Fenella's slots
            fenella = Child(name="Fenella", schools=[school], custody_schedule={})
            fenella_slot_am = ScheduleSlot(
                child=fenella,
                parent=fenella_custody["AM"],
                is_dropoff=True,
                time=None,
                duration=15  # 15 minutes for drop-off
            )
            fenella_slot_pm = ScheduleSlot(
                child=fenella,
                parent=fenella_custody["PM"],
                is_dropoff=False,
                time=None,
                duration=15  # 15 minutes for pick-up
            )
            slots.extend([fenella_slot_am, fenella_slot_pm])
            
            # Ruby's slots (fixed)
            ruby = self.children["Ruby"]
            ruby_slot_am = ScheduleSlot(
                child=ruby,
                parent=ruby_custody["AM"],
                is_dropoff=True,
                time=None,
                duration=15
            )
            ruby_slot_pm = ScheduleSlot(
                child=ruby,
                parent=ruby_custody["PM"],
                is_dropoff=False,
                time=None,
                duration=15
            )
            slots.extend([ruby_slot_am, ruby_slot_pm])
            
            # Teddy's slots (fixed)
            teddy = self.children["Teddy"]
            teddy_slot_am = ScheduleSlot(
                child=teddy,
                parent=teddy_custody["AM"],
                is_dropoff=True,
                time=None,
                duration=15
            )
            teddy_slot_pm = ScheduleSlot(
                child=teddy,
                parent=teddy_custody["PM"],
                is_dropoff=False,
                time=None,
                duration=15
            )
            slots.extend([teddy_slot_am, teddy_slot_pm])
            
            # Calculate times and journey durations
            slots_with_times = self._calculate_slot_times(slots, date_obj)
            total_journey_time = self._calculate_total_journey_time(slots_with_times)
            
            schedule = DaySchedule(
                date=date_obj,
                slots=slots_with_times,
                total_journey_time=total_journey_time
            )
            possible_schedules.append(schedule)
        
        # Select the schedule with the minimal total journey time
        if possible_schedules:
            optimal_schedule = min(possible_schedules, key=lambda s: s.total_journey_time)
            logger.info(f"Selected optimal schedule for {date_obj} with journey time {optimal_schedule.total_journey_time} minutes")
            return [optimal_schedule]
        else:
            logger.warning(f"No schedules generated for {date_obj}")
            return []

    def _calculate_slot_times(self, slots: List[ScheduleSlot], date_obj: date) -> List[ScheduleSlot]:
        """Calculate exact times for each slot based on school times and travel."""
        slots_with_times = []
        
        # Sort slots by is_dropoff and school start/end times
        dropoff_slots = [slot for slot in slots if slot.is_dropoff]
        pickup_slots = [slot for slot in slots if not slot.is_dropoff]
        
        # Calculate times for drop-off slots
        for slot in dropoff_slots:
            school_start_time = datetime.combine(date_obj, slot.child.schools[0].normal_start)
            dropoff_start_time = school_start_time - timedelta(minutes=15)  # Drop-off starts 15 minutes before school starts
            slot.time = dropoff_start_time
            slots_with_times.append(slot)
        
        # Calculate times for pick-up slots
        for slot in pickup_slots:
            school_end_time = datetime.combine(date_obj, slot.child.schools[0].normal_end)
            pickup_start_time = school_end_time - timedelta(minutes=5)  # Pick-up starts 5 minutes before school ends
            slot.time = pickup_start_time
            slots_with_times.append(slot)
        
        return slots_with_times

    def _calculate_total_journey_time(self, slots: List[ScheduleSlot]) -> int:
        total_time = 0
        slots = sorted(slots, key=lambda x: x.time)
        
        for i in range(len(slots) - 1):
            start_slot = slots[i]
            end_slot = slots[i + 1]
            start_address = start_slot.child.schools[0].address if start_slot.is_dropoff else start_slot.parent.address
            end_address = end_slot.child.schools[0].address if end_slot.is_dropoff else end_slot.parent.address
            travel_time = self.calculate_journey_time(
                start_location=start_address,
                end_location=end_address,
                arrival_time=end_slot.time
            )
            total_time += travel_time
            logger.debug(f"Journey from {start_address} to {end_address}: {travel_time} minutes")
        
        return total_time

    def generate_possible_two_week_schedules(self) -> List[TwoWeekSchedule]:
        """Generate all possible two-week schedules within constraints."""
        logger.info("Starting two-week schedule generation")
        
        possible_two_week_schedules = []
        day_schedules = []
        
        for week in [1, 2]:
            for day in range(5):
                date_obj = datetime.now().date() + timedelta(days=(week - 1) * 7 + day)
                day_schedule_list = self.generate_possible_day_schedules(date_obj, week, day)
                if day_schedule_list:
                    day_schedule = day_schedule_list[0]
                    day_schedules.append(day_schedule)
                else:
                    logger.error(f"No valid schedule for {date_obj}")
                    return []
        
        total_journey_time = sum(day.total_journey_time for day in day_schedules)
        
        two_week_schedule = TwoWeekSchedule(
            schedules=day_schedules,
            total_journey_time=total_journey_time
        )
        possible_two_week_schedules.append(two_week_schedule)
        logger.info("Generated the fixed two-week schedule")
        return possible_two_week_schedules

    def output_two_week_schedule(self, two_week_schedule: TwoWeekSchedule):
        """Output the two-week schedule in a concise table format."""
        print("\nOptimal Two-Week Schedule")
        print("=" * 70)
        print(f"Total Journey Time: {two_week_schedule.total_journey_time} minutes")
        print("=" * 70)
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        week_days = ['Week 1', 'Week 2']
        
        # Prepare the schedule table
        schedule_table = {
            'Date': [],
            'Fenella': [],
            'Ruby': [],
            'Teddy': []
        }
        
        for week_number in [1, 2]:
            for day_index in range(5):
                date_obj = datetime.now().date() + timedelta(days=(week_number - 1) * 7 + day_index)
                day_name = day_names[day_index]
                day_schedule = two_week_schedule.schedules[(week_number - 1) * 5 + day_index]
                schedule_table['Date'].append(f"{week_days[week_number - 1]} {day_name}")
                
                # Fenella's overnight parent
                fenella_overnight = self.children["Fenella"].custody_schedule[week_number][day_index]['Overnight'].name
                schedule_table['Fenella'].append(fenella_overnight)
                
                # Ruby's overnight parent
                ruby_overnight = self.children["Ruby"].custody_schedule[week_number][day_index]['Overnight'].name
                schedule_table['Ruby'].append(ruby_overnight)
                
                # Teddy's overnight parent
                teddy_overnight = self.children["Teddy"].custody_schedule[week_number][day_index]['Overnight'].name
                schedule_table['Teddy'].append(teddy_overnight)
        
        # Print the schedule table
        print("\nSchedule Overview")
        print("-" * 70)
        print(f"{'Date':<15}{'Fenella':<10}{'Ruby':<10}{'Teddy':<10}")
        for i in range(len(schedule_table['Date'])):
            print(f"{schedule_table['Date'][i]:<15}{schedule_table['Fenella'][i]:<10}{schedule_table['Ruby'][i]:<10}{schedule_table['Teddy'][i]:<10}")
        print("-" * 70)

    def run(self):
        possible_two_week_schedules = self.generate_possible_two_week_schedules()
        if not possible_two_week_schedules:
            print("No feasible two-week schedules found.")
            return

        optimal_schedule = possible_two_week_schedules[0]
        self.output_two_week_schedule(optimal_schedule)

# Main execution
def main():
    try:
        optimizer = ScheduleOptimizer()
        optimizer.run()
    except Exception as e:
        logger.error(f"Error running optimizer: {str(e)}")
        raise

if __name__ == "__main__":
    main()