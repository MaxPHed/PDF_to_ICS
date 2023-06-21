from ics import Calendar, Event
from dateutil import tz
from datetime import datetime, timedelta
from io import BytesIO

#Konvertera datum och key i workind dictionary till en lista med ISO-datum.
def convert_date_str(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%d-%b")
        date_obj = date_obj.replace(year=datetime.now().year)
    except ValueError:
        print(f"Unable to parse date string: {date_str}")
        return None

    return date_obj

def get_start_end_datetime(date_obj, start_time_str, end_time_str, add_one_day_to_end=False):
    try:
        start_time_obj = datetime.strptime(start_time_str, "%H:%M")
        end_time_obj = datetime.strptime(end_time_str, "%H:%M")

        start_datetime = date_obj.replace(hour=start_time_obj.hour, minute=start_time_obj.minute)
        end_datetime = date_obj.replace(hour=end_time_obj.hour, minute=end_time_obj.minute)

        if add_one_day_to_end:
            end_datetime += timedelta(days=1)
    except ValueError:
        print(f"Unable to parse time range: {start_time_str}, {end_time_str}")
        return None, None

    return start_datetime, end_datetime

def handle_work_hours_key(work_hours_key, date_obj, time_range):
    try:
        if work_hours_key == "FM":
            start_datetime, end_datetime = get_start_end_datetime(date_obj, *time_range.split(' '))
            end_datetime += timedelta(days=1)
            work_description = 'FM-dygn'
        elif work_hours_key in ["L", "0", "F", "S"]:
            start_datetime, end_datetime = get_start_end_datetime(date_obj, '00:00', '23:59')
            work_description = 'Ledig' if work_hours_key =="F" else 'Föräldraledig' if work_hours_key =="S" else 'Semester'
        else:
            start_time_str, end_time_str = time_range.split(' ')
            add_one_day_to_end = end_time_str == "24:00"
            start_datetime, end_datetime = get_start_end_datetime(date_obj, start_time_str, end_time_str, add_one_day_to_end)
            work_description = "Arbetspass"
    except ValueError:
        print(f"Unable to parse time range: {time_range}")
        return None, None, None
    return start_datetime, end_datetime, work_description


def translate_month(date_str):
    """Translates Swedish month abbreviations in a date string to English."""
    replacements = {
        '-maj': '-May',
        '-okt': '-Oct',
    }

    for old, new in replacements.items():
        date_str = date_str.replace(old, new)

    return date_str

def convert_to_iso_dates(work_shifts, working_hours_dict):
    start_end_dic = []
    for work_shift in work_shifts:
        date_str = translate_month(work_shift['date'])  # translate month names
        work_hours_key = work_shift['work_hours'] if work_shift['work_hours'].isdigit() else work_shift['work_hours']
        date_obj = datetime.strptime(date_str, "%d-%b")
        date_obj = date_obj.replace(year=datetime.now().year)
        if work_hours_key in working_hours_dict:
            time_ranges = working_hours_dict[work_hours_key]
            for time_range in time_ranges:
                start_datetime, end_datetime, work_description = handle_work_hours_key(work_hours_key, date_obj, time_range)
                if start_datetime is None or end_datetime is None or work_description is None:
                    print(f"Error handling work shift: {work_shift}")
                    continue
                start_end_dic.append({
                    'start_datetime': start_datetime.isoformat(),
                    'end_datetime': end_datetime.isoformat(),
                    'work_description' : work_description})
        else:
            print(f"work_hours_key {work_hours_key} not found in working_hours_dict.")
    return start_end_dic



def create_ics_file(start_end_dic):
    # Create a calendar
    cal = Calendar()

    # Set your local timezone, e.g., for Sweden (CET/CEST)
    local_tz = tz.gettz("Europe/Stockholm")

    # Add events to the calendar for each work shift
    for work_shift in start_end_dic:
        event = Event()
        #TODO Lägg till en rad som säger vilken omplan skiftet gäller i beskrivningen.
        event.name = work_shift['work_description']  # Set the event name, e.g., "Arbetspass"

        start_datetime = datetime.fromisoformat(work_shift['start_datetime']).replace(tzinfo=local_tz)
        end_datetime = datetime.fromisoformat(work_shift['end_datetime']).replace(tzinfo=local_tz)

        # Add DTSTAMP
        now = datetime.utcnow()
        event.created = now

        # Generate a unique identifier for the event
        uid_data = f"{start_datetime.isoformat()}_{end_datetime.isoformat()}_{work_shift['work_description']}"
        uid = uid_data.replace(":", "").replace("-", "").replace("+", "").replace(" ", "")
        event.uid = uid

        event.begin = start_datetime
        event.end = end_datetime

        cal.events.add(event)

    #Gör en Bytes-IO-ström istället för en ICS-fil
    ics_data = BytesIO()
    ics_data.write(cal.serialize().encode('utf-8'))
    ics_data.seek(0)

    return ics_data


def return_calendar(work_shifts, working_hours_dict):
    main_calendar = Calendar()

    start_end_dic = convert_to_iso_dates(work_shifts, working_hours_dict)

    ics_data = create_ics_file(start_end_dic)
    calendar = Calendar(ics_data.read().decode('utf-8'))

    for event in calendar.events:
        main_calendar.events.add(event)

    return main_calendar

