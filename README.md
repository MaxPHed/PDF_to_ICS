# PDF_to_ICS

## Features
This program converts a PDF work schedule into an ICS-file, which can be imported into most calendar applications. The program can also process high-quality screenshots of the PDF file using computer vision.

Please note: If the input is a PNG file, working days represented by a letter instead of a number will be ignored. If the quality of the picture is too low, the program may also produce inaccurate information about the working schedule

## Usage
1. Clone the repository and run the program from your Python environment (e.g., PyCharm). This will start a local web server and open the application in your default web browser.
2. Upload a PDF or PNG file of a supported work schedule. (planering.pdf, planering72.pdf and schema_pic.png is supported and tested)
3. Enter a signature.
4. Press the "Submit" button.
5. The program will generate an ICS file and download it to your default downloads folder.

To import the ICS file into your calendar:
1. Open the downloaded ICS file.
2. Import the events into your preferred calendar application.

## Dependencies
This project uses the Tesseract OCR engine. Here's how you can install it:

- On Ubuntu: `sudo apt-get install tesseract-ocr`
- On Mac: `brew install tesseract`
- On Windows: Download and install the executable from [here](https://github.com/UB-Mannheim/tesseract/wiki).

##Installation
After installing Tesseract follow these steps:
1.Navigate to the project directory in cmd using CD (EXAMPLE: cd C:\Users\username\downloads\CalendarApp)
2. Create a virtual environment using the following command: "python -m venv venv"
3. Activate the virtual environment using these commands =  for Windows: "venv\Scripts\activate" , for Mac: "source venv/bin/activate"
4. Install the necessary dependencies by running the following command: pip install -r requirements.txt (This will install all the required packages and dependencies for the project). install the necessary Python packages by running `pip install -r requirements.txt` in your terminal.
5. Set the module to be run with "set FLASK_APP=main.py" for windows or  "export FLASK_APP=main.py" for Bash
6. Once the previous steps are completed you can type "flask run" in the console and it will provide a html link to your local port, copy this and paste into your webbrowers searchbar and hit enter.

