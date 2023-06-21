import cv2
import numpy as np
import matplotlib.pyplot as plt
import pytesseract
import re
import os

def detect_lines(image):
    # Initialize two empty lists to store the horizontal and vertical lines
    horizontal_lines = []
    vertical_lines = []

    # Scan the image for horizontal lines
    for y in range(image.shape[0]):
        white_pixels = []
        for x in range(image.shape[1]):
            if image[y, x] == 255:  # White pixel
                white_pixels.append((x, y))
            elif white_pixels:
                if len(white_pixels) >= 400:
                    horizontal_lines.append(white_pixels)
                white_pixels = []
        if white_pixels and len(white_pixels) >= 400:
            horizontal_lines.append(white_pixels)

    # Scan the image for vertical lines
    for x in range(image.shape[1]):
        white_pixels = []
        for y in range(image.shape[0]):
            if image[y, x] == 255:  # White pixel
                white_pixels.append((x, y))
            elif white_pixels:
                if len(white_pixels) >= 200:
                    vertical_lines.append(white_pixels)
                white_pixels = []
        if white_pixels and len(white_pixels) >= 200:
            vertical_lines.append(white_pixels)

    return horizontal_lines, vertical_lines

def merge_lines(lines, is_horizontal=True, thickness_threshold=10, length_threshold=10):
    if not lines:
        return []

    # Sorting criterion depends on whether the lines are horizontal or vertical
    sort_index = 1 if is_horizontal else 0
    lines.sort(key=lambda line: (line[0][sort_index], line[0][1-sort_index]))

    merged_lines = []
    current_line = lines[0]

    for next_line in lines[1:]:
        # Check whether the lines are neighboring and part of the same grid line
        if abs(current_line[0][sort_index] - next_line[0][sort_index]) <= thickness_threshold and \
                abs(current_line[-1][1-sort_index] - next_line[0][1-sort_index]) <= thickness_threshold:
            # Merge the lines by taking union of pixels
            current_line = list(set(current_line) | set(next_line))
        else:
            # Only add line if it exceeds the minimum length
            if len(current_line) >= length_threshold:
                merged_lines.append(current_line)
            current_line = next_line

    # Add the last line if it exceeds the minimum length
    if len(current_line) >= length_threshold:
        merged_lines.append(current_line)

    return merged_lines


def get_cells(horizontal_lines, vertical_lines):
    # Flatten the list of lines and separate the x and y coordinates
    x_coords = {x for line in vertical_lines for x, _ in line}
    y_coords = {y for line in horizontal_lines for _, y in line}

    # Convert the sets to sorted lists
    x_coords = sorted(list(x_coords))
    y_coords = sorted(list(y_coords))

    # Get the cells by finding the four corners for each consecutive pair of x and y coordinates
    cells = []
    for i in range(len(x_coords) - 1):
        for j in range(len(y_coords) - 1):
            cell = [(x_coords[i], y_coords[j]),
                    (x_coords[i+1], y_coords[j]),
                    (x_coords[i], y_coords[j+1]),
                    (x_coords[i+1], y_coords[j+1])]
            cells.append(cell)

    return cells


def filter_cells_by_dimensions(cells, min_width=20, min_height=20):
    filtered_cells = []

    for cell in cells:
        # Calculate the width and height of the cell
        width = abs(cell[1][0] - cell[0][0])
        height = abs(cell[2][1] - cell[0][1])

        # Only keep the cell if its width and height are above the specified minimums
        if width >= min_width and height >= min_height:
            filtered_cells.append(cell)

    return filtered_cells

def rescale_image(image, new_height=35):
    # Get the current dimensions of the image
    original_height, original_width = image.shape[:2]

    # Calculate the new width while maintaining the aspect ratio
    new_width = int(original_width * new_height / original_height)

    # Use cv2.resize to resize the image
    resized_image = cv2.resize(image, (new_width, new_height), interpolation = cv2.INTER_LINEAR)

    return resized_image

def crop_borders(image, x):
    """
    Crop the left and top border of an image.

    :param image: numpy array
        The input image.
    :param x: int
        The number of pixels to crop from the left and top border.

    :return: numpy array
        The cropped image.
    """
    height, width = image.shape[:2]
    return image[x:height-x, x:width-x]

