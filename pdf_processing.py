import pdfplumber
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


def return_work_shifts_and_working_keys(sign, _temp_pdf_file_path):
    temp_pdf_file_path = _temp_pdf_file_path
    number_of_pages = get_amount_of_pages(temp_pdf_file_path)
    x = 0
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
        x = x + 1
    return work_shifts, working_hours_dict
