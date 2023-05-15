from flask import Flask, render_template, request, send_file
from cal_functions import run_all
import tempfile
import os
from io import BytesIO


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

# Lägg till ytterligare rutter här om det behövs.


@app.route('/generate_ics', methods=['POST'])
def generate_ics():
    pdf_file = request.files.get('pdf_file')
    sign = request.form.get('name')

    if pdf_file and sign:
        temp_pdf_file = tempfile.NamedTemporaryFile(delete=False)
        temp_pdf_file.write(pdf_file.read())
        temp_pdf_file.close()
        main_calendar = run_all(sign, temp_pdf_file.name)  # Pass the temporary file's name to run_all
        os.unlink(temp_pdf_file.name)  # Remove the temporary PDF file after processing
        ics_data = BytesIO(main_calendar.serialize().encode('utf-8'))

        return send_file(ics_data, as_attachment=True, download_name=f"arbetspass_{sign}.ics", mimetype='text/calendar')

    else:
        return "Något gick fel. Försök igen.", 400



if __name__ == '__main__':
    app.run(debug=True)