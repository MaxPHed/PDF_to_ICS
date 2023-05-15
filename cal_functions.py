import pdfplumber
from ics import Calendar, Event
from dateutil import tz
from datetime import datetime, timedelta
from io import BytesIO
import tempfile
import re



def import_pdf(pdf_file_path):
    # Save the file temporarily
    temp_pdf_file = tempfile.NamedTemporaryFile(delete=False)
    temp_pdf_file.write(pdf_file_path.read())
    temp_pdf_file.close()
    return temp_pdf_file

def get_amount_of_pages(pdf_file_path):
    with pdfplumber.open(pdf_file_path) as pdf:
        total_pages = len(pdf.pages)

    return total_pages


def get_tables_from_pdf(x, pdf_file_path):
    #Ändra så att den läser filen som skickades via formulär istället enligt gpt
    # Läser av tabellerna i en PDF och skapar Listor av listor av dem
    with pdfplumber.open(pdf_file_path) as pdf:
        first_page = pdf.pages[x]
        tables = first_page.extract_tables()
    return tables


def is_date_format(cell):
    if cell is None:
        return False
    date_pattern = re.compile(r'\d{1,2}-[a-zA-Z]{3}')
    return bool(date_pattern.match(cell))

def extract_date_and_name_lists(tables, name):
    date_list = None
    name_list = None

    # Tar ut en lista med datum och en lista med ett namn(name) och sparar som egna listor.
    for table in tables:
        for row in table:
            if row and len(row) > 0:
                # Check if row contains mostly date-like strings
                date_like_cells = [cell for cell in row if is_date_format(cell)]
                if len(date_like_cells) / len(row) > 0.5:
                    date_list = [date.replace("maj", "may").replace("okt", "oct") for date in row]
                elif row[0] == name:
                    name_list = row

            if date_list and name_list:
                break
    return date_list, name_list


def create_work_shifts(date_list, name_list):
    work_shifts = []

    # Sätter ihop lista med arbetsnycklar med datum i en lista med dictionarys
    for idx, date in enumerate(date_list):
        if not date or date == 'Dat':
            continue

        work_hours = name_list[idx]

        if work_hours and work_hours != '':
            work_shifts.append({
                'date': date,
                'work_hours': work_hours
            })
    return work_shifts


def extract_working_hours_list(tables):
    # Tar ut alla nycklar för working hour och lägger i en lista
    working_hours_list = []

    for table in tables:
        for row in table:
            if row and len(row) > 0 and row[0] and row[0].isdigit() and 1 <= int(row[0]) <= 10:
                working_hours_list.extend(row)
    return working_hours_list


def create_working_hours_dict(working_hours_list):
    special_keys = ["FM", "Ö", 'L', 'F', 'S']

    working_hours_dict = {'L': ['00:00', '23:59'], '0':['00:00', '23:59'], 'S':['00:00', '23:59']}
    key = None
    item_count = 0

    for item in working_hours_list:
        if item and (item.isdigit() or item in special_keys):
            key = item
            working_hours_dict[key] = []
            item_count = 0
        else:
            if key and item_count < 4:
                working_hours_dict[key].append(item)
                item_count += 1

    working_hours_dict = {key: working_hours_dict[key] for key in
                          sorted(working_hours_dict, key=lambda x: (str(x).isdigit(), x))}
    if "FM" in working_hours_dict:
        start_time = working_hours_dict["FM"][0].split(' ')[0]
        working_hours_dict["FM"] = [f"{start_time} {start_time}"]
    if "S" in working_hours_dict:
        start_time = working_hours_dict["FM"][0].split(' ')[0]
        working_hours_dict["S"] = ['00:00', '23:59']
    return working_hours_dict


#Ta bort onödiga variabler i working hours dict
def remove_last_and_empty(input_list):
    return [item for index, item in enumerate(input_list[:-1]) if item]