def is_cell_empty(image, variance_threshold=2000):
    """
    Check if a cell is more or less empty.

    :param image: numpy array
        The input image.
    :param variance_threshold: int
        The threshold for variance to consider a cell as empty.

    :return: boolean
        True if the cell is empty, False otherwise.
    """
    #The threshold 2000 is usally enough for an empty cell
    return np.var(image) < variance_threshold

def move_cell(cell, direction, move_pixels=5):
    """
    Move the boundaries of a cell in a certain direction by a certain number of pixels.

    :param cell: list
        The cell boundaries in the format [top_left, top_right, bottom_left, bottom_right].
    :param direction: str
        The direction to move the cell's boundaries. Can be 'left', 'up', 'right', or 'down'.
    :param move_pixels: int
        The number of pixels to move the cell's boundaries.

    :return: list
        The new cell.
    """
    # Get the cell's boundaries
    top_left = list(cell[0])
    bottom_right = list(cell[3])

    # Determine the direction to move the cell's boundaries
    if direction == 'left':
        top_left[0] -= move_pixels
        bottom_right[0] -= move_pixels
    elif direction == 'up':
        top_left[1] -= move_pixels
        bottom_right[1] -= move_pixels
    elif direction == 'right':
        top_left[0] += move_pixels
        bottom_right[0] += move_pixels
    elif direction == 'down':
        top_left[1] += move_pixels
        bottom_right[1] += move_pixels

    # Return the new cell
    new_cell = [top_left, [bottom_right[0], top_left[1]], [top_left[0], bottom_right[1]], bottom_right]

    return new_cell


def remove_frame(image, threshold=150):
    while True:
        # Check if the borders are uniformly colored
        top_row = image[0, :]
        bottom_row = image[-1, :]
        left_col = image[:, 0]
        right_col = image[:, -1]

        # If the borders are uniform and in a shade of black, remove them
        if np.all(top_row < threshold):
            image = image[1:, :]
        elif np.all(bottom_row < threshold):
            image = image[:-1, :]
        elif np.all(left_col < threshold):
            image = image[:, 1:]
        elif np.all(right_col < threshold):
            image = image[:, :-1]
        else:
            # If no borders are uniformly colored and in a shade of black, stop the loop
            break

    return image

def remove_border(image, threshold=50):
    while True:
        # Check the mean color of the border pixels, if it's less than the threshold, remove the border
        if np.mean(image[0, :]) < threshold:  # top border
            print(f"Removing top border, mean color: {np.mean(image[0, :])}")
            image = image[1:, :]
        elif np.mean(image[-1, :]) < threshold:  # bottom border
            print(f"Removing bottom border, mean color: {np.mean(image[-1, :])}")
            image = image[:-1, :]
        elif np.mean(image[:, 0]) < threshold:  # left border
            print(f"Removing left border, mean color: {np.mean(image[:, 0])}")
            image = image[:, 1:]
        elif np.mean(image[:, -1]) < threshold:  # right border
            print(f"Removing right border, mean color: {np.mean(image[:, -1])}")
            image = image[:, :-1]
        else:
            # If no border has mean color less than the threshold, break the loop

            break

    return image

def print_image(image):
    plt.figure(figsize=(5,5))
    plt.imshow(image, cmap='gray')
    plt.show()
def dilate_image(image, cell, kernel_size=5):
    """
    Dilate the image.

    :param image: numpy array
        The input image.
    :param cell: list
        The cell boundaries in the format [top_left, top_right, bottom_left, bottom_right].
    :param kernel_size: int
        The size of the kernel used for dilation. A larger kernel_size value means a larger dilation effect.

    :return: numpy array
        The dilated image.
    """
    # Get the cell's boundaries
    top_left = cell[0]
    bottom_right = cell[3]

    # Crop the image to the cell's boundaries
    cell_image = image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

    # Create the kernel for dilation
    kernel = np.ones((kernel_size, kernel_size), np.uint8)

    # Dilate the image
    dilated_image = cv2.dilate(cell_image, kernel, iterations = 1)

    return dilated_image

