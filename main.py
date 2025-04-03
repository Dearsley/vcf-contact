from flask import Flask, render_template, request, redirect, url_for, send_file
import os
import vobject
import csv

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'vcf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return redirect(url_for('index'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.vcf')
    file.save(filepath)
    return redirect(url_for('view_contacts'))


@app.route('/view')
def view_contacts():
    search_query = request.args.get('search', '').lower()
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.vcf')
    contacts = []

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as file:
            vcf_data = file.read()
            for vcard in vobject.readComponents(vcf_data):
                name = vcard.fn.value if hasattr(vcard, 'fn') else 'Неизвестно'
                work_phone = None
                home_phone = None
                email = vcard.email.value if hasattr(vcard, 'email') else 'Нет email'
                address = 'Нет адреса'

                if hasattr(vcard, 'tel'):
                    for tel in vcard.contents['tel']:
                        if 'work' in tel.params.get('TYPE', []):
                            work_phone = tel.value
                        elif 'home' in tel.params.get('TYPE', []):
                            home_phone = tel.value

                if hasattr(vcard, 'adr'):
                    adr = vcard.adr.value
                    address_parts = [
                        ' '.join(adr.street) if isinstance(adr.street, list) else adr.street,
                        adr.city,
                        adr.region,
                        adr.code,
                        adr.country
                    ]
                    address = ', '.join(filter(None, address_parts))

                contact = {
                    'name': name,
                    'work_phone': work_phone or 'Нет рабочего телефона',
                    'home_phone': home_phone or 'Нет домашнего телефона',
                    'email': email,
                    'address': address
                }

                if search_query in name.lower() or \
                        search_query in (work_phone or '').lower() or \
                        search_query in (home_phone or '').lower() or \
                        search_query in email.lower() or \
                        search_query in address.lower():
                    contacts.append(contact)

    return render_template('view.html', contacts=contacts, search_query=search_query)


@app.route('/edit/<int:index>', methods=['GET', 'POST'])
def edit_contact(index):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.vcf')
    contacts = []

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as file:
            contacts = list(vobject.readComponents(file.read()))

    if request.method == 'POST':
        if 0 <= index < len(contacts):
            vcard = contacts[index]

            vcard.fn.value = request.form['name']
            if hasattr(vcard, 'email'):
                vcard.email.value = request.form['email']
            else:
                vcard.add('email').value = request.form['email']

            if hasattr(vcard, 'tel'):
                for tel in vcard.contents['tel']:
                    if 'work' in tel.params.get('TYPE', []):
                        tel.value = request.form['work_phone']
                    elif 'home' in tel.params.get('TYPE', []):
                        tel.value = request.form['home_phone']
            else:
                vcard.add('tel').value = request.form['work_phone']
                vcard.contents['tel'][-1].params['TYPE'] = ['work']

                vcard.add('tel').value = request.form['home_phone']
                vcard.contents['tel'][-1].params['TYPE'] = ['home']

            if hasattr(vcard, 'adr'):
                vcard.adr.value.street = [request.form['address']]
            else:
                vcard.add('adr').value = vobject.vcard.Address(street=[request.form['address']])

            with open(filepath, 'w', encoding='utf-8') as file:
                file.writelines([vc.serialize() for vc in contacts])

        return redirect(url_for('view_contacts'))

    if 0 <= index < len(contacts):
        vcard = contacts[index]
        contact_data = {
            'name': vcard.fn.value if hasattr(vcard, 'fn') else '',
            'email': vcard.email.value if hasattr(vcard, 'email') else '',
            'work_phone': '',
            'home_phone': '',
            'address': ''
        }

        if hasattr(vcard, 'tel'):
            for tel in vcard.contents['tel']:
                if 'work' in tel.params.get('TYPE', []):
                    contact_data['work_phone'] = tel.value
                elif 'home' in tel.params.get('TYPE', []):
                    contact_data['home_phone'] = tel.value

        if hasattr(vcard, 'adr'):
            adr = vcard.adr.value
            contact_data['address'] = ', '.join(filter(None, [
                ' '.join(adr.street) if isinstance(adr.street, list) else adr.street,
                adr.city,
                adr.region,
                adr.code,
                adr.country
            ]))

        return render_template('edit.html', contact=contact_data, index=index)

    return redirect(url_for('view_contacts'))


@app.route('/export_vcf')
def export_vcf():
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.vcf')
    export_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'exported_contacts.vcf')

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as file:
            with open(export_filepath, 'w', encoding='utf-8') as export_file:
                export_file.write(file.read())

        return send_file(export_filepath, as_attachment=True, download_name='contacts.vcf')

    return redirect(url_for('view_contacts'))


@app.route('/export_csv')
def export_csv():
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.vcf')
    export_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.csv')
    contacts = []

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as file:
            vcf_data = file.read()
            for vcard in vobject.readComponents(vcf_data):
                name = vcard.fn.value if hasattr(vcard, 'fn') else 'Неизвестно'
                work_phone = None
                home_phone = None
                email = vcard.email.value if hasattr(vcard, 'email') else 'Нет email'
                address = 'Нет адреса'

                if hasattr(vcard, 'tel'):
                    for tel in vcard.contents['tel']:
                        if 'work' in tel.params.get('TYPE', []):
                            work_phone = tel.value
                        elif 'home' in tel.params.get('TYPE', []):
                            home_phone = tel.value

                if hasattr(vcard, 'adr'):
                    adr = vcard.adr.value
                    address = ', '.join(filter(None, [
                        ' '.join(adr.street) if isinstance(adr.street, list) else adr.street,
                        adr.city,
                        adr.region,
                        adr.code,
                        adr.country
                    ]))

                contacts.append([name, work_phone, home_phone, email, address])

    with open(export_filepath, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Name', 'Work Phone', 'Home Phone', 'Email', 'Address'])
        writer.writerows(contacts)

    return send_file(export_filepath, as_attachment=True, download_name='contacts.csv')


if __name__ == '__main__':
    app.run(debug=True)