#Konvertera datum och key i workind dictionary till en lista med ISO-datum.
def convert_to_iso_dates(work_shifts, working_hours_dict):

    start_end_dic = []

    for work_shift in work_shifts:
        date_str = work_shift['date']
        work_hours_key = work_shift['work_hours'] if work_shift['work_hours'].isdigit() else work_shift[
            'work_hours']

        date_obj = datetime.strptime(date_str, "%d-%b")
        date_obj = date_obj.replace(year=datetime.now().year)

        work_description = "Arbete"

        if work_hours_key in working_hours_dict:
            time_ranges = working_hours_dict[work_hours_key]

            for time_range in time_ranges:
                work_description = "Arbetspass"
                if work_hours_key == "FM":
                    start_time_str, end_time_str = time_range.split(' ')

                    start_time_obj = datetime.strptime(start_time_str, "%H:%M")
                    end_time_obj = datetime.strptime(end_time_str, "%H:%M")

                    start_datetime = date_obj.replace(hour=start_time_obj.hour, minute=start_time_obj.minute)
                    end_datetime = date_obj.replace(hour=end_time_obj.hour, minute=end_time_obj.minute)

                    end_datetime += timedelta(days=1)

                    work_description = 'FM-dygn'
                elif work_hours_key == "L" or work_hours_key == "0" or work_hours_key == "F" or work_hours_key == "S":
                    start_time_obj = datetime.strptime('00:00', "%H:%M")
                    end_time_obj = datetime.strptime('23:59', "%H:%M")

                    start_datetime = date_obj.replace(hour=start_time_obj.hour, minute=start_time_obj.minute)
                    end_datetime = date_obj.replace(hour=end_time_obj.hour, minute=end_time_obj.minute)
                    work_description = 'Ledig'
                    if work_hours_key =="F":
                        work_description = 'Föräldraledig'
                    if work_hours_key =="S":
                        work_description = 'Semester'
                else:
                    start_time_str, end_time_str = time_range.split(' ')

                    if end_time_str == "24:00":
                        end_time_str = "00:00"
                        add_one_day_to_end = True
                    else:
                        add_one_day_to_end = False

                    start_time_obj = datetime.strptime(start_time_str, "%H:%M")
                    end_time_obj = datetime.strptime(end_time_str, "%H:%M")

                    start_datetime = date_obj.replace(hour=start_time_obj.hour, minute=start_time_obj.minute)
                    end_datetime = date_obj.replace(hour=end_time_obj.hour, minute=end_time_obj.minute)

                    if add_one_day_to_end:
                        end_datetime += timedelta(days=1)

                start_end_dic.append({
                    'start_datetime': start_datetime.isoformat(),
                    'end_datetime': end_datetime.isoformat(),
                    'work_description' : work_description})
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

    # Write the calendar to an .ics file
    '''with open(file_name, "w") as f:
        f.write(cal.serialize())'''
    #Gör en Bytes-IO-ström istället för en ICS-fil
    ics_data = BytesIO()
    ics_data.write(cal.serialize().encode('utf-8'))
    ics_data.seek(0)

    return ics_data


def run_all(sign, _temp_pdf_file_path):
    temp_pdf_file_path = _temp_pdf_file_path
    number_of_pages = get_amount_of_pages(temp_pdf_file_path)
    x = 0
    main_calendar = Calendar()
    while x < number_of_pages:
        tables = get_tables_from_pdf(x, temp_pdf_file_path)
        date_list, name_list = extract_date_and_name_lists(tables, sign)
        work_shifts = create_work_shifts(date_list, name_list)
        working_hours_list = extract_working_hours_list(tables)
        working_hours_dict = create_working_hours_dict(working_hours_list)
        for key in working_hours_dict:
            if key == 'FM':
                continue
            else:
                working_hours_dict[key] = remove_last_and_empty(working_hours_dict[key])
        start_end_dic = convert_to_iso_dates(work_shifts, working_hours_dict)
        #ics_file_path = create_ics_file(start_end_dic, f"arbetspass_{sign}_{str(x)}.ics")

        '''with open(ics_file_path, 'r') as f:
            calendar = Calendar(f.read())'''

        ics_data = create_ics_file(start_end_dic)
        calendar = Calendar(ics_data.read().decode('utf-8'))

        x = x + 1
        for event in calendar.events:
            main_calendar.events.add(event)

    return main_calendar


#run_all("LNG", "arbetspass")