def erode_image(image, cell, kernel_size=5):
    """
    Erode the image.

    :param image: numpy array
        The input image.
    :param cell: list
        The cell boundaries in the format [top_left, top_right, bottom_left, bottom_right].
    :param kernel_size: int
        The size of the kernel used for erosion. A larger kernel_size value means a larger erosion effect.

    :return: numpy array
        The eroded image.
    """
    # Get the cell's boundaries
    top_left = cell[0]
    bottom_right = cell[3]

    # Crop the image to the cell's boundaries
    cell_image = image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

    # Create the kernel for erosion
    kernel = np.ones((kernel_size, kernel_size), np.uint8)

    # Erode the image
    eroded_image = cv2.erode(cell_image, kernel, iterations = 1)

    return eroded_image

def read_cell(image, cell, type=None, print = False):
    if not isinstance(image, np.ndarray) or image.ndim != 2:
        raise ValueError("Input image must be a 2D numpy array.")

    if not isinstance(cell, list) or len(cell) != 4:
        raise ValueError("Cell must be a list of 4 points.")

    if not all(0 <= x < image.shape[1] and 0 <= y < image.shape[0] for x, y in cell):
        raise ValueError("Cell points must lie within the image bounds.")

    cell_contents = {}

    # Define cell boundaries
    top_left = cell[0]
    bottom_right = cell[3]
    # Crop the image to the cell's boundaries
    cell_image = image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

    #Check if cell is more or less empty

    cell_empty = is_cell_empty(cell_image)
    config = '--psm 7'
    if type == 'digit':
        config= '--psm 10'
    if cell_empty:
        text = 'empty'

    else:
        #cell_image = crop_borders(cell_image,2)
        cell_image = remove_frame(cell_image, 50)

        # Use Tesseract to extract the text from the cell
        text = pytesseract.image_to_string(cell_image, config=config).strip()  # strip() is used to remove leading and trailing white space

        if text == "":
            cell_image = rescale_image(cell_image)
            text = pytesseract.image_to_string(cell_image, config=config).strip()
        directions = ['down', 'up', 'left', 'right']

        for direction in directions:
            if text == "":
                new_cell = move_cell(cell, direction, 10)
                cell_image_moved = image[new_cell[0][1]:new_cell[3][1], new_cell[0][0]:new_cell[3][0]]
                text = pytesseract.image_to_string(cell_image_moved, config=config).strip()
            else:
                break
        if text == "":
            dilated_image = dilate_image(image, cell, 3)
            text = pytesseract.image_to_string(dilated_image, config=config).strip()
        if text == "":
            eroded_image = erode_image(image, cell, 3)
            text = pytesseract.image_to_string(eroded_image, config=config).strip()
        if text == "":
            text = pytesseract.image_to_string(cell_image, config='--psm 10')
            if text == 'oO\n':
                text == ""
        if text == "":
            print('Cant regognize')
            plt.figure(figsize=(5,5))
            plt.imshow(cell_image, cmap='gray')
            plt.show()
            print(cell)

    rect = [top_left, (bottom_right[0], top_left[1]), (top_left[0], bottom_right[1]), bottom_right]
    if print: print_image(cell_image)
    cell_contents = {'rect': rect, 'content': text}
    return cell_contents

def get_cells_on_row(all_cells, reference_cell, only_right=False):
    # Get the y-coordinates of the reference cell
    reference_y_top = reference_cell[0][1]
    reference_y_bottom = reference_cell[2][1]

    # Calculate the y-coordinate of the middle point of the reference cell
    reference_y_mid = (reference_y_top + reference_y_bottom) / 2

    # Get the x-coordinate of the right edge and left edge of the reference cell
    reference_x_right = reference_cell[2][0]
    reference_x_left = reference_cell[0][0]

    # Initialize an empty list to store the row cells
    row_cells = []

    # Iterate over all cells
    for cell in all_cells:
        # Get the y-coordinates of the current cell
        cell_y_top = cell[0][1]
        cell_y_bottom = cell[2][1]

        # Get the x-coordinate of the left and right edge of the current cell
        cell_x_left = cell[0][0]
        cell_x_right = cell[2][0]

        # Check if the reference cell's middle point falls within the y-coordinates of the current cell
        if cell_y_top <= reference_y_mid <= cell_y_bottom:
            # Check if we only want cells on the right or all cells on the same row
            if only_right:
                # Only consider the cell if it is to the right of the reference cell
                if cell_x_left > reference_x_right:
                    row_cells.append(cell)
            else:
                # Consider all cells on the same row
                if cell_x_right >= reference_x_left or cell_x_left <= reference_x_right:
                    row_cells.append(cell)

    return row_cells


