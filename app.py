from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask_cors import CORS
from flask_mysqldb import MySQL
from flask_bootstrap import Bootstrap
import yaml
from flask_sqlalchemy import SQLAlchemy

#import sys
#reload(sys)
#sys.setdefaultencoding("utf-8")

db = yaml.load(open('db.yaml'))
app = Flask(__name__)
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@127.0.0.1/airbnb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#app.config.from_pyfile('config.conf')

mysql = MySQL(app)
CORS(app)
# Bootstrap(app)
db2 = SQLAlchemy(app)

class Apartment(db2.Model):
    __tablename__ = 'apartment'

    # columns
    ID = db2.Column(db2.Integer, primary_key=True)
    Description = db2.Column(db2.String(250))
    Zipcode = db2.Column(db2.Integer)
    NumGuests = db2.Column(db2.Integer)
    Price = db2.Column(db2.Integer)
    Landlord = db2.Column(db2.String(50))
    SafetyRating = db2.Column(db2.Float)

    # 关系引用
    # books是给自己(Author模型)用的, author是给Book模型用的
    # books = db.relationship('Book', backref='author')

    def __repr__(self):
        return 'Apartment ID: %s Landord: %s' % (self.ID, self.Landlord)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin_search.html', methods=['GET', 'POST'])
def admin_search():
    results = []
    if request.method == 'POST':
        zipcode = request.form.get('zipcode')
        guest = request.form.get('guest')
        lowerprice = request.form.get('lowerprice')
        upperprice = request.form.get('upperprice')
        safety = request.form.get('safety')
        results = Apartment.query.all()
        if zipcode !='':
            results = Apartment.query.filter(Apartment.Zipcode==zipcode).all()
            if guest != '':
                results = Apartment.query.filter(Apartment.NumGuests==guest, Apartment.Zipcode==zipcode).all()
    return render_template('admin_search.html', results=results)

# search
@app.route('/user_search.html', methods=['GET', 'POST'])
def user_search():
    results = []
    if request.method == 'POST':
        zipcode = request.form.get('zipcode')
        guest = request.form.get('guest')
        lowerprice = request.form.get('lowerprice')
        upperprice = request.form.get('upperprice')
        safety = request.form.get('safety')
        results = Apartment.query.all()
        if zipcode !='':
            results = Apartment.query.filter(Apartment.Zipcode==zipcode).all()
            if guest != '':
                results = Apartment.query.filter(Apartment.NumGuests==guest, Apartment.Zipcode==zipcode).all()

    return render_template('user_search.html', results=results)

# delete data
@app.route('/admin_search.html/delete/<apartment_id>')
def delete_apartment(apartment_id):
    apartment = Apartment.query.get(apartment_id)
    db2.session.delete(apartment)
    db2.session.commit()
    return redirect(url_for('admin_search'))
# update data
@app.route('/admin_search.html/update/<apartment_id>', methods=['GET', 'POST'] )
def update_apartment(apartment_id):
    apartment = Apartment.query.get(apartment_id)
    if request.method == 'POST':
        id = request.form.get('ID')
        description = request.form.get('description')
        zipcode = request.form.get('zipcode')
        guest = request.form.get('guest')
        price = request.form.get('price')
        landlord = request.form.get('landlord')
        safety = request.form.get('safety')
        apartment.ID = id
        apartment.Description = description
        apartment.Zipcode = zipcode
        apartment.NumGuests = guest
        apartment.Price = price
        apartment.Landlord = landlord
        apartment.SafetyRating = safety
        db2.session.commit()
        return redirect(url_for('admin_search'))
    return render_template('update.html', apartment=apartment)

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
    db2.drop_all()
    db2.create_all()

    # 生成数据
    ap1 = Apartment(ID=1, Description='NICE', Zipcode=61820, NumGuests=3, Price=1000, Landlord='Jack', SafetyRating=5.8)
    ap2 = Apartment(ID=2, Description='good', Zipcode=91798, NumGuests=1, Price=200, Landlord='Rose', SafetyRating=4.3)
    ap3 = Apartment(ID=3, Description='great', Zipcode=91798, NumGuests=2, Price=500, Landlord='Mike', SafetyRating=5.3)
    # 把数据提交给用户会话
    db2.session.add_all([ap1,ap2,ap3])
    # 提交会话
    db2.session.commit()

    app.run(debug=True)
