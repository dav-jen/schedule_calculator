import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Dict, List, Tuple
import requests
import pandas as pd
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Parent:
    name: str
    addresses: List[Tuple[str, str]]  # List of (concise_name, full_address)
    availability: Dict[str, Tuple[time, time]]  # Day of week to (start_time, end_time)

@dataclass
class School:
    name: str  # Full name
    concise_name: str  # Abbreviated name
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

# Utils
class GoogleMapsClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise ValueError("Google Maps API key not found in .env file")
        self.journey_times_cache = {}
        logger.info("GoogleMapsClient initialized successfully")

    def get_journey_time(self, origin: str, destination: str) -> int:
        """Get journey time between two locations using Google Maps API."""
        try:
            cache_key = (origin, destination)
            if cache_key in self.journey_times_cache:
                logger.debug(f"Using cached journey time for {cache_key}")
                return self.journey_times_cache[cache_key]

            logger.debug(f"Fetching journey time from {origin} to {destination}")

            params = {
                'origins': origin,
                'destinations': destination,
                'key': self.api_key,
                'mode': 'driving',
                'departure_time': 'now',
                'traffic_model': 'best_guess'
            }

            url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            response = requests.get(url, params=params)
            data = response.json()

            if (data.get('status') == 'OK' and
                data.get('rows') and
                data['rows'][0].get('elements') and
                data['rows'][0]['elements'][0].get('status') == 'OK' and
                'duration_in_traffic' in data['rows'][0]['elements'][0]):

                duration = data['rows'][0]['elements'][0]['duration_in_traffic']['value']
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

