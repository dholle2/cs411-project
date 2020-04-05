from flask import Flask, render_template, request, redirect
from flask_mysqldb import MySQL
import yaml

app = Flask(__name__)

# configure database
db = yaml.load(open('db.yaml'))
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

# mysql = MySQL(app)
mysql = MySQL()
mysql.init_app(app)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # fetch form data
        # userDetails = request.form
        airbnbDetails = request.form
        apartment_id = airbnbDetails['apartment_id']
        description = airbnbDetails['description']
        deposit = airbnbDetails['deposit']
        latitude = airbnbDetails['latitude']
        longitude = airbnbDetails['longitude']
        no_guests = airbnbDetails['no_guests']
        price = airbnbDetails['price']
        landlord = airbnbDetails['landlord']
        safety_rating = airbnbDetails['safety_rating']
        # name = userDetails['name']
        # email = userDetails['email']
        cur = mysql.connection.cursor()
        # cur.execute("INSERT INTO users(name, email) VALUES (%s, %s)",
        #     (name, email))
        cur.execute("INSERT INTO airbnb(apartment_id, description, deposit, latitude, longitude, no_guests, price, landlord, safety_rating) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (apartment_id, description, deposit, latitude, longitude, no_guests, price, landlord, safety_rating))
        mysql.connection.commit()
        cur.close()
        # return redirect('/users')
        return redirect('/airbnb')
    return render_template('index.html')

# @app.route('/users')
@app.route('/airbnb')
def users():
    cur = mysql.connection.cursor()
    # resultValue = cur.execute("SELECT * FROM users")
    resultValue = cur.execute("SELECT * FROM airbnb")
    # if resultValue > 0:
    #     userDetails = cur.fetchall()
    #     return render_template('users.html', userDetails=userDetails)
    if resultValue > 0:
        airbnbDetails = cur.fetchall()
        return render_template('airbnb.html', airbnbDetails=airbnbDetails)

if __name__ == '__main__':
    app.run(debug=True)