def remove_empty_cells(cells):
    return [cell for cell in cells if cell['content'].strip() != ""]


def remove_cells_without_dash(cells):
    cells_with_dash = [cell for cell in cells if '-' in cell['content']]
    return cells_with_dash


def fix_cell_dates(cells):
    # Check if cells is a list
    if not isinstance(cells, list):
        raise TypeError("Expected a list for 'cells', got: %s" % type(cells))

    pattern = re.compile("([0-3][0-9])-(\w{3})")  # Matches 'dd-mmm'

    for i in range(len(cells)):
        # Check if cell is a dictionary with a 'content' key
        if not isinstance(cells[i], dict) or 'content' not in cells[i]:
            raise ValueError("Expected a dictionary with a 'content' key for each cell")

        # Check if 'content' is a string
        if not isinstance(cells[i]['content'], str):
            raise TypeError("Expected a string for 'content' in each cell, got: %s" % type(cells[i]['content']))

        # If the current cell content does not match the pattern
        if not pattern.fullmatch(cells[i]['content']):
            # If it's not the first cell
            if i > 0:
                # Get the previous cell's date and increment it
                prev_date_match = pattern.fullmatch(cells[i-1]['content'])

                if prev_date_match:  # if the previous cell's content was a valid date
                    day = int(prev_date_match.group(1))
                    month = prev_date_match.group(2)

                    # Increment the day and reset to 01 if it reaches 32
                    day = day + 1 if day < 31 else 1

                    # Format the day to always have 2 digits
                    day_str = str(day).zfill(2)

                    # Set the current cell's content to the fixed date
                    cells[i]['content'] = f"{day_str}-{month}"

    return cells


def retrieve_cells_by_content(cells, content):
    matched_cells = []

    for cell in cells:
        if str(content) in cell['content']:
            matched_cells.append(cell)

    return matched_cells

def retrieve_cells_by_exact_content(cells, content):
    matched_cells = []

    for cell in cells:
        if str(content) == cell['content']:
            matched_cells.append(cell)

    return matched_cells

def return_sign_and_date_cell(image, cells, sign):
    sign_cell = None
    date_cell = None

    # Create additional search patterns for the sign
    search_patterns = [sign.lower(), sign.lower().replace('ö', 'o'), sign.lower().replace('ä', 'a'), sign.lower().replace('å', 'a')]

    for cell in cells:
        # Read the cell
        cell_content = read_cell(image, cell)

        # Check cell content for "sign" and store the cell if found
        if any(pattern in cell_content['content'].lower() for pattern in search_patterns) and sign_cell is None:
            sign_cell = cell_content

        # Check cell content for the date regex and store the cell if found
        elif re.match(r"\b(0[1-9]|1[0-9]|2[0-9]|3[0-1])-(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)\b", cell_content['content'].lower()) and date_cell is None:
            date_cell = cell_content

        # If both "sign" and a date have been found, stop reading cells
        if sign_cell is not None and date_cell is not None:
            break

    if sign_cell is None:
        raise ValueError(f"No cell found containing the sign: {sign}")

    if date_cell is None:
        raise ValueError("No cell found containing a valid date. Try uploading a file with higher quality")

    return sign_cell, date_cell


