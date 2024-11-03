# Schedule Calculator

**Version:** 0.1.0

## Description

**Schedule Calculator** is a Python-based application designed to optimize school schedules for managing drop-offs and pick-ups across multiple families. It leverages the Google Maps API to calculate journey times, ensuring efficient scheduling that minimizes total travel time while adhering to custody arrangements and school timings.

## Features

- **Multi-Family Support:** Manages schedules for multiple children (Fenella, Ruby, and Teddy) across different families
- **Custody Schedule Integration:** Handles complex custody arrangements with multiple parents
- **School Options:** Supports multiple school options for schedule optimization
- **Journey Time Optimization:** Uses Google Maps API to calculate and minimize total travel time
- **Flexible Drop-off/Pick-up Windows:** Accounts for 15-minute drop-off and pick-up periods
- **Clear Output Format:** Provides both detailed daily schedules and a concise two-week overview

## Installation

### Prerequisites

- Python 3.11 or higher
- Poetry dependency manager
- Google Maps API key

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/your-username/schedule_calculator.git
   cd schedule_calculator
   ```

2. **Install Dependencies**

   ```bash
   poetry install
   ```

## Configuration

1. **Environment Variables**

   Create a `.env` file in the project root:

   ```env
   GOOGLE_MAPS_API_KEY=your_api_key_here
   ```

2. **Project Structure**

   ```
   schedule_calculator/
   ├── pyproject.toml
   ├── poetry.lock
   ├── .env
   ├── README.md
   └── src/
       ├── __init__.py
       └── scheduler.py
   ```

## Usage

Run the scheduler:
