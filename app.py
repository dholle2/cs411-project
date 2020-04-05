from flask import Flask, render_template, request, redirect, jsonify
from flask_cors import CORS
from flask_mysqldb import MySQL
import yaml

db = yaml.load(open('db.yaml'))
app = Flask(__name__)
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(app)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data', methods = ['GET', 'POST'])
def data():
    if request.method == 'POST':
        body = request.json
        description = body['description']
        deposit = body['deposit']
        latitude = body['latitude']
        longitude = body['longitude']
        num_guests = body['num_guests']
        price = body['price']
        landlord = body['landlord']
        safety_rating = body['safety_rating']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO listings VALUES(null, %s, %s, %s, %s, %s, %s, %s, %s)", (str(description), deposit, latitude, longitude, num_guests, price, str(landlord), safety_rating))
        mysql.connection.commit()
        cur.close()
        return jsonify({
            'description': description,
            'deposit': deposit,
            'latitude': latitude,
            'longitude': longitude,
            'num_guests': num_guests,
            'price': price,
            'landlord': landlord,
            'safety_rating': safety_rating
        })
    if request.method == 'GET':
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM listings')
        listings = cursor.fetchall()
        res = []

        for i in range(len(listings)):
            id = listings[i][0]
            description = listings[i][1]
            deposit = listings[i][2]
            latitude = listings[i][3]
            longitude = listings[i][4]
            num_guests = listings[i][5]
            price = listings[i][6]
            landlord = listings[i][7]
            safety_rating = listings[i][8]
            dataDict = {
                "id": id,
                "description": description,
                "deposit": deposit,
                "latitude": latitude,
                "longitude": longitude,
                "num_guests": num_guests,
                "price": price,
                "landlord": landlord,
                "safety_rating": safety_rating
            }
            res.append(dataDict)

        return jsonify(res)

@app.route('/data/<string:id>', methods=['GET', 'DELETE', 'PUT'])
def single(id):

    if request.method == 'GET':
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM listings WHERE id = %s', (id))
        listings = cursor.fetchall()
        print(listings)
        data = []
        for i in range(len(listings)):
            id = listings[i][0]
            description = listings[i][1]
            deposit = listings[i][2]
            latitude = listings[i][3]
            longitude = listings[i][4]
            num_guests = listings[i][5]
            price = listings[i][6]
            landlord = listings[i][7]
            safety_rating = listings[i][8]
            dataDict = {
                "id": id,
                "description": description,
                "deposit": deposit,
                "latitude": latitude,
                "longitude": longitude,
                "num_guests": num_guests,
                "price": price,
                "landlord": landlord,
                "safety_rating": safety_rating
            }
            data.append(dataDict)
        return jsonify(data)
        
    if request.method == 'DELETE':
        cursor = mysql.connection.cursor()
        cursor.execute('DELETE FROM listings WHERE id = %s', (id))
        mysql.connection.commit()
        cursor.close()
        return jsonify({'status': 'Data '+id+' is deleted from the database.'})

    if request.method == 'PUT':
        body = request.json
        description = body['description']
        deposit = body['deposit']
        latitude = body['latitude']
        longitude = body['longitude']
        num_guests = body['num_guests']
        price = body['price']
        landlord = body['landlord']
        safety_rating = body['safety_rating']

        cursor = mysql.connection.cursor()
        cursor.execute('UPDATE listings SET description = %s, deposit = %s, latitude = %s, longitude = %s, num_guests = %s, price = %s, landlord = %s, safety_rating = %s WHERE id = %s', (description, deposit, latitude, longitude, num_guests, price, landlord, safety_rating, id))
        mysql.connection.commit()
        cursor.close()
        return jsonify({'status': 'Data '+id+' is updated in the database.'})
if __name__ == '__main__':
    app.run(debug=True)