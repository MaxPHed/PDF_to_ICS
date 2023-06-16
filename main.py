from flask import Flask, render_template, request, send_file, flash, url_for, redirect
from cal_functions import run_pdf, run_png
import tempfile
import os
from io import BytesIO
import traceback


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # replace with your own secret key


@app.route('/')
def index():
    return render_template('index.html')

# Lägg till ytterligare rutter här om det behövs.


'''@app.route('/generate_ics', methods=['POST'])
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
        return "Något gick fel. Försök igen.", 400'''

@app.route('/generate_ics', methods=['POST'])
def generate_ics():
    upload_file = request.files.get('upload_file')
    sign = request.form.get('name')

    if upload_file and sign:
        file_extension = os.path.splitext(upload_file.filename)[1].lower()
        temp_file = tempfile.NamedTemporaryFile(suffix=file_extension, delete=False)
        temp_file.write(upload_file.read())
        temp_file.close()

        try:
            if file_extension == '.pdf':
                main_calendar = run_pdf(sign, temp_file.name)
            elif file_extension == '.png':
                main_calendar = run_png(sign, temp_file.name)
            else:
                flash("Invalid file type. Please upload a PDF or PNG file.")
                return redirect(url_for('index'))
        except Exception as e:
            error_info = traceback.format_exc()
            flash(error_info)
            return redirect(url_for('index'))
        if main_calendar:
            os.unlink(temp_file.name)
            ics_data = BytesIO(main_calendar.serialize().encode('utf-8'))

        return send_file(ics_data, as_attachment=True, download_name=f"arbetspass_{sign}.ics", mimetype='text/calendar')

    else:
        flash("Något gick fel. Försök igen.")
        return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(debug=True)