from flask import Flask, render_template, request, send_file, flash, url_for, redirect
from cal_functions import return_calendar
import tempfile
import os
from io import BytesIO
import traceback
import png_processing
import pdf_processing


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # replace with your own secret key


@app.route('/')
def index():
    return render_template('index.html')

# Lägg till ytterligare rutter här om det behövs.

@app.route('/generate_ics', methods=['POST'])
def generate_ics():
    upload_file = request.files.get('upload_file')
    sign = request.form.get('name')

    if upload_file and sign:
        file_extension = os.path.splitext(upload_file.filename)[1].lower()
        temp_file_fd, temp_file_path = tempfile.mkstemp(suffix=file_extension)
        with os.fdopen(temp_file_fd, 'wb') as tmp:
            # write the data to file
            tmp.write(upload_file.read())

        try:
            if file_extension == '.pdf':
                work_shifts, working_hours_dict = pdf_processing.return_work_shifts_and_working_keys(sign, temp_file_path)
            elif file_extension == '.png':

                work_shifts, working_hours_dict = png_processing.return_work_shifts_and_working_keys(sign, temp_file_path)
                print(f'Work shifts: {work_shifts}')
                print(f'Working hours dict: {working_hours_dict}')
            else:
                flash("Invalid file type. Please upload a PDF or PNG file.")
                return redirect(url_for('index'))
        except Exception as e:
            error_info = traceback.format_exc()
            flash(error_info)
            return redirect(url_for('index'))
        finally:
            os.remove(temp_file_path)  # Make sure to delete the file in any case

        main_calendar = return_calendar(work_shifts, working_hours_dict) #Returns an ICS-file
        print(f'main calendar: {main_calendar}')
        if main_calendar:
            ics_data = BytesIO(main_calendar.serialize().encode('utf-8'))

        return send_file(ics_data, as_attachment=True, attachment_filename=f"arbetspass_{sign}.ics", mimetype='text/calendar')


    else:
        flash("Något gick fel. Försök igen.")
        return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(debug=True)