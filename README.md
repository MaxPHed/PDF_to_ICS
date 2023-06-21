# PDF_to_ICS
Features:
This program converts pdf with a working schedule to an ICS-file.
It can also convert print screens of the PDF to ICS using computer vision.
The print screen needs to be of high quality, else the program may classify some days wrong, or skip days.
Working days represented by a letter instead of a number will be ignored if png is provided.

Usage:
Run the program by clicking on the local host-link in PyCharm or similar. A flask app will open in your web browser. Provide a pdf or PNG and a signature. A ICS-file will be created and downloaded and is stored in your default download folder.


Dependencies
This project uses the Tesseract OCR engine. Here's how you can install it:

On Ubuntu: sudo apt-get install tesseract-ocr
On Mac: brew install tesseract
On Windows: Go to https://github.com/UB-Mannheim/tesseract/wiki and install the executable
After installing Tesseract, you can install the necessary Python packages with pip install -r requirements.txt.