def get_hours_keys(unique_numbers_in_row, cells_filtered, gray_image):
    # Assuming page_height is the height of your page, define the start of the lower 40%
    lower_40_threshold = gray_image.shape[0] * 0.6

    # Copy your set of numbers so you can modify it while iterating
    numbers_to_find = unique_numbers_in_row.copy()

    # Create an empty list to store the cell contents
    cell_contents_hours_key = []

    # Iterate over cells
    for cell in cells_filtered:
        # Get the 'y' attribute as the vertical position
        y_position = max(coord[1] for coord in cell)

        # Check if the cell is in the lower 40% of the image
        if y_position >= lower_40_threshold:

            # Read cell and get the content
            cell_content = read_cell(gray_image,cell, 'digit', False)
            text = cell_content['content']
            # If the cell_content is a digit and is in our numbers_to_find
            if text.isdigit() and int(text) in numbers_to_find:
                # Add cell content to our list
                cell_contents_hours_key.append(cell_content)

                # Remove the found number from our set
                numbers_to_find.remove(int(text))
            # If we have found all numbers, break the loop
            if len(numbers_to_find) == 0:
                break
    return cell_contents_hours_key


def get_list_of_working_hours(cell_contents_hours_key, cells_filtered, gray_image):
    def get_list_of_working_hours(cell_contents_hours_key, cells_filtered, gray_image):
        if not isinstance(cell_contents_hours_key, list) or not isinstance(cells_filtered, list):
            raise ValueError("Both cell_contents_hours_key and cells_filtered must be lists.")

        if not isinstance(gray_image, np.ndarray) or gray_image.ndim != 2:
            raise ValueError("gray_image must be a 2D numpy array.")

        if not cell_contents_hours_key:
            raise ValueError("cell_contents_hours_key cannot be empty.")

    working_hours_list = []
    for cell in cell_contents_hours_key:
        dic = {}
        dic['work_key'] = cell['content']
        dic['hours'] = []
        cells_to_right = get_cells_on_row(cells_filtered, cell['rect'], only_right=True)
        for subcell in cells_to_right[:6]:
            subcell_content = read_cell(gray_image, subcell, type = 'digit', print = False)
            matches = re.findall(r"\b\d{1,2}[:-]\d{2}\b", subcell_content['content'])
            if matches: dic['hours'].extend(matches)  # extend the list with new matches
        working_hours_list.append(dic)
    return working_hours_list

def get_mid_x(rect):
    """Get middle x-point of a rectangle"""
    x_left = rect[0][0]
    x_right = rect[2][0]
    return (x_left + x_right) / 2

def find_corresponding_cell(mid_x, sign_row_read):
    """Find the corresponding cell in sign_row_read that has mid_x within its x range"""
    for cell in sign_row_read:
        x_left = cell['rect'][0][0]
        x_right = cell['rect'][2][0]
        if x_left <= mid_x <= x_right:
            return cell
    return None

def combine_date_and_work_key(date_cells_filtered, sign_row_read):
    if not isinstance(date_cells_filtered, list) or not isinstance(sign_row_read, list):
        raise ValueError("Both date_cells_filtered and sign_row_read must be lists.")

    if not date_cells_filtered:
        raise ValueError("date_cells_filtered cannot be empty.")

    result_list = []

    for date_cell in date_cells_filtered:
        mid_x = get_mid_x(date_cell['rect'])
        corresponding_cell = find_corresponding_cell(mid_x, sign_row_read)

        if corresponding_cell is not None:
            result_list.append({'date': date_cell['content'], 'work_hours': corresponding_cell['content']})

    return result_list

def filter_content(sign_row_read):
    # Use list comprehension to filter out unwanted content
    filtered_list = [d for d in sign_row_read if not any(unwanted in d['content'] for unwanted in ['-', ':', 'empty', '—'])]

    return filtered_list


def combine_hours(working_hours_list):
    if not isinstance(working_hours_list, list):
        raise ValueError("working_hours_list must be a list.")

    new_dict = {}

    for dic in working_hours_list:
        if not isinstance(dic, dict) or 'work_key' not in dic or 'hours' not in dic:
            raise ValueError("Each item in working_hours_list must be a dictionary with 'work_key' and 'hours' keys.")

        if not isinstance(dic['hours'], list):
            raise ValueError("The 'hours' value in each dictionary must be a list.")

        hours = dic['hours']
        combined_hours = [' '.join(hours[i:i + 2]) for i in range(0, len(hours), 2)]
        new_dict[dic['work_key']] = combined_hours

    return new_dict