class JourneyCalculator:
    def __init__(self):
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
                addresses=[
                    ("Islingword Rd", "39 Islingword Road, Brighton & Hove, East Sussex BN2 9SF")
                ],
                availability=weekday_availability
            ),
            "Hannah": Parent(
                name="Hannah",
                addresses=[
                    ("Chandlers Ford", "12 The Maples, Chandler's Ford, Eastleigh, Hampshire SO53 1DZ"),
                    ("Petersfield", "Petersfield, UK")
                ],
                availability=weekday_availability
            )
        }

    def _initialize_schools(self) -> Dict[str, School]:
        return {
            "St Luke's": School(
                name="St Luke's",
                concise_name="St Luke's",
                address="Queens Park Rise, Brighton, BN2 9ZF",
                normal_start=time(8, 40),
                normal_end=time(15, 15),
                breakfast_club_start=time(8, 0),
                aftercare_end=time(17, 30)
            ),
            "Lindfield": School(
                name="Lindfield Primary Academy",
                concise_name="Lindfield PA",
                address="School Lane, Lindfield, Haywards Heath, RH16 2DX",
                normal_start=time(8, 45),
                normal_end=time(15, 15),
                breakfast_club_start=time(7, 0),
                aftercare_end=time(18, 30)
            ),
            "Bedales": School(
                name="Bedales",
                concise_name="Bedales",
                address="Alton Road, Petersfield, GU32 2DR",
                normal_start=time(8, 30),
                normal_end=time(15, 30),
                breakfast_club_start=time(8, 0),
                aftercare_end=time(17, 25)
            )
        }

    def _initialize_children(self) -> Dict[str, Child]:
        return {
            "Fenella": Child(
                name="Fenella",
                schools=[
                    self.schools["Lindfield"],
                    self.schools["St Luke's"]
                ]
            ),
            "Ruby": Child(
                name="Ruby",
                schools=[self.schools["Lindfield"]]
            ),
            "Teddy": Child(
                name="Teddy",
                schools=[self.schools["Bedales"]]
            )
        }

    def calculate_permutations(self):
        results = []
        scenarios = []

        # For David
        for david_address in self.parents["David"].addresses:
            for fenella_school in self.children["Fenella"].schools:
                # David has Fenella and Ruby
                scenario = {
                    'Parent': 'David',
                    'Parent Address': david_address,
                    'Children': ['Fenella', 'Ruby'],
                    'Schools': [fenella_school, self.children["Ruby"].schools[0]],
                }
                scenarios.append(scenario)
                # David has just Fenella
                scenario = {
                    'Parent': 'David',
                    'Parent Address': david_address,
                    'Children': ['Fenella'],
                    'Schools': [fenella_school],
                }
                scenarios.append(scenario)

        # For Hannah
        for hannah_address in self.parents["Hannah"].addresses:
            for fenella_school in self.children["Fenella"].schools:
                # Hannah has Fenella and Teddy
                scenario = {
                    'Parent': 'Hannah',
                    'Parent Address': hannah_address,
                    'Children': ['Fenella', 'Teddy'],
                    'Schools': [fenella_school, self.children["Teddy"].schools[0]],
                }
                scenarios.append(scenario)
                # Hannah has just Fenella
                scenario = {
                    'Parent': 'Hannah',
                    'Parent Address': hannah_address,
                    'Children': ['Fenella'],
                    'Schools': [fenella_school],
                }
                scenarios.append(scenario)

        # Calculate journey times for each scenario
        for scenario in scenarios:
            for time_of_day in ['Drop-off', 'Pick-up']:
                result = self._calculate_journey(scenario, time_of_day)
                results.append(result)

        return results

    def _calculate_journey(self, scenario, time_of_day):
        parent = scenario['Parent']
        parent_address_name, parent_address_full = scenario['Parent Address']
        children = scenario['Children']
        schools = scenario['Schools']

        # Build journey sequence
        journey_sequence = []
        journey_sequence.append(('Home', parent_address_full))
        for school in schools:
            journey_sequence.append((school.concise_name, school.address))
        journey_sequence.append(('Return Home', parent_address_full))

        # Calculate journey times between each point
        total_journey_time = 0
        journey_details = []
        for i in range(len(journey_sequence) - 1):
            start_label, start_addr = journey_sequence[i]
            end_label, end_addr = journey_sequence[i + 1]
            journey_time = self.maps_client.get_journey_time(start_addr, end_addr)
            total_journey_time += journey_time
            journey_details.append({
                'From': start_label,
                'To': end_label,
                'Journey Time (mins)': journey_time
            })

        # Build result
        scenario_name = f"{parent} Home ({parent_address_name}) > " + " + ".join([s.concise_name for s in schools]) + f" {time_of_day}"
        result = {
            'Scenario Name': scenario_name,
            'Parent': parent,
            'Parent Address': parent_address_name,
            'Children': ', '.join(children),
            'Fenella School': schools[0].concise_name,
            'Schools': ', '.join([s.concise_name for s in schools]),
            'Time of Day': time_of_day,
            'Total Journey Time (mins)': total_journey_time,
            'Journey Details': journey_details
        }

        logger.info(f"Calculated {time_of_day} journey for scenario: {result['Scenario Name']}")
        return result

    def output_table(self, results):
        # Convert results to DataFrame
        df = pd.DataFrame(results)
        
        # Order by Fenella's school selection
        df['Fenella School Order'] = df['Fenella School'].map({'Lindfield PA': 1, "St Luke's": 2})
        
        # Order by Parent Address
        address_order = {
            ('Hannah', 'Chandlers Ford'): 1,
            ('Hannah', 'Petersfield'): 2,
            ('David', 'Islingword Rd'): 3
        }
        df['Parent Address Order'] = df.apply(lambda x: address_order.get((x['Parent'], x['Parent Address']), 4), axis=1)
        
        # Sort DataFrame
        df = df.sort_values(['Fenella School Order', 'Parent Address Order'])
        
        # Select columns to display
        display_columns = ['Scenario Name', 'Total Journey Time (mins)', 'Time of Day', 'Children']
        
        # Print the table
        print("\nPossible Journey Scenarios:")
        print("-" * 100)
        header = f"{'Scenario Name':<50}{'Total Time (mins)':<20}{'Time of Day':<15}{'Children':<20}"
        print(header)
        print("-" * 100)
        for _, row in df.iterrows():
            row_str = f"{row['Scenario Name']:<50}{row['Total Journey Time (mins)']:<20}{row['Time of Day']:<15}{row['Children']:<20}"
            print(row_str)
        print("-" * 100)
        
        # Save DataFrame to CSV
        df.to_csv('journey_scenarios.csv', index=False)

    def run(self):
        results = self.calculate_permutations()
        self.output_table(results)

def main():
    try:
        calculator = JourneyCalculator()
        calculator.run()
    except Exception as e:
        logger.error(f"Error running journey calculator: {str(e)}")
        raise

if __name__ == "__main__":
    main() 