filepath = 'schema_pic.png'
signature = 'DOF'

def return_work_shifts_and_working_keys(signature, filepath):
    # Check if the file exists
    if not os.path.isfile(filepath):
        raise ValueError(f"File {filepath} does not exist.")
    # Load the image in full color
    color_image = cv2.imread(filepath, cv2.IMREAD_COLOR)

    # Check if the image is readable
    if color_image is None:
        raise ValueError(f"Could not read the file {filepath} as an image.")

    # Check if the signature is valid
    if not isinstance(signature, str) or signature == "":
        raise ValueError("Signature must be a non-empty string.")

    # Convert the color image to grayscale
    gray_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)

    # Check if the image has at least two dimensions (height and width)
    if len(gray_image.shape) < 2:
        raise ValueError("Image must have at least two dimensions (height and width).")

    # Threshold the image to get a binary image
    _, binary_image = cv2.threshold(gray_image, 150, 255, cv2.THRESH_BINARY_INV)

    # Detect the lines in the image. One line is one pixel wide
    horizontal_lines, vertical_lines = detect_lines(binary_image)

    # Merge the lines to reduce them
    merged_horizontal_lines = merge_lines(horizontal_lines, True)
    merged_vertical_lines = merge_lines(vertical_lines, False)

    # Makes a grid of cells according to the lines. Each cell has four points to mark its corners.
    cells = get_cells(merged_horizontal_lines, merged_vertical_lines)

    # Check if the cells are detected
    if not cells:
        raise ValueError("No cells detected in the image.")

    # Filters the cells so that they need to be at least 10x10 pixels
    cells_filtered = filter_cells_by_dimensions(cells, 10, 10)

    # Reads the first 200 cells until it finds the signature and a cell that contains a date and returns it
    sign_cell, date_cell = return_sign_and_date_cell(gray_image, cells_filtered[:200], signature)

    # Check if the signature and date cells are detected
    if sign_cell is None or date_cell is None:
        raise ValueError("Could not detect the signature and date cells.")

    # Get the coordinates of all the date cells that are on the row of the one we found.
    date_cells = get_cells_on_row(cells_filtered, date_cell['rect'])

    # Reads the image of all the date-cells and stores it in a list with dictionaries
    date_cells_read = [read_cell(gray_image,cell) for cell in date_cells]

    # Filters empty cells
    date_cells_filtered = remove_empty_cells(date_cells_read)
    # Removes all cells that don't have a dash in it = no date
    date_cells_filtered = remove_cells_without_dash(date_cells_filtered)
    # If any date wrong, this function tries to correct that. Not foolproof, i.e. the first date is read wrong.
    date_cells_filtered = fix_cell_dates(date_cells_filtered)

    # Gets the coordinates for all the cells on the row of the signature
    sign_row = get_cells_on_row(cells_filtered, sign_cell['rect'])

    # Reads the image of all the cells in the signature row
    sign_row_read = [read_cell(gray_image,cell, 'digit') for cell in sign_row]

    sign_row_read = filter_content(sign_row_read)

    # Stores a set with all the unique number values of the row corresponding to the signature
    unique_numbers_in_row = {int(cell['content']) for cell in sign_row_read if
                             cell['content'].isdigit() and len(cell['content']) <= 2 and int(cell['content']) > 0}

    # Reads the lower 40% of the image until it finds all the unique numbers we want.
    # Then returns a list of dictionaries
    cell_contents_hours_key = get_hours_keys(unique_numbers_in_row, cells_filtered, gray_image)

    # Reads the following 6 cells to the right of the unique numbers, getting a list of dictionaries
    working_hours_list = get_list_of_working_hours(cell_contents_hours_key, cells_filtered, gray_image)

    # Converts the list to a dictionary that can be read by cal-functions.
    working_hours_dict = combine_hours(working_hours_list)

    # Combines the date with the corresponding number on the sign row by its coordinates. Stores it in a list of dictionaries
    work_shifts = combine_date_and_work_key(date_cells_filtered, sign_row_read)

    return work_shifts, working_hours_dict



