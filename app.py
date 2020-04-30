from typing import Union

from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, get_flashed_messages
from flask_cors import CORS
from flask_mysqldb import MySQL
from flask_bootstrap import Bootstrap
import yaml
from flask_sqlalchemy import SQLAlchemy
from flask_pymongo import PyMongo
from pygeodesy import ellipsoidalVincenty as ev
from pymongo import MongoClient
import pymysql
import pandas as pd
from sodapy import Socrata
from datetime import datetime
import re
#from sqlalchemy import or_,and_

#import sys
#reload(sys)
#sys.setdefaultencoding("utf-8")

db = yaml.load(open('db.yaml'))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'cs411'
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@127.0.0.1/airbnb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# mongodb
app.config['MONGO_URI'] = 'mongodb+srv://user1:user1password@cluster0-9dppt.mongodb.net/crimedata?retryWrites=true&w=majority'
#app.config.from_pyfile('config.conf')

mysql = MySQL(app)
mongo = PyMongo(app)
crimes = mongo.db['crimeRecords']
CORS(app)
# Bootstrap(app)
db2 = SQLAlchemy(app)
#mongo.db.users.insert({'name':name, 'email':email})
#mongo.db.users.find({"online": True})


#create table
class Apartment(db2.Model):
    __tablename__ = 'apartment'
    # columns
    ID = db2.Column(db2.Integer, primary_key=True)
    Description = db2.Column(db2.String(200))
    # Zipcode = db2.Column(db2.Integer)
    Latitude = db2.Column(db2.Float)
    Longitude = db2.Column(db2.Float)
    NumGuests = db2.Column(db2.Integer)
    Price = db2.Column(db2.Integer)
    Landlord = db2.Column(db2.String(50))
    SafetyRating = db2.Column(db2.Float)

    def __repr__(self):
        return 'Apartment ID: %s Landord: %s' % (self.ID, self.Landlord)
"""
#search
mycol = mongo.db[collection_name]
mycol.find_one(conditions_dic)
mycol.find(conditions_dic).sort([order_rule]).skip(page_num*(page_num-1)).limit(page_size)
#update
mycol.update(conditions_dic,{'$set':data_dic}, multi=multi_field_update)
mycol.update(conditions_dic, {'$set': data_dic})
#insert
mycol.insert(data_dic)
delete
mycol.delete_many
mycol.delete_one
"""

def cal_safety(apartment:list, crimes:list):
    """
    To calculate safety rating of apartment
    :param apartment: a row from table apartment in list format
    :param crimes: a collection in list format
    :return:
    """

    crime_score = {'ARSON': 8, 'ASSAULT': 8, 'BATTERY': 8, 'BURGLARY': 7, 'CONCEALED CARRY LICENSE VIOLATION': 5,
                   'CRIM SEXUAL ASSAULT': 8, 'CRIMINAL DAMAGE': 5, 'CRIMINAL SEXUAL ASSAULT': 8, 'CRIMINAL TRESPASS': 7,
                   'DECEPTIVE PRACTICE': 5, 'GAMBLING': 5, 'HOMICIDE': 10, 'HUMAN TRAFFICKING': 9,
                   'INTERFERENCE WITH PUBLIC OFFICER': 5,
                   'INTIMIDATION': 7, 'KIDNAPPING': 9, 'LIQUOR LAW VIOLATION': 3, 'MOTOR VEHICLE THEFT': 5,
                   'NARCOTICS': 6,
                   'OBSCENITY': 5, 'OFFENSE INVOLVING CHILDREN': 8, 'OTHER NARCOTIC VIOLATION': 6, 'OTHER OFFENSE': 5,
                   'PROSTITUTION': 5, 'PUBLIC INDECENCY': 5, 'PUBLIC PEACE VIOLATION': 5, 'ROBBERY': 6,
                   'SEX OFFENSE': 7,
                   'STALKING': 6, 'THEFT': 5, 'WEAPONS VIOLATION': 5, 'PUBLIC PEACE VIOLATION': 7, 'RITUALISM': 5,
                   'NON-CRIMINAL': 1, 'CRIMINAL ABORTION': 1
                   }
    total_score = 0
    for crime in crimes:
        start = ev.LatLon(apartment[2], apartment[3])
        end = ev.LatLon(crime['latitude'], crime['longitude'])
        distance = float(start.distanceTo(end))  # meter
        if distance > 3000:
            continue
        base_score = crime_score[crime['primary_type']]
        arrest_leverage = 1 if crime['arrest'] else 1.5
        '''     
        if crime['frequency'] > 5:
            fre_leverage = 2
        elif crime['frequency'] <= 2:
            fre_leverage = 1
        else:
            fre_leverage = 1.5
        score = base_score * arrest_leverage * fre_leverage
        '''
        score = base_score * arrest_leverage * crime['frequency']
        total_score += score
    rating = round(10 - total_score / 100, 2)
    return rating



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/database.html')
def database():
    return render_template('database.html')

@app.route('/admin_mongo.html/calculate')
def reset_safety():
    cur = mysql.connection.cursor()
    results = cur.execute("SELECT * FROM apartment")
    if results > 0:
        resultsDetails = cur.fetchall()
    crime_records = list(crimes.find({}))
    for apartment in resultsDetails:
        rating = cal_safety(apartment, crime_records)
        cur.execute("update apartment set SafetyRating = %s where ID = %s", (rating, apartment[0]))
        mysql.connection.commit()
    cur.close()
    flash('Calculation Completed')
    return redirect(url_for('admin_mongo'))

@app.route('/admin_mongo.html/import')
def import_data():
    client = Socrata("data.cityofchicago.org", None)
    results = client.get("qzdf-xmn8", limit=1000)
    results_df = pd.DataFrame.from_records(results,
                                           exclude=['location', 'district', 'block', 'y_coordinate', 'description',
                                                    'location_description', 'updated_on', 'community_area',
                                                    'iucr', 'x_coordinate', 'ward', 'year', 'domestic', 'fbi_code',
                                                    'beat', 'id'])
    # convert datatype
    results_df['date'] = results_df['date'].str.slice(0, 10)
    # results_df['date'] = pd.to_datetime(results_df['date'].str.slice(0,10))
    results_df['latitude'] = results_df['latitude'].astype(float)
    results_df['longitude'] = results_df['longitude'].astype(float)
    results_df['case_number'] = results_df['case_number'].astype(str)
    results_df['primary_type'] = results_df['primary_type'].astype(str)
    results_df.dropna(axis=0, how='any', inplace=True)
    results_group = results_df.groupby(['latitude', 'longitude', 'primary_type', 'arrest'])
    crime_records = []
    i = 1
    for k, v in results_group:
        each_record = {}
        detail = []
        each_record['_id'] = i
        i += 1
        each_record['latitude'] = k[0]
        each_record['longitude'] = k[1]
        each_record['primary_type'] = k[2]
        each_record['arrest'] = k[3]
        each_record['frequency'] = v.shape[0]
        for j in range(v.shape[0]):
            each_crime = {}
            each_crime['case_number'] = v.iloc[j, 2]
            # each_crime['date']=pd.Timestamp.date(v.iloc[j,0])
            each_crime['date'] = datetime.strptime(v.iloc[j, 0], '%Y-%m-%d')
            # each_crime['date'] = v.iloc[j,0]
            detail.append(each_crime)
            each_record['detail'] = detail
        crime_records.append(each_record)
    crimes.delete_many({})
    crimes.insert_many(crime_records)
    flash('Finished')
    return redirect(url_for('admin_mongo'))


# mongodb CRUD
@app.route('/admin_mongo.html', methods=['GET', 'POST'])
def admin_mongo():
    results = []
    bool = {'yes':True, 'no':False}
    if request.method == 'POST':
        if 'search_listing' in request.form:
            ID = request.form.get('ID')
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            type = request.form.get('type')
            arrest = request.form.get('arrest')
            frequency = request.form.get('frequency')
            #caseNo = request.form.get('caseNo')
            #date = request.form.get('date')

            condition = {}
            if ID:
                condition['_id'] = int(ID)
            if latitude:
                condition['latitude'] = float(latitude)
            if longitude:
                condition['longitude'] = float(longitude)
            #if caseNo:
                #condition['Case Number'] = caseNo
            #if date:
                #condition['Date'] = date
            if type:
                condition['primary_type'] = type
            if arrest:
                condition['arrest'] = bool[arrest]
                #condition['arrest'] = True
            if frequency:
                condition['frequency'] = int(frequency)
            resultsDetails=crimes.find(condition)
            return render_template('admin_mongo.html', results=resultsDetails)
        if 'new_listing' in request.form:
            ID = request.form.get('ID')
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            type = request.form.get('type')
            arrest = request.form.get('arrest')
            frequency = request.form.get('frequency')
            caseNo = request.form.getlist('caseNo')
            date = request.form.getlist('date')
            detail = []
            for i in range(len(caseNo)):
                record = {}
                if caseNo[i] and date[i]:
                    record['case_number'] = caseNo[i]
                    record['date'] = datetime.strptime(date[i], '%Y-%m-%d')
                    detail.append(record)
            crimes.insert({'_id': int(ID), 'latitude': float(latitude), 'longitude': float(longitude), 'primary_type':type,
                           'arrest': bool[arrest], 'frequency':int(frequency), 'detail': detail})
    return render_template('admin_mongo.html', results=results)

@app.route('/admin_mongo.html/delete/<crime_id>')
def delete_crime(crime_id):
    crimes.remove({'_id':int(crime_id)})
    return redirect(url_for('admin_mongo'))

@app.route('/admin_mongo.html/update/<crime_id>', methods=['GET', 'POST'] )
def update_crime(crime_id):
    crime=crimes.find({'_id': int(crime_id)})
    bool = bool = {'yes':True, 'no':False, 'true':True, 'false':False}
    if request.method == 'POST':
        ID = request.form.get('ID')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        type = request.form.get('type')
        arrest = request.form.get('arrest').lower()
        frequency = request.form.get('frequency')
        caseNo = request.form.getlist('caseNo')
        date = request.form.getlist('date')
        detail = []
        for i in range(len(caseNo)):
            record = {}
            if caseNo[i] and date[i]:
                record['case_number'] = caseNo[i]
                record['date'] = datetime.strptime(date[i][0:10], '%Y-%m-%d')
                detail.append(record)
        crimes.update({'_id': int(crime_id)}, {'$set':{'_id': int(ID), 'latitude': float(latitude), 'longitude': float(longitude), 'primary_type':type,
                          'arrest': bool[arrest], 'frequency':int(frequency), 'detail': detail}})
        return redirect(url_for('admin_mongo'))
    return render_template('mongo_update.html', crime=crime)

#search & insert
@app.route('/admin_search.html', methods=['GET', 'POST'])
def admin_search():
    results = []
    #latitude = request.form.get('latitude')
    #longitude = request.form.get('longitude')
    #flash(str(longitude))

    latitude2 = request.values.get('latitudeInsert','')
    longitude2 = request.values.get('longitudeInsert','')
    flash(latitude2)
    if request.method == 'POST':
        if 'search_listing' in request.form:
            # zipcode = request.form.get('zipcode')
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            guest = request.form.get('guest')
            lowerprice = request.form.get('lowerprice')
            upperprice = request.form.get('upperprice')
            safety = request.form.get('safety')
            landlord = request.form.get('landlord')
            description = request.form.get('description')
            id = ''
            condition = ["ID != %s"]
            para = [id]
            # if zipcode:
            #     condition.append("Zipcode=%s")
            #     para.append(int(zipcode))
            if latitude:
                condition.append("Latitude=%s")
                para.append(float(latitude))
            if longitude:
                condition.append("Longitude=%s")
                para.append((float(longitude)))
            if guest:
                condition.append("NumGuests=%s")
                para.append(int(guest))
            if lowerprice:
                condition.append("Price>=%s")
                para.append(int(lowerprice))
            if upperprice:
                condition.append("Price<=%s")
                para.append(int(upperprice))
            if safety:
                condition.append("SafetyRating>=%s")
                para.append(float(safety))
            if landlord:
                condition.append("Landlord  LIKE %s")
                para.append('%' + landlord + '%')
            if description:
                condition.append("Description LIKE %s")
                para.append('%' + description + '%')
            cur = mysql.connection.cursor()
            results = cur.execute("SELECT * FROM apartment WHERE " + " AND ".join(condition), para)
            if results > 0:
                resultsDetails = cur.fetchall()
            else:
                resultsDetails = []
            return render_template('admin_search.html', results=resultsDetails)
        if 'new_listing' in request.form:
            listingDetails = request.form
            description = listingDetails['description']
            # zipcode = listingDetails['zipcode']
            latitude = listingDetails['latitude']
            longitude = listingDetails['longitude']
            num_guests = listingDetails['num_guests']
            price = listingDetails['price']
            landlord = listingDetails['landlord']
            safety_rating = listingDetails['safety']

            cur = mysql.connection.cursor()
            # cur.execute("INSERT INTO apartment VALUES(null, %s, %s, %s, %s, %s, %s)", (str(description), zipcode, num_guests, price, str(landlord), safety_rating))
            cur.execute("INSERT INTO apartment VALUES(null, %s, %s, %s, %s, %s, %s, %s)", (str(description), latitude, longitude, num_guests, price, str(landlord), safety_rating))
            mysql.connection.commit()
            cur.close()
    return render_template('admin_search.html', results=results, lati=latitude2, longi=longitude2)

@app.route('/user_search.html/<latitude>&<longitude>')
def coordinate_safety(latitude, longitude):
    if latitude and longitude:
        crime_records = list(crimes.find({}))
        apartment = [0, 0, float(latitude), float(longitude)]
        rating = cal_safety(apartment, crimes=crime_records)
        flash('The safety rating of coordinate ({}, {}) is {}'.format(latitude,longitude, rating))
    else:
        flash('Please input valid coordinate')
    return redirect(url_for('admin_search'))

# search
@app.route('/user_search.html', methods=['GET', 'POST'])
def user_search():
    results = []
    if request.method == 'POST':
        # zipcode = request.form.get('zipcode')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        guest = request.form.get('guest')
        lowerprice = request.form.get('lowerprice')
        upperprice = request.form.get('upperprice')
        safety = request.form.get('safety')
        landlord = request.form.get('landlord')
        #description = request.form.get('description')
        id=''
        condition = ["ID != %s"]
        para = [id]
        # if zipcode:
        #     condition.append("Zipcode=%s")
        #     para.append(int(zipcode))
        if guest:
            condition.append("NumGuests=%s")
            para.append(int(guest))
        if lowerprice:
            condition.append("Price>=%s")
            para.append(int(lowerprice))
        if upperprice:
            condition.append("Price<=%s")
            para.append(int(upperprice))
        if safety:
            condition.append("SafetyRating>=%s")
            para.append(float(safety))
        if landlord:
            condition.append("Landlord  LIKE %s")
            para.append('%'+landlord+'%')
        #if description:
            #condition.append("Description LIKE %s")
            #para.append('%'+description+'%')
        cur = mysql.connection.cursor()
        results = cur.execute("SELECT * FROM apartment WHERE " + " AND ".join(condition), para)
        if results > 0:
            resultsDetails = cur.fetchall()
        else:
            resultsDetails = []
        return render_template('user_search.html', results=resultsDetails)
    return render_template('user_search.html', results=results)

# delete data
@app.route('/admin_search.html/delete/<apartment_id>')
def delete_apartment(apartment_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM apartment WHERE ID=(%s)", apartment_id)
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('admin_search'))

# update data
@app.route('/admin_search.html/update/<apartment_id>', methods=['GET', 'POST'] )
def update_apartment(apartment_id):
    cur = mysql.connection.cursor()
    results = cur.execute("SELECT * FROM apartment WHERE ID=%s", apartment_id)
    apartment=cur.fetchone()
    if request.method == 'POST':
        id = request.form.get('ID')
        description = request.form.get('description')
        # zipcode = request.form.get('zipcode')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        guest = request.form.get('guest')
        price = request.form.get('price')
        landlord = request.form.get('landlord')
        safety = request.form.get('safety')
        cur = mysql.connection.cursor()
        # cur.execute("UPDATE apartment SET ID=%s, Description=%s, Zipcode=%s, NumGuests=%s, Price=%s, Landlord=%s, SafetyRating=%s WHERE ID=(%s)",
        #             (id, description, zipcode, guest, price, landlord, safety, apartment_id))
        cur.execute("UPDATE apartment SET ID=%s, Description=%s, Latitude=%s, Longitude=%s, NumGuests=%s, Price=%s, Landlord=%s, SafetyRating=%s WHERE ID=(%s)",
                    (id, description, latitude, longitude, guest, price, landlord, safety, apartment_id))
        mysql.connection.commit()
        cur.close()
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


    # ap1 = Apartment(ID=1, Description='NICE', Zipcode=61820, NumGuests=3, Price=1000, Landlord='Jack', SafetyRating=5.8)
    # ap2 = Apartment(ID=2, Description='good', Zipcode=91798, NumGuests=1, Price=200, Landlord='Rose', SafetyRating=4.3)
    # ap3 = Apartment(ID=3, Description='great', Zipcode=91798, NumGuests=2, Price=500, Landlord='Mike', SafetyRating=5.3)

    # db2.session.add_all([ap1,ap2,ap3])

    ap2 = Apartment(ID=1, Description='Modern Boystown/Wrigleyville 1 BDRM', Latitude=41.9488427926778, Longitude=-87.6490462233825, NumGuests=3, Price=103, Landlord='Michael', SafetyRating=0.0)
    ap3 = Apartment(ID=2, Description='The Best Location in Downtown Chi!', Latitude=41.8904217387672, Longitude=-87.6320817379974, NumGuests=2, Price=99, Landlord='Kelsea', SafetyRating=0.0)
    ap4 = Apartment(ID=3, Description='Clean, Cozy and Close to Everything', Latitude=41.8947327399715, Longitude=-87.6815375437123, NumGuests=1, Price=70, Landlord='Mindy', SafetyRating=0.0)
    ap5 = Apartment(ID=4, Description='Fantastic River North Location 2b-6', Latitude=41.8918919402708, Longitude=-87.6280437024356, NumGuests=4, Price=559, Landlord='Justin', SafetyRating=0.0)
    ap6 = Apartment(ID=5, Description='Cozy Apt - Perfect Chicago Getaway!', Latitude=41.870501750455, Longitude=-87.6291252608363, NumGuests=2, Price=160, Landlord='James', SafetyRating=0.0)
    ap7 = Apartment(ID=6, Description='Bucktown - Private Room', Latitude=41.9223374616782, Longitude=-87.687003258889, NumGuests=2, Price=75, Landlord='Carrie & Brad', SafetyRating=0.0)
    ap8 = Apartment(ID=7, Description='West Town Walkable - near Blue Line', Latitude=41.8945151195157, Longitude=-87.6642306273441, NumGuests=8, Price=499, Landlord='Erik', SafetyRating=0.0)
    ap9 = Apartment(ID=8, Description='Spacious town home in Wicker Park', Latitude=41.8974663287093, Longitude=-87.6639730626217, NumGuests=4, Price=200, Landlord='Jen', SafetyRating=0.0)
    ap10 = Apartment(ID=9, Description='Awesome Wrigleyville location #Cubs', Latitude=41.9481876675722, Longitude=-87.6579297378243, NumGuests=2, Price=200, Landlord='Jarrad', SafetyRating=0.0)
    ap11 = Apartment(ID=10, Description='Goose & Fox Hostel Lincoln Park', Latitude=41.9172721863165, Longitude=-87.6533371940492, NumGuests=2, Price=100, Landlord='Greg', SafetyRating=0.0)
    ap12 = Apartment(ID=11, Description='Spacious Apartment in Lincoln Park', Latitude=41.9249189440732, Longitude=-87.6633719358951, NumGuests=2, Price=50, Landlord='David', SafetyRating=0.0)
    ap13 = Apartment(ID=12, Description='The best bedroom in Lincoln Park', Latitude=41.9193962573672, Longitude=-87.6519221891464, NumGuests=1, Price=150, Landlord='Ariel', SafetyRating=0.0)
    ap14 = Apartment(ID=13, Description='Spacious townhome on 3 plus levels', Latitude=41.9384760974722, Longitude=-87.6936551396525, NumGuests=4, Price=235, Landlord='Daniel', SafetyRating=0.0)
    ap15 = Apartment(ID=14, Description='Sunny Logan Square Apartment', Latitude=41.9331317627868, Longitude=-87.7041159144061, NumGuests=2, Price=35, Landlord='David', SafetyRating=0.0)
    ap16 = Apartment(ID=15, Description='Gorgeous Lincoln Square Two-Level', Latitude=41.969459243438, Longitude=-87.6952315747796, NumGuests=4, Price=215, Landlord='Lisa', SafetyRating=0.0)
    ap17 = Apartment(ID=16, Description='Huge Basement Loft in Logan Square', Latitude=41.9206466629941, Longitude=-87.7009338548145, NumGuests=5, Price=175, Landlord='Davis', SafetyRating=0.0)
    ap18 = Apartment(ID=17, Description='Ideal Location in Logan Square 1BR', Latitude=41.9239075173728, Longitude=-87.7034582340815, NumGuests=2, Price=115, Landlord='Jake', SafetyRating=0.0)
    ap19 = Apartment(ID=18, Description='1BR Downtown VIEW of John Hancock', Latitude=41.9046318972259, Longitude=-87.6315909729437, NumGuests=2, Price=150, Landlord='Hollie', SafetyRating=0.0)
    ap20 = Apartment(ID=19, Description='Room in wicker park town home', Latitude=41.8986568035934, Longitude=-87.6659186930603, NumGuests=2, Price=100, Landlord='Jen', SafetyRating=0.0)
    ap21 = Apartment(ID=20, Description='Cozy Ukrainian Village Apt 10 minutes to downtown', Latitude=41.8970896171509, Longitude=-87.6808223052727, NumGuests=2, Price=46, Landlord='Lindsey', SafetyRating=0.0)
    ap22 = Apartment(ID=21, Description='Buona Sera in Chicago\'s Beautiful Little Italy! 1', Latitude=41.8712994427934, Longitude=-87.653051651207, NumGuests=5, Price=100, Landlord='Keval', SafetyRating=0.0)
    ap23 = Apartment(ID=22, Description='Lovely Apartment in Logan Square', Latitude=41.9256144771644, Longitude=-87.7049263811894, NumGuests=6, Price=150, Landlord='Sam', SafetyRating=0.0)
    ap24 = Apartment(ID=23, Description='Private Bedroom in New Apartment', Latitude=41.8965814787056, Longitude=-87.6955558709854, NumGuests=2, Price=89, Landlord='Joe', SafetyRating=0.0)
    ap25 = Apartment(ID=24, Description='Queen Bunk Beds + Walk In Closet', Latitude=41.9068377687123, Longitude=-87.6897392166697, NumGuests=3, Price=60, Landlord='Zac', SafetyRating=0.0)
    ap26 = Apartment(ID=25, Description='5 Star Reviews! The Blackhawk Tavern - Wicker Park', Latitude=41.9062073303146, Longitude=-87.6704473842338, NumGuests=4, Price=99, Landlord='Dan', SafetyRating=0.0)
    ap27 = Apartment(ID=26, Description='Private bed&bath in Ukrainian Vlg.', Latitude=41.8982114921167, Longitude=-87.6696211737136, NumGuests=2, Price=110, Landlord='Bijou', SafetyRating=0.0)
    ap28 = Apartment(ID=27, Description='Top Floor Corner Loft', Latitude=41.876801022553, Longitude=-87.6453354617965, NumGuests=6, Price=600, Landlord='Conner', SafetyRating=0.0)
    ap29 = Apartment(ID=28, Description='Beautiful South Loop Surprise', Latitude=41.8665477529775, Longitude=-87.6280752998688, NumGuests=4, Price=149, Landlord='Kemi', SafetyRating=0.0)
    ap30 = Apartment(ID=29, Description='Fantastic River North Location!-s3', Latitude=41.8905623450788, Longitude=-87.6264892392425, NumGuests=2, Price=359, Landlord='Justin', SafetyRating=0.0)
    ap31 = Apartment(ID=30, Description='Fantastic River North Location 2b-9', Latitude=41.891915438934, Longitude=-87.6276981586578, NumGuests=4, Price=559, Landlord='Justin', SafetyRating=0.0)
    ap32 = Apartment(ID=31, Description='Welcome home at Wrigleyville', Latitude=41.9432151126285, Longitude=-87.6492969928248, NumGuests=6, Price=130, Landlord='Ricardo', SafetyRating=0.0)
    ap33 = Apartment(ID=32, Description='Newly Renovated Lakeview Penthouse!', Latitude=41.9411690634429, Longitude=-87.6704382877756, NumGuests=2, Price=175, Landlord='Matthew', SafetyRating=0.0)
    ap34 = Apartment(ID=33, Description='Fantastic River North Location (5)', Latitude=41.8904268354961, Longitude=-87.6289626788668, NumGuests=2, Price=429, Landlord='Justin', SafetyRating=0.0)
    ap35 = Apartment(ID=34, Description='Perfect Wicker Park Apartment', Latitude=41.9010540169813, Longitude=-87.6657617493098, NumGuests=3, Price=65, Landlord='Travis', SafetyRating=0.0)
    ap36 = Apartment(ID=35, Description='Stylish & Updated 2 Bed', Latitude=41.9926693097296, Longitude=-87.6618967045403, NumGuests=6, Price=320, Landlord='Michael', SafetyRating=0.0)
    ap37 = Apartment(ID=36, Description='Spacious, sunny apartment in Ravenswood.', Latitude=41.9704373392664, Longitude=-87.6742918213979, NumGuests=2, Price=200, Landlord='Paul & Andrew', SafetyRating=0.0)
    ap38 = Apartment(ID=37, Description='One Bed Gold Coast Gem', Latitude=41.9084741497638, Longitude=-87.6295161450836, NumGuests=2, Price=200, Landlord='Molly', SafetyRating=0.0)
    ap39 = Apartment(ID=38, Description='Fantastic River North Location 2b-2', Latitude=41.8921731453877, Longitude=-87.6275016320104, NumGuests=4, Price=559, Landlord='Justin', SafetyRating=0.0)
    ap40 = Apartment(ID=39, Description='Top Floor Unit In Gold Coast! Close to Everything!', Latitude=41.9008604963031, Longitude=-87.6256485481321, NumGuests=2, Price=120, Landlord='Mali', SafetyRating=0.0)
    ap41 = Apartment(ID=40, Description='Comfortable and tranquil', Latitude=41.9976975948026, Longitude=-87.7016642795539, NumGuests=1, Price=45, Landlord='Lyz', SafetyRating=0.0)
    ap42 = Apartment(ID=41, Description='Charming bohemian duplex w King bed', Latitude=41.9213603089876, Longitude=-87.6994159066212, NumGuests=3, Price=110, Landlord='Masumi', SafetyRating=0.0)
    ap43 = Apartment(ID=42, Description='Bucktown Studio Apartment', Latitude=41.9176999259705, Longitude=-87.6721427104518, NumGuests=2, Price=92, Landlord='Anthony', SafetyRating=0.0)
    ap44 = Apartment(ID=43, Description='Stylish & Artsy Room in Vintage Chicago Flat', Latitude=41.915151010003, Longitude=-87.6879114158141, NumGuests=2, Price=45, Landlord='April', SafetyRating=0.0)
    ap45 = Apartment(ID=44, Description='Gorgeous Apartment in Chicago', Latitude=41.9009421315186, Longitude=-87.6836781824253, NumGuests=8, Price=211, Landlord='Tamara', SafetyRating=0.0)
    ap46 = Apartment(ID=45, Description='Private bed/bath in Wicker Park', Latitude=41.9016175743859, Longitude=-87.6711745255904, NumGuests=1, Price=95, Landlord='Vijay', SafetyRating=0.0)
    ap47 = Apartment(ID=46, Description='Cozy n affordable place to sleep n relax..', Latitude=41.8027139628661, Longitude=-87.584609411552, NumGuests=2, Price=76, Landlord='Cleo', SafetyRating=0.0)
    ap48 = Apartment(ID=47, Description='Stylish, comfortable 1br', Latitude=41.954823470566, Longitude=-87.7130922809161, NumGuests=2, Price=95, Landlord='Artur', SafetyRating=0.0)
    ap49 = Apartment(ID=48, Description='Beautiful Logan Square Home', Latitude=41.9331232973597, Longitude=-87.7080869289025, NumGuests=5, Price=199, Landlord='Tawni And Sam', SafetyRating=0.0)
    ap50 = Apartment(ID=49, Description='one bedroom in townhouse', Latitude=41.9402910457156, Longitude=-87.6953030905725, NumGuests=2, Price=90, Landlord='Daniel', SafetyRating=0.0)
    ap51 = Apartment(ID=50, Description='The Attic on Avers near Blue Line', Latitude=41.9336162631253, Longitude=-87.7225192252334, NumGuests=2, Price=64, Landlord='Jeffry And Bob', SafetyRating=0.0)
    ap52 = Apartment(ID=51, Description='Spacious 2 bedroom apartment with laundry', Latitude=41.9466683409093, Longitude=-87.6616114133544, NumGuests=4, Price=175, Landlord='Juliet', SafetyRating=0.0)
    ap53 = Apartment(ID=52, Description='Large 2 bed 1st floor apt. 50 yards from Wrigley!', Latitude=41.9488071355184, Longitude=-87.6564258744279, NumGuests=8, Price=800, Landlord='Matthew', SafetyRating=0.0)
    ap54 = Apartment(ID=53, Description='Fantastic River North Location (0)', Latitude=41.8908001776941, Longitude=-87.628529953139, NumGuests=2, Price=429, Landlord='Justin', SafetyRating=0.0)
    ap55 = Apartment(ID=54, Description='2 BD Condo by downtown,park,lake', Latitude=41.9030231542809, Longitude=-87.6349893180336, NumGuests=4, Price=137, Landlord='Marv', SafetyRating=0.0)
    ap56 = Apartment(ID=55, Description='Spacious, Charming Hyde Park Condo', Latitude=41.8096478052537, Longitude=-87.6001491922461, NumGuests=5, Price=155, Landlord='Roxanne', SafetyRating=0.0)
    ap57 = Apartment(ID=56, Description='Woodsy Hyde Park Getaway', Latitude=41.8072327725457, Longitude=-87.6015897339566, NumGuests=2, Price=55, Landlord='Sharla', SafetyRating=0.0)
    ap58 = Apartment(ID=57, Description='CUBS,DELUXE, CHIC TERRACED DUPLEX LOFT, TOP LOCALE', Latitude=41.9331386185564, Longitude=-87.6682609912436, NumGuests=1, Price=65, Landlord='Sam And Amy', SafetyRating=0.0)
    ap59 = Apartment(ID=58, Description='Modern Private br/ba Logan Square', Latitude=41.9230536860407, Longitude=-87.7266865506352, NumGuests=4, Price=60, Landlord='Mo', SafetyRating=0.0)
    ap60 = Apartment(ID=59, Description='UPTOWN ROW HOUSE-SPACIOUS PRIVATE SHARED ROOM(S)', Latitude=41.9665427109946, Longitude=-87.6570154577907, NumGuests=5, Price=85, Landlord='Tomasso', SafetyRating=0.0)
    ap61 = Apartment(ID=60, Description='Fantastic River North Location! (13)', Latitude=41.8905425028868, Longitude=-87.6282136944457, NumGuests=2, Price=399, Landlord='Justin', SafetyRating=0.0)
    ap62 = Apartment(ID=61, Description='Fantastic River North Location (8)', Latitude=41.8902618870088, Longitude=-87.6285115394938, NumGuests=2, Price=429, Landlord='Justin', SafetyRating=0.0)
    ap63 = Apartment(ID=62, Description='Luxury room in Wrigleyville!', Latitude=41.9538342604035, Longitude=-87.6686378728699, NumGuests=2, Price=100, Landlord='Maurizio', SafetyRating=0.0)
    ap64 = Apartment(ID=63, Description='LargeApt2blksFrmTrains+Rstrnts+Bars', Latitude=41.9209034179288, Longitude=-87.6557789419183, NumGuests=4, Price=80, Landlord='Robert', SafetyRating=0.0)
    ap65 = Apartment(ID=64, Description='2 BR Historic Home in Old Town', Latitude=41.9128137217068, Longitude=-87.6362769156137, NumGuests=4, Price=290, Landlord='Lori', SafetyRating=0.0)
    ap66 = Apartment(ID=65, Description='Cozy Pilsen Apartment', Latitude=41.8515887887677, Longitude=-87.6786480745101, NumGuests=2, Price=100, Landlord='Michael', SafetyRating=0.0)
    ap67 = Apartment(ID=66, Description='Vintage Modern Apt. in Pilsen', Latitude=41.850820071608, Longitude=-87.6811848599066, NumGuests=2, Price=90, Landlord='Alicia', SafetyRating=0.0)
    ap68 = Apartment(ID=67, Description='Private room in awesome Pilsen area', Latitude=41.8587426241515, Longitude=-87.6470233679281, NumGuests=2, Price=50, Landlord='Sharon', SafetyRating=0.0)
    ap69 = Apartment(ID=68, Description='Purple palace in West Town!', Latitude=41.8954091650345, Longitude=-87.6753677134389, NumGuests=2, Price=80, Landlord='Aaron & Kate', SafetyRating=0.0)
    ap70 = Apartment(ID=69, Description='Top Floor Condo With Skyline View!', Latitude=41.8836703040543, Longitude=-87.6976451463499, NumGuests=4, Price=100, Landlord='Robert', SafetyRating=0.0)
    ap71 = Apartment(ID=70, Description='Spacious & Cozy 2 Bed 2 Bath in heart of Lakeview', Latitude=41.9386183573298, Longitude=-87.6538214212156, NumGuests=4, Price=200, Landlord='Jackie', SafetyRating=0.0)
    ap72 = Apartment(ID=71, Description='Stunning Condo in Lakeview/Boystown', Latitude=41.9506723515025, Longitude=-87.6459077097609, NumGuests=4, Price=175, Landlord='Zayd', SafetyRating=0.0)
    ap73 = Apartment(ID=72, Description='Bucktown - Great Northside Location', Latitude=41.9205531795884, Longitude=-87.6874349909715, NumGuests=2, Price=75, Landlord='Carrie & Brad', SafetyRating=0.0)
    ap74 = Apartment(ID=73, Description='Oakley Bells', Latitude=41.8993360843808, Longitude=-87.6844269723364, NumGuests=4, Price=85, Landlord='Tamara', SafetyRating=0.0)
    ap75 = Apartment(ID=74, Description='Culturally Rich Pad', Latitude=41.8548205089656, Longitude=-87.6668665148838, NumGuests=7, Price=111, Landlord='Levi', SafetyRating=0.0)
    ap76 = Apartment(ID=75, Description='Fantastic River North Location (7)', Latitude=41.8920770035282, Longitude=-87.6262154244446, NumGuests=2, Price=429, Landlord='Justin', SafetyRating=0.0)
    ap77 = Apartment(ID=76, Description='1BD+ 1BA in Luxury Timber Loft', Latitude=41.872480411118, Longitude=-87.6301378724473, NumGuests=2, Price=195, Landlord='Alexander', SafetyRating=0.0)
    ap78 = Apartment(ID=77, Description='Eclectic Logan Square Retreat', Latitude=41.9193292691, Longitude=-87.7122759114298, NumGuests=4, Price=65, Landlord='Kasey + Joe', SafetyRating=0.0)
    ap79 = Apartment(ID=78, Description='Beautiful Grey Stone in Logan Square', Latitude=41.9269975975744, Longitude=-87.6982892487772, NumGuests=2, Price=100, Landlord='Daniel', SafetyRating=0.0)
    ap80 = Apartment(ID=79, Description='Sunny and Modern Logan Square Condo!', Latitude=41.9309356873206, Longitude=-87.7118772322524, NumGuests=3, Price=125, Landlord='Polly And Bobby', SafetyRating=0.0)
    ap81 = Apartment(ID=80, Description='Spacious Retro Basement', Latitude=41.9957437872143, Longitude=-87.762318170493, NumGuests=2, Price=40, Landlord='Georg', SafetyRating=0.0)
    ap82 = Apartment(ID=81, Description='Cozy Family Friendly Home in Galewood', Latitude=41.9118322706607, Longitude=-87.7888856585802, NumGuests=5, Price=150, Landlord='Emily', SafetyRating=0.0)
    ap83 = Apartment(ID=82, Description='Buona Sera in Chicago\'s Beautiful Little Italy! 4', Latitude=41.873317102883, Longitude=-87.6538264926584, NumGuests=6, Price=49, Landlord='Keval', SafetyRating=0.0)
    ap84 = Apartment(ID=83, Description='Cool Place', Latitude=41.9557608459283, Longitude=-87.6516182375845, NumGuests=1, Price=777, Landlord='Vaida', SafetyRating=0.0)
    ap85 = Apartment(ID=84, Description='Historic Home near Lake Michigan', Latitude=41.8180942198594, Longitude=-87.599597710669, NumGuests=2, Price=65, Landlord='Danielle', SafetyRating=0.0)
    ap86 = Apartment(ID=85, Description='Bohemian Lincoln Park', Latitude=41.9209720338389, Longitude=-87.6484140775679, NumGuests=2, Price=60, Landlord='Pablo', SafetyRating=0.0)
    ap87 = Apartment(ID=86, Description='Spacious bedroom in Lincoln Park', Latitude=41.9265330342626, Longitude=-87.6445564063809, NumGuests=2, Price=50, Landlord='Katy', SafetyRating=0.0)
    ap88 = Apartment(ID=87, Description='Cozy Apartment In Logan Square', Latitude=41.9266973192025, Longitude=-87.7072876157154, NumGuests=7, Price=150, Landlord='Aviva', SafetyRating=0.0)
    ap89 = Apartment(ID=88, Description='Michigan Avenue Penthouse', Latitude=41.8641331657098, Longitude=-87.6244149797656, NumGuests=6, Price=550, Landlord='Jill', SafetyRating=0.0)
    ap90 = Apartment(ID=89, Description='Fantastic River North Location (6)', Latitude=41.8906529405613, Longitude=-87.628251499299, NumGuests=2, Price=429, Landlord='Justin', SafetyRating=0.0)
    ap91 = Apartment(ID=90, Description='Cozy Bedroom in Spacious Tri-Taylor House', Latitude=41.8691955042598, Longitude=-87.6815939361171, NumGuests=2, Price=45, Landlord='Margaret', SafetyRating=0.0)
    ap92 = Apartment(ID=91, Description='Cozy Room in Beautiful Penthouse', Latitude=41.894342399394, Longitude=-87.6623307563912, NumGuests=2, Price=85, Landlord='Rasheed', SafetyRating=0.0)
    ap93 = Apartment(ID=92, Description='Steps to Wrigley & Red Line in Quiet Condo', Latitude=41.947067767377, Longitude=-87.6532385670619, NumGuests=2, Price=95, Landlord='Jennifer', SafetyRating=0.0)
    ap94 = Apartment(ID=93, Description='Large Modern Vintage Condo near Wrigley/Lake', Latitude=41.9516142243413, Longitude=-87.6464500369352, NumGuests=4, Price=200, Landlord='Larissa', SafetyRating=0.0)
    ap95 = Apartment(ID=94, Description='River West, Grand Blue Line Stop', Latitude=41.8939686333044, Longitude=-87.6497538008763, NumGuests=2, Price=100, Landlord='Russ', SafetyRating=0.0)
    ap96 = Apartment(ID=95, Description='Clean, safe and family-friendly', Latitude=41.9700517870353, Longitude=-87.6843609859813, NumGuests=8, Price=350, Landlord='Guy', SafetyRating=0.0)
    ap97 = Apartment(ID=96, Description='Fantastic River North Location (9)', Latitude=41.8921365338386, Longitude=-87.6278302265711, NumGuests=2, Price=429, Landlord='Justin', SafetyRating=0.0)
    ap98 = Apartment(ID=97, Description='Spacious Wicker Park Loft with 30 ft ceilings', Latitude=41.9008580233957, Longitude=-87.6668543072212, NumGuests=7, Price=127, Landlord='Shane', SafetyRating=0.0)
    ap99 = Apartment(ID=98, Description='Buona Sera in Chicago\'s Beautiful Little Italy!', Latitude=41.8744546707489, Longitude=-87.6523085949961, NumGuests=16, Price=166, Landlord='Keval', SafetyRating=0.0)
    ap100 = Apartment(ID=99, Description='Quiet Room in Uptown', Latitude=41.9669619658008, Longitude=-87.6521294694188, NumGuests=2, Price=65, Landlord='Rose', SafetyRating=0.0)
    ap101 = Apartment(ID=100, Description='Two bedroom 3 bathroom condo in Bucktown', Latitude=41.9147145370895, Longitude=-87.6876269571239, NumGuests=4, Price=250, Landlord='Jessie', SafetyRating=0.0)
    ap102 = Apartment(ID=101, Description='Modern luxury condo minutes away from downtown', Latitude=41.9237377057764, Longitude=-87.705948752075, NumGuests=2, Price=55, Landlord='Alexander', SafetyRating=0.0)
    ap103 = Apartment(ID=102, Description='Private room w bathroom logan squar', Latitude=41.9289486994658, Longitude=-87.6931924795459, NumGuests=1, Price=55, Landlord='Juls', SafetyRating=0.0)
    ap104 = Apartment(ID=103, Description='Fantastic River North Location (2)', Latitude=41.8916234065733, Longitude=-87.6275057938027, NumGuests=2, Price=429, Landlord='Justin', SafetyRating=0.0)
    ap105 = Apartment(ID=104, Description='River North Loft in Prime Location', Latitude=41.8913619786066, Longitude=-87.6374244324547, NumGuests=2, Price=115, Landlord='Reza', SafetyRating=0.0)
    ap106 = Apartment(ID=105, Description='Private Sunny Hyde Park Room & Bath', Latitude=41.798190264507, Longitude=-87.5960131755388, NumGuests=2, Price=98, Landlord='Jeremiah', SafetyRating=0.0)
    ap107 = Apartment(ID=106, Description='Beautiful Home in Wicker Park', Latitude=41.9052868667413, Longitude=-87.683469407321, NumGuests=8, Price=100, Landlord='Jon', SafetyRating=0.0)
    ap108 = Apartment(ID=107, Description='One or Two Rooms - LoganSquare, 20 Min To Downtown', Latitude=41.9160125725964, Longitude=-87.6983804440708, NumGuests=2, Price=35, Landlord='Angela', SafetyRating=0.0)
    ap109 = Apartment(ID=108, Description='Beautiful Modern Vintage Condo w/2 rooms avialable', Latitude=41.9507110766649, Longitude=-87.644630359887, NumGuests=4, Price=125, Landlord='Larissa', SafetyRating=0.0)
    ap110 = Apartment(ID=109, Description='Rogue Philanthropy Manor', Latitude=41.9066696580025, Longitude=-87.7142914076931, NumGuests=2, Price=60, Landlord='Denise', SafetyRating=0.0)
    ap111 = Apartment(ID=110, Description='Private Room, Eclectic \'Hood', Latitude=41.9640758154902, Longitude=-87.6525072477008, NumGuests=2, Price=70, Landlord='Paul & Andrew', SafetyRating=0.0)
    ap112 = Apartment(ID=111, Description='NoHo Haven', Latitude=42.0208297608738, Longitude=-87.6704435516694, NumGuests=4, Price=135, Landlord='Fabiany & Ben', SafetyRating=0.0)
    ap113 = Apartment(ID=112, Description='Sunny Greystone House in Hyde Park', Latitude=41.7981720491008, Longitude=-87.5962133385433, NumGuests=6, Price=250, Landlord='Jeremiah', SafetyRating=0.0)
    ap114 = Apartment(ID=113, Description='Cozy Room, Classic Chicago House', Latitude=42.0185514297418, Longitude=-87.6678223024374, NumGuests=2, Price=45, Landlord='Patricia', SafetyRating=0.0)
    ap115 = Apartment(ID=114, Description='Private room in the heart of Lakeview East', Latitude=41.9397554775949, Longitude=-87.6462021190415, NumGuests=2, Price=60, Landlord='Sharon', SafetyRating=0.0)
    ap116 = Apartment(ID=115, Description='Charming Residence in the heart of the Gold Coast', Latitude=41.9035068512023, Longitude=-87.6305796842244, NumGuests=2, Price=105, Landlord='Phillip', SafetyRating=0.0)
    ap117 = Apartment(ID=116, Description='Hyde Park Condo', Latitude=41.8030216879038, Longitude=-87.5847726768578, NumGuests=2, Price=75, Landlord='Cleo', SafetyRating=0.0)
    ap118 = Apartment(ID=117, Description='Cozy 2 BD Free parking Mall near by', Latitude=41.9271963593102, Longitude=-87.7849063965788, NumGuests=3, Price=60, Landlord='Rosanna', SafetyRating=0.0)
    ap119 = Apartment(ID=118, Description='Logan Square-Butterfly- bed 1', Latitude=41.9328685817307, Longitude=-87.7296902402603, NumGuests=1, Price=30, Landlord='Maria', SafetyRating=0.0)
    ap120 = Apartment(ID=119, Description='Bright Boho Vibes in Humbolt Park', Latitude=41.903602518664, Longitude=-87.7095147969685, NumGuests=4, Price=98, Landlord='Nicole', SafetyRating=0.0)
    ap121 = Apartment(ID=120, Description='Top Floor Ukrainian Village Condo', Latitude=41.9013439183436, Longitude=-87.6782548627651, NumGuests=2, Price=88, Landlord='Jessica', SafetyRating=0.0)
    ap122 = Apartment(ID=121, Description='Fantastic Location! Deluxe 3 Bd/2Ba condo', Latitude=41.8816192982356, Longitude=-87.6805190569002, NumGuests=5, Price=131, Landlord='Lisa', SafetyRating=0.0)
    ap123 = Apartment(ID=122, Description='Logan Square -Green Room', Latitude=41.933064819971, Longitude=-87.7285078672176, NumGuests=1, Price=45, Landlord='Maria', SafetyRating=0.0)
    ap124 = Apartment(ID=123, Description='North Center 2 bdr 2 bth 6+ guests', Latitude=41.9531770195191, Longitude=-87.687160435496, NumGuests=7, Price=75, Landlord='Barry', SafetyRating=0.0)
    ap125 = Apartment(ID=124, Description='*** Logan Square /// 2BR /// 1BA /// Amazing Condo', Latitude=41.9273418201176, Longitude=-87.7264945158028, NumGuests=6, Price=150, Landlord='Rob', SafetyRating=0.0)
    ap126 = Apartment(ID=125, Description='Split-Level Artist Loft', Latitude=41.8892115058883, Longitude=-87.6535899657528, NumGuests=4, Price=200, Landlord='Christopher', SafetyRating=0.0)
    ap127 = Apartment(ID=126, Description='Fantastic River North Location 2b-7', Latitude=41.8916065079748, Longitude=-87.626647242076, NumGuests=4, Price=559, Landlord='Justin', SafetyRating=0.0)
    ap128 = Apartment(ID=127, Description='Cute Wicker Walk Up', Latitude=41.9067648527575, Longitude=-87.6688096851884, NumGuests=3, Price=54, Landlord='Erinn', SafetyRating=0.0)
    ap129 = Apartment(ID=128, Description='Cozy Garden Apt in North Center', Latitude=41.9566058414159, Longitude=-87.6780097164312, NumGuests=4, Price=115, Landlord='Nisara', SafetyRating=0.0)
    ap130 = Apartment(ID=129, Description='old school double decked 2 bedroom/1bath in Uptown', Latitude=41.9688252802841, Longitude=-87.6511922082049, NumGuests=2, Price=65, Landlord='Thomas', SafetyRating=0.0)
    ap131 = Apartment(ID=130, Description='Private Room near McCormick Place', Latitude=41.8549707297254, Longitude=-87.626614265747, NumGuests=2, Price=83, Landlord='Stephanie', SafetyRating=0.0)
    ap132 = Apartment(ID=131, Description='Entire Old Town Condo with Parking', Latitude=41.9109347613119, Longitude=-87.6386493802552, NumGuests=2, Price=100, Landlord='Sarah', SafetyRating=0.0)
    ap133 = Apartment(ID=132, Description='Fantastic River North Location 2b-5', Latitude=41.8916573280084, Longitude=-87.6274550176908, NumGuests=4, Price=559, Landlord='Justin', SafetyRating=0.0)
    ap134 = Apartment(ID=133, Description='Charming & Modern Urban Apartment', Latitude=41.7653181003897, Longitude=-87.6310994009043, NumGuests=4, Price=48, Landlord='Marc', SafetyRating=0.0)
    ap135 = Apartment(ID=134, Description='Comfy Room in Vintage WalkUp', Latitude=41.9275651546303, Longitude=-87.6639696667112, NumGuests=2, Price=62, Landlord='Catrina', SafetyRating=0.0)
    ap136 = Apartment(ID=135, Description='Cozy bedroom in Hip Chicago Neighborhood', Latitude=41.8996534873387, Longitude=-87.6750656156962, NumGuests=2, Price=60, Landlord='Lisa', SafetyRating=0.0)
    ap137 = Apartment(ID=136, Description='Spacious 3 BD in the heart of Humboldt Park!', Latitude=41.9007110477411, Longitude=-87.7013157766076, NumGuests=5, Price=219, Landlord='Amanda', SafetyRating=0.0)
    ap138 = Apartment(ID=137, Description='2bed/2bath w/ parking - short walk to Wrigley!', Latitude=41.9426649185022, Longitude=-87.6462228309805, NumGuests=4, Price=500, Landlord='Alison', SafetyRating=0.0)
    ap139 = Apartment(ID=138, Description='Bright, Spacious 1BR in Lincoln Park', Latitude=41.9276541119955, Longitude=-87.642667557419, NumGuests=4, Price=162, Landlord='Tyler', SafetyRating=0.0)
    ap140 = Apartment(ID=139, Description='Great Edgewater/Andersonville Suite', Latitude=41.9864203929472, Longitude=-87.6618863382104, NumGuests=4, Price=120, Landlord='Tripp & Todd', SafetyRating=0.0)
    ap141 = Apartment(ID=140, Description='Stunning Pulse break in the Heart of the City', Latitude=41.8891422259132, Longitude=-87.6459650725624, NumGuests=4, Price=122, Landlord='Kelsey', SafetyRating=0.0)
    ap142 = Apartment(ID=141, Description='3 Bed High-Rise in Conveinent Downtown Chicago!', Latitude=41.8909048946202, Longitude=-87.6315706376841, NumGuests=6, Price=149, Landlord='Kelsea', SafetyRating=0.0)
    ap143 = Apartment(ID=142, Description='Lake and river view in the heart of Chicago', Latitude=41.8879067050147, Longitude=-87.617650621418, NumGuests=5, Price=300, Landlord='Belen', SafetyRating=0.0)
    ap144 = Apartment(ID=143, Description='Logan Square-Buddy Room - Bed 1', Latitude=41.9349646015873, Longitude=-87.7284183146013, NumGuests=1, Price=30, Landlord='Maria', SafetyRating=0.0)
    ap145 = Apartment(ID=144, Description='Cozy Room in Hideaway Coach House', Latitude=41.9122298708598, Longitude=-87.686595658845, NumGuests=2, Price=59, Landlord='Ethan', SafetyRating=0.0)
    ap146 = Apartment(ID=145, Description='Mag Mile One Bedroom with Amenities', Latitude=41.8996151811768, Longitude=-87.6294176679265, NumGuests=2, Price=150, Landlord='Matt', SafetyRating=0.0)
    ap147 = Apartment(ID=146, Description='Cozy studio in Downtown Chicago', Latitude=41.8917054500816, Longitude=-87.6171723779428, NumGuests=2, Price=119, Landlord='Ali', SafetyRating=0.0)
    ap148 = Apartment(ID=147, Description='Luxury 1BD by Navy Pier', Latitude=41.89337773279, Longitude=-87.6185651749012, NumGuests=2, Price=250, Landlord='Kristi', SafetyRating=0.0)
    ap149 = Apartment(ID=148, Description='Fantastic River North Location!-s2', Latitude=41.8922208975962, Longitude=-87.6263597610235, NumGuests=2, Price=359, Landlord='Justin', SafetyRating=0.0)
    ap150 = Apartment(ID=149, Description='Sunny Room w/ Private Bath in Buzzing Bucktown', Latitude=41.9161713357197, Longitude=-87.6893146392642, NumGuests=2, Price=60, Landlord='Megan', SafetyRating=0.0)
    ap151 = Apartment(ID=150, Description='Large Home in Fun Neighborhood!', Latitude=41.9212353863679, Longitude=-87.6944856703317, NumGuests=6, Price=390, Landlord='Megan', SafetyRating=0.0)
    ap152 = Apartment(ID=151, Description='Perfectly Located BUCKTOWN Apt!', Latitude=41.9183235936147, Longitude=-87.6809956762727, NumGuests=3, Price=109, Landlord='Andy', SafetyRating=0.0)
    ap153 = Apartment(ID=152, Description='Private room & bathroom in Noble Sq / Wicker Pk', Latitude=41.9014979882635, Longitude=-87.6629912499661, NumGuests=2, Price=127, Landlord='Jenny', SafetyRating=0.0)
    ap154 = Apartment(ID=153, Description='Wrigleyville Condo', Latitude=41.950585429006, Longitude=-87.6591959288316, NumGuests=4, Price=125, Landlord='Ryan', SafetyRating=0.0)
    ap155 = Apartment(ID=154, Description='Big Apt on North Ave in Wicker Park', Latitude=41.9113939446077, Longitude=-87.6856681143347, NumGuests=2, Price=60, Landlord='Ian', SafetyRating=0.0)
    ap156 = Apartment(ID=155, Description='Centrally located 1br/ba', Latitude=41.8909228848945, Longitude=-87.648224831583, NumGuests=2, Price=69, Landlord='Z', SafetyRating=0.0)
    ap157 = Apartment(ID=156, Description='Buona Sera in Chicago\'s Beautiful Little Italy! 3', Latitude=41.8722565619472, Longitude=-87.6546558604072, NumGuests=3, Price=45, Landlord='Keval', SafetyRating=0.0)
    ap158 = Apartment(ID=157, Description='Comfortable/clean condo in the heart of Ukrainian', Latitude=41.8995976383678, Longitude=-87.6769552606356, NumGuests=2, Price=50, Landlord='John', SafetyRating=0.0)
    ap159 = Apartment(ID=158, Description='Beautiful, Spacious Retreat in the City', Latitude=41.8902018298584, Longitude=-87.7728533475994, NumGuests=9, Price=250, Landlord='Erin', SafetyRating=0.0)
    ap160 = Apartment(ID=159, Description='Bright open house, garden & deck', Latitude=41.9695200515011, Longitude=-87.6723924136495, NumGuests=8, Price=168, Landlord='Eileen', SafetyRating=0.0)
    ap161 = Apartment(ID=160, Description='Private Room near Lake and Train', Latitude=42.0181514791354, Longitude=-87.6683672969908, NumGuests=2, Price=45, Landlord='Patricia', SafetyRating=0.0)
    ap162 = Apartment(ID=161, Description='Logan Square - Yellow Room', Latitude=41.9348103530455, Longitude=-87.7297165364163, NumGuests=1, Price=35, Landlord='Maria', SafetyRating=0.0)
    ap163 = Apartment(ID=162, Description='Private Rooftop condo- walk to Wrigley w/parking', Latitude=41.9604862260145, Longitude=-87.6681350590518, NumGuests=5, Price=450, Landlord='Erin', SafetyRating=0.0)
    ap164 = Apartment(ID=163, Description='3BR Penthouse with deck on Oz Park', Latitude=41.9199240620638, Longitude=-87.6469327889901, NumGuests=6, Price=295, Landlord='Joanne', SafetyRating=0.0)
    ap165 = Apartment(ID=164, Description='Great place in heart of Chicago', Latitude=41.9196111311266, Longitude=-87.6511759822574, NumGuests=2, Price=200, Landlord='Ariel', SafetyRating=0.0)
    ap166 = Apartment(ID=165, Description='Vintage One Bedroom in Andersonville + Two Cats!', Latitude=41.9799367822665, Longitude=-87.6715439538442, NumGuests=2, Price=71, Landlord='Mark', SafetyRating=0.0)
    ap167 = Apartment(ID=166, Description='New 2BR West Town Condo', Latitude=41.8984497353859, Longitude=-87.6713554094315, NumGuests=4, Price=250, Landlord='Craig', SafetyRating=0.0)
    ap168 = Apartment(ID=167, Description='Private bedroom in top floor condo', Latitude=41.9672784459462, Longitude=-87.6594276011105, NumGuests=2, Price=76, Landlord='Drew', SafetyRating=0.0)
    ap169 = Apartment(ID=168, Description='Fantastic River North Location 2b-8', Latitude=41.891762057352, Longitude=-87.6278263880115, NumGuests=4, Price=559, Landlord='Justin', SafetyRating=0.0)
    ap170 = Apartment(ID=169, Description='Beautiful studio in the Loop!', Latitude=41.8847226372167, Longitude=-87.6272563098581, NumGuests=2, Price=88, Landlord='Shani', SafetyRating=0.0)
    ap171 = Apartment(ID=170, Description='Modern South Loop Penthouse', Latitude=41.8546684191309, Longitude=-87.6213966079631, NumGuests=5, Price=250, Landlord='Stephanie', SafetyRating=0.0)
    ap172 = Apartment(ID=171, Description='East Pilsen small 2BR', Latitude=41.8589965760916, Longitude=-87.6461971565091, NumGuests=3, Price=94, Landlord='Maximiliano', SafetyRating=0.0)
    ap173 = Apartment(ID=172, Description='Oh Cornelia', Latitude=41.9451230707055, Longitude=-87.6441532880681, NumGuests=4, Price=50, Landlord='Max', SafetyRating=0.0)
    ap174 = Apartment(ID=173, Description='High End Wrigleyville Condo - 1/4 block to Stadium', Latitude=41.9502541561841, Longitude=-87.6578245523427, NumGuests=4, Price=600, Landlord='Kyle', SafetyRating=0.0)
    ap175 = Apartment(ID=174, Description='Granville Guest Suite', Latitude=41.9948366722767, Longitude=-87.6618422796864, NumGuests=2, Price=100, Landlord='Jenn And Alex', SafetyRating=0.0)
    ap176 = Apartment(ID=175, Description='Sunny 2bd Flat: Location! Location! Wicker Park', Latitude=41.9117803797657, Longitude=-87.6763498444181, NumGuests=5, Price=175, Landlord='Amanda', SafetyRating=0.0)
    ap177 = Apartment(ID=176, Description='Private UK Village Room', Latitude=41.8997119626525, Longitude=-87.6735186655386, NumGuests=2, Price=57, Landlord='Stacy', SafetyRating=0.0)
    ap178 = Apartment(ID=177, Description='Sweet Home Chicago', Latitude=41.9082402098188, Longitude=-87.6952416693807, NumGuests=2, Price=60, Landlord='Heather', SafetyRating=0.0)
    ap179 = Apartment(ID=178, Description='Sunny renovated apt 3 blocks from Wrigley!', Latitude=41.9528678610956, Longitude=-87.656644663072, NumGuests=4, Price=115, Landlord='James', SafetyRating=0.0)
    ap180 = Apartment(ID=179, Description='Walk to Wrigley! Top-floor-Lakeview/Roscoe Village', Latitude=41.9402597865585, Longitude=-87.6696574725744, NumGuests=4, Price=175, Landlord='Natalie', SafetyRating=0.0)
    ap181 = Apartment(ID=180, Description='Lincoln Park! 3BR/2BA Magnificent Roof Top', Latitude=41.9194908435306, Longitude=-87.6420736547911, NumGuests=5, Price=285, Landlord='Sasha', SafetyRating=0.0)
    ap182 = Apartment(ID=181, Description='Private Room in Beautiful Home + Safe Neighborhood', Latitude=41.9505381621001, Longitude=-87.7609377105895, NumGuests=2, Price=65, Landlord='Ludell And Davis', SafetyRating=0.0)
    ap183 = Apartment(ID=182, Description='West Town --> walk to Blue-Line CTA', Latitude=41.8930929985577, Longitude=-87.6651410068881, NumGuests=2, Price=90, Landlord='Erik', SafetyRating=0.0)
    ap184 = Apartment(ID=183, Description='Convenient Bucktown 2 Bedroom Flat', Latitude=41.9103612672371, Longitude=-87.6830227887667, NumGuests=5, Price=109, Landlord='Amanda', SafetyRating=0.0)
    ap185 = Apartment(ID=184, Description='Hauserly on the Boulevard', Latitude=41.9157061996192, Longitude=-87.7037639459526, NumGuests=2, Price=70, Landlord='Saskia', SafetyRating=0.0)
    ap186 = Apartment(ID=185, Description='Funky Fabulous Greektown Loft', Latitude=41.8779797784277, Longitude=-87.652084688952, NumGuests=1, Price=180, Landlord='Bebe', SafetyRating=0.0)
    ap187 = Apartment(ID=186, Description='Comfy lofted bedroom and bath near UIC', Latitude=41.8659794980292, Longitude=-87.6545260275554, NumGuests=2, Price=100, Landlord='Roberto', SafetyRating=0.0)
    ap188 = Apartment(ID=187, Description='Funky Fabulous Greektown Loft', Latitude=41.8767197045238, Longitude=-87.6495254150834, NumGuests=2, Price=325, Landlord='Bebe', SafetyRating=0.0)
    ap189 = Apartment(ID=188, Description='Large Room & Bath | Beautiful Apt', Latitude=41.9587666625223, Longitude=-87.6471157393112, NumGuests=2, Price=115, Landlord='Derek', SafetyRating=0.0)
    ap190 = Apartment(ID=189, Description='2 Bedroom 15 minute walk from Wrigley Field', Latitude=41.9526596827583, Longitude=-87.6650884285156, NumGuests=4, Price=125, Landlord='John', SafetyRating=0.0)
    ap191 = Apartment(ID=190, Description='Amazing studio in heart of Lakeview', Latitude=41.933922512009, Longitude=-87.6510513805503, NumGuests=2, Price=117, Landlord='Borja', SafetyRating=0.0)
    ap192 = Apartment(ID=191, Description='Huge Space in River North.', Latitude=41.8958654795531, Longitude=-87.632669149092, NumGuests=4, Price=189, Landlord='Rishi', SafetyRating=0.0)
    ap193 = Apartment(ID=192, Description='Private Room - Uptown Condo', Latitude=41.9668182966344, Longitude=-87.6556310988813, NumGuests=4, Price=125, Landlord='Jims', SafetyRating=0.0)
    ap194 = Apartment(ID=193, Description='Musician\'s Quarters', Latitude=41.7996266917381, Longitude=-87.5947678399749, NumGuests=2, Price=85, Landlord='Chester', SafetyRating=0.0)
    ap195 = Apartment(ID=194, Description='Fantastic River North Location 2b-1', Latitude=41.891510889141, Longitude=-87.6284110581974, NumGuests=4, Price=559, Landlord='Justin', SafetyRating=0.0)
    ap196 = Apartment(ID=195, Description='Heart of Gold Coast (lady only)', Latitude=41.8993155277434, Longitude=-87.6260301765227, NumGuests=1, Price=55, Landlord='Renee', SafetyRating=0.0)
    ap197 = Apartment(ID=196, Description='Spacious 2br/2bath with picture perfect city views', Latitude=41.8731698209254, Longitude=-87.6322197453015, NumGuests=7, Price=200, Landlord='Pamela', SafetyRating=0.0)
    ap198 = Apartment(ID=197, Description='WORLD SERIES PERFECTION W/ PARKING!', Latitude=41.9241315864878, Longitude=-87.6420101408764, NumGuests=3, Price=325, Landlord='Dana', SafetyRating=0.0)
    ap199 = Apartment(ID=198, Description='CUBS,YOUR OWN LUXE TERRACED DUPLEX LOFT INCLUDED', Latitude=41.9319317557448, Longitude=-87.669883653759, NumGuests=2, Price=96, Landlord='Sam And Amy', SafetyRating=0.0)
    ap200 = Apartment(ID=199, Description='Edgewater Studio- Great Location and Quaint Space', Latitude=41.9891569667086, Longitude=-87.6560916044041, NumGuests=2, Price=90, Landlord='Brittany', SafetyRating=0.0)
    ap201 = Apartment(ID=200, Description='Spacious Room w/own Bathroom', Latitude=41.8127209789802, Longitude=-87.6221887812354, NumGuests=2, Price=55, Landlord='Valicia', SafetyRating=0.0)
    ap202 = Apartment(ID=201, Description='Logan Square- Blk & Wht', Latitude=41.9331281974534, Longitude=-87.7284475406465, NumGuests=1, Price=40, Landlord='Maria', SafetyRating=0.0)
    ap203 = Apartment(ID=202, Description='Gorgeous Ukrainian Village condo w/ roof & view', Latitude=41.8972121252617, Longitude=-87.6691014436182, NumGuests=2, Price=131, Landlord='Kathryn And Ted', SafetyRating=0.0)
    ap204 = Apartment(ID=203, Description='Wicker Park Walk Up', Latitude=41.9063905991464, Longitude=-87.6661303917396, NumGuests=1, Price=62, Landlord='Jeph', SafetyRating=0.0)
    ap205 = Apartment(ID=204, Description='Cool, Quiet, and Chill at Morse \'L\'', Latitude=42.0107483114125, Longitude=-87.6649878691215, NumGuests=2, Price=65, Landlord='Oliver & Will', SafetyRating=0.0)
    ap206 = Apartment(ID=205, Description='Beautiful Penthouse in Wicker Park', Latitude=41.9036811783673, Longitude=-87.6799317636387, NumGuests=2, Price=125, Landlord='Jon', SafetyRating=0.0)
    ap207 = Apartment(ID=206, Description='Bright Room in Ukrainian Village', Latitude=41.8952143137331, Longitude=-87.6771277279685, NumGuests=2, Price=75, Landlord='Tyler', SafetyRating=0.0)
    ap208 = Apartment(ID=207, Description='Sunny Large Apartment, Near Beautiful Public Pool', Latitude=41.8895386664741, Longitude=-87.6603957850901, NumGuests=2, Price=50, Landlord='Susan', SafetyRating=0.0)
    ap209 = Apartment(ID=208, Description='Eclectic \'Hood, Private Room', Latitude=41.9636089061834, Longitude=-87.6522288667707, NumGuests=2, Price=70, Landlord='Paul & Andrew', SafetyRating=0.0)
    ap210 = Apartment(ID=209, Description='Spacious Old Town Apartment Close to EVERYTHING', Latitude=41.90464922373, Longitude=-87.6370425897887, NumGuests=4, Price=150, Landlord='Connor', SafetyRating=0.0)
    ap211 = Apartment(ID=210, Description='Luxury room in 2bed apt, great location', Latitude=41.8862080432111, Longitude=-87.626237077581, NumGuests=1, Price=100, Landlord='Renata', SafetyRating=0.0)
    ap212 = Apartment(ID=211, Description='Hyde Park Lakeview Studio Apartment', Latitude=41.8032399991123, Longitude=-87.5862280318782, NumGuests=2, Price=80, Landlord='Victor', SafetyRating=0.0)
    ap213 = Apartment(ID=212, Description='Private Room With Living Area in Safe Neighborhood', Latitude=41.9496665608073, Longitude=-87.761395813779, NumGuests=2, Price=55, Landlord='Ludell And Davis', SafetyRating=0.0)
    ap214 = Apartment(ID=213, Description='Irving Park Private Tree-lined Room', Latitude=41.954933813346, Longitude=-87.7109451644491, NumGuests=2, Price=55, Landlord='Jackie', SafetyRating=0.0)
    ap215 = Apartment(ID=214, Description='LOGAN FULL APARTMENT FOR RENT', Latitude=41.9333407661941, Longitude=-87.6935331385578, NumGuests=3, Price=85, Landlord='Mike', SafetyRating=0.0)
    ap216 = Apartment(ID=215, Description='Cozy & Modern Urban Oasis', Latitude=41.9560758710827, Longitude=-87.6453578421986, NumGuests=4, Price=250, Landlord='Derek', SafetyRating=0.0)
    ap217 = Apartment(ID=216, Description='Quiet Room near Loyola Univ. north', Latitude=41.9952595015646, Longitude=-87.6654551245387, NumGuests=2, Price=50, Landlord='Karen', SafetyRating=0.0)
    ap218 = Apartment(ID=217, Description='Big Studio Close To Everything!', Latitude=41.9334064287842, Longitude=-87.6475290770572, NumGuests=2, Price=65, Landlord='Kurt', SafetyRating=0.0)
    ap219 = Apartment(ID=218, Description='Luxurious, modern Lincoln Park apartment', Latitude=41.9197336889716, Longitude=-87.65968963693, NumGuests=2, Price=125, Landlord='Lauren', SafetyRating=0.0)
    ap220 = Apartment(ID=219, Description='2-bedroom Uptown Condo', Latitude=41.9683055284191, Longitude=-87.6573863536359, NumGuests=7, Price=83, Landlord='Jims', SafetyRating=0.0)
    ap221 = Apartment(ID=220, Description='Chic 1 Bedroom Apartment !', Latitude=41.9545747519733, Longitude=-87.6556016814833, NumGuests=2, Price=125, Landlord='Miranda', SafetyRating=0.0)
    ap222 = Apartment(ID=221, Description='Spacious sunlit vintage 2 bed flat', Latitude=41.97492741202, Longitude=-87.6793065673132, NumGuests=4, Price=135, Landlord='George', SafetyRating=0.0)
    ap223 = Apartment(ID=222, Description='Beautiful Apt. Peaceful - Close to Transportation', Latitude=41.9664680820793, Longitude=-87.7187293140874, NumGuests=2, Price=31, Landlord='Adriana', SafetyRating=0.0)
    ap224 = Apartment(ID=223, Description='Cozy north', Latitude=41.9959040726279, Longitude=-87.7028351134247, NumGuests=1, Price=37, Landlord='Lyz', SafetyRating=0.0)
    ap225 = Apartment(ID=224, Description='Fantastic River North Location 2b-3', Latitude=41.8914639977403, Longitude=-87.6266679424223, NumGuests=4, Price=559, Landlord='Justin', SafetyRating=0.0)
    ap226 = Apartment(ID=225, Description='Charming apartment in Lakeview', Latitude=41.9356848504611, Longitude=-87.6385290092192, NumGuests=4, Price=180, Landlord='Leah', SafetyRating=0.0)
    ap227 = Apartment(ID=226, Description='Great one bedroom apartment w/den', Latitude=41.9356252364476, Longitude=-87.6645953279352, NumGuests=3, Price=115, Landlord='Maria', SafetyRating=0.0)
    ap228 = Apartment(ID=227, Description='Beautiful Loft in Lakeview Sleeps 9', Latitude=41.9416538921797, Longitude=-87.6515516911187, NumGuests=9, Price=900, Landlord='Corine', SafetyRating=0.0)
    ap229 = Apartment(ID=228, Description='Fantastic River North Location (3)', Latitude=41.8903108002046, Longitude=-87.6286265298093, NumGuests=2, Price=429, Landlord='Justin', SafetyRating=0.0)
    ap230 = Apartment(ID=229, Description='Beautiful West Town Abode', Latitude=41.8940612154748, Longitude=-87.6658906075659, NumGuests=2, Price=119, Landlord='Lisa', SafetyRating=0.0)
    ap231 = Apartment(ID=230, Description='2-Bedroom Apartment with Patio', Latitude=41.8964649737914, Longitude=-87.6961963408632, NumGuests=6, Price=179, Landlord='Joe', SafetyRating=0.0)
    ap232 = Apartment(ID=231, Description='Room for rent in homey two-flat', Latitude=41.9610628418278, Longitude=-87.7063510559496, NumGuests=1, Price=23, Landlord='Angela', SafetyRating=0.0)
    ap233 = Apartment(ID=232, Description='Old Town Triangle awesomeness!', Latitude=41.9198311504622, Longitude=-87.6390837111857, NumGuests=3, Price=124, Landlord='Brett & Karen', SafetyRating=0.0)
    ap234 = Apartment(ID=233, Description='Logan Square - full size bed', Latitude=41.9335148298309, Longitude=-87.7281931694527, NumGuests=1, Price=50, Landlord='Maria', SafetyRating=0.0)
    ap235 = Apartment(ID=234, Description='Cozy Pilsen Reading Room', Latitude=41.8534186769446, Longitude=-87.6668430624722, NumGuests=2, Price=29, Landlord='Jason', SafetyRating=0.0)
    ap236 = Apartment(ID=235, Description='Walk one minute to the Beach!!!', Latitude=42.011799200432, Longitude=-87.6626923866082, NumGuests=6, Price=225, Landlord='Merit', SafetyRating=0.0)
    ap237 = Apartment(ID=236, Description='Vintage Fairytale Gingerbread Tudor House', Latitude=41.9898593664516, Longitude=-87.7426363346206, NumGuests=10, Price=430, Landlord='Georgios', SafetyRating=0.0)
    ap238 = Apartment(ID=237, Description='Rustic River Space', Latitude=41.973552149254, Longitude=-87.7065960928674, NumGuests=2, Price=75, Landlord='Ryan', SafetyRating=0.0)
    ap239 = Apartment(ID=238, Description='Sunny Logan Square apt., walk to everything!', Latitude=41.9212067423977, Longitude=-87.6995837788232, NumGuests=4, Price=150, Landlord='Molly', SafetyRating=0.0)
    ap240 = Apartment(ID=239, Description='Cozy Vintage WalkUp', Latitude=41.9270930147864, Longitude=-87.6633679288205, NumGuests=2, Price=74, Landlord='Catrina', SafetyRating=0.0)
    ap241 = Apartment(ID=240, Description='Sweet apartment in the heart of Chicago', Latitude=41.854386175122, Longitude=-87.6978128371023, NumGuests=2, Price=60, Landlord='Daniel', SafetyRating=0.0)
    ap242 = Apartment(ID=241, Description='1 or 2 rooms town house', Latitude=41.94028607935, Longitude=-87.6935670784646, NumGuests=4, Price=90, Landlord='Aqui', SafetyRating=0.0)
    ap243 = Apartment(ID=242, Description='Spend where it matters - Safe haven', Latitude=41.8328215658394, Longitude=-87.6415428969742, NumGuests=1, Price=37, Landlord='Megan', SafetyRating=0.0)
    ap244 = Apartment(ID=243, Description='Charming Ukrainian Village Condo', Latitude=41.8993670936522, Longitude=-87.6856780161161, NumGuests=2, Price=90, Landlord='Mike', SafetyRating=0.0)
    ap245 = Apartment(ID=244, Description='Spacious Ukranian Village apartment', Latitude=41.8979784124415, Longitude=-87.6882698782857, NumGuests=4, Price=129, Landlord='Jenny', SafetyRating=0.0)
    ap246 = Apartment(ID=245, Description='Brick Home in Bucktown, Chicago', Latitude=41.9185823355661, Longitude=-87.6778984981826, NumGuests=3, Price=125, Landlord='Laurie', SafetyRating=0.0)
    ap247 = Apartment(ID=246, Description='3 bedroom Dramatic Bucktown LOFT', Latitude=41.9208299818749, Longitude=-87.6801038360157, NumGuests=6, Price=250, Landlord='Justin', SafetyRating=0.0)
    ap248 = Apartment(ID=247, Description='Fantastic River North Location (4)', Latitude=41.8904009871023, Longitude=-87.6281836770396, NumGuests=2, Price=429, Landlord='Lindsay', SafetyRating=0.0)
    ap249 = Apartment(ID=248, Description='Bright, modern Avondale apartment', Latitude=41.9404895403601, Longitude=-87.7238874438079, NumGuests=3, Price=175, Landlord='Taylee', SafetyRating=0.0)
    ap250 = Apartment(ID=249, Description='Spacious and Kid-friendly 2-bed in Logan Square', Latitude=41.9337717608468, Longitude=-87.7043074133548, NumGuests=4, Price=100, Landlord='Ricardo', SafetyRating=0.0)
    ap251 = Apartment(ID=250, Description='Sharing Aptment at great location', Latitude=41.9448168803638, Longitude=-87.6504853200683, NumGuests=2, Price=70, Landlord='Travis', SafetyRating=0.0)
    ap252 = Apartment(ID=251, Description='Steps from public transport, Lake, & restaurants', Latitude=41.9264183251252, Longitude=-87.6408893127356, NumGuests=2, Price=65, Landlord='Joe & Danielle', SafetyRating=0.0)
    ap253 = Apartment(ID=252, Description='Vintage 2 br. in East Humboldt', Latitude=41.908234557282, Longitude=-87.6926356394311, NumGuests=4, Price=100, Landlord='Michael', SafetyRating=0.0)
    ap254 = Apartment(ID=253, Description='Amazing 2BR, 2BTH in Wicker Park!', Latitude=41.9028940995466, Longitude=-87.6729293917014, NumGuests=5, Price=200, Landlord='Megan', SafetyRating=0.0)
    ap255 = Apartment(ID=254, Description='Charming Ukrainian Village Condo', Latitude=41.9000600670702, Longitude=-87.6850893853245, NumGuests=4, Price=300, Landlord='Sara', SafetyRating=0.0)
    ap256 = Apartment(ID=255, Description='Chicago room minutes from Downtown', Latitude=41.911734100239, Longitude=-87.6731042654368, NumGuests=2, Price=60, Landlord='Ian', SafetyRating=0.0)
    ap257 = Apartment(ID=256, Description='Humboldt Park Guest Room', Latitude=41.9058884916355, Longitude=-87.6897931816984, NumGuests=2, Price=39, Landlord='Kayla', SafetyRating=0.0)
    ap258 = Apartment(ID=257, Description='Logan Sq. Comfort Private Bath, Walk to L & Dining', Latitude=41.9184694830525, Longitude=-87.7062245180029, NumGuests=2, Price=90, Landlord='Vaida', SafetyRating=0.0)
    ap259 = Apartment(ID=258, Description='Sunlit Buena Park Condo w/Deck Near Park and Lake', Latitude=41.9553641367863, Longitude=-87.6522758528109, NumGuests=2, Price=77, Landlord='Chicago Private', SafetyRating=0.0)
    ap260 = Apartment(ID=259, Description='Adeline\'s Sea Moose, Burnham Harbor Yacht Rental', Latitude=41.8596091566525, Longitude=-87.6132147521657, NumGuests=6, Price=100, Landlord='Stephanie', SafetyRating=0.0)
    ap261 = Apartment(ID=260, Description='Bright Spacious 2 BR', Latitude=41.9946151024673, Longitude=-87.7795041358049, NumGuests=5, Price=95, Landlord='Marv', SafetyRating=0.0)
    ap262 = Apartment(ID=261, Description='1 BD Condo by downtown,park,lake', Latitude=41.9027401481374, Longitude=-87.6330262558493, NumGuests=2, Price=119, Landlord='Jill K', SafetyRating=0.0)
    ap263 = Apartment(ID=262, Description='Cozy Unique Large Private Room Lincoln Square', Latitude=41.9680971170212, Longitude=-87.6902633029448, NumGuests=2, Price=50, Landlord='Keval', SafetyRating=0.0)
    ap264 = Apartment(ID=263, Description='Buona Sera in Chicago\'s Beautiful Little Italy! 2', Latitude=41.8718607630016, Longitude=-87.6543542202323, NumGuests=5, Price=75, Landlord='Neda', SafetyRating=0.0)
    ap265 = Apartment(ID=264, Description='High-rise apt available!!', Latitude=41.8341233481952, Longitude=-87.6152286876761, NumGuests=3, Price=100, Landlord='Sarah', SafetyRating=0.0)
    ap266 = Apartment(ID=265, Description='Clean & Comfortable Near Blue Line', Latitude=41.9407592821955, Longitude=-87.7041001273326, NumGuests=2, Price=72, Landlord='Jill', SafetyRating=0.0)
    ap267 = Apartment(ID=266, Description='Spacious, exposed brick in Lakeview', Latitude=41.9501344756282, Longitude=-87.6615779123828, NumGuests=2, Price=190, Landlord='Maria', SafetyRating=0.0)
    ap268 = Apartment(ID=267, Description='Logan Square-Buddy Room - Bed 2', Latitude=41.9327920835566, Longitude=-87.7287709420237, NumGuests=2, Price=30, Landlord='Kate', SafetyRating=0.0)
    ap269 = Apartment(ID=268, Description='Private Room in Artist Loft', Latitude=41.9090382294641, Longitude=-87.6860322347092, NumGuests=2, Price=80, Landlord='Michael', SafetyRating=0.0)
    ap270 = Apartment(ID=269, Description='Updated Andersonville Garden', Latitude=41.9801772950794, Longitude=-87.670467404984, NumGuests=4, Price=400, Landlord='Jose', SafetyRating=0.0)
    ap271 = Apartment(ID=270, Description='The perfect place to be in Chicago!', Latitude=41.9423702496888, Longitude=-87.6408994044334, NumGuests=2, Price=70, Landlord='Collin', SafetyRating=0.0)
    ap272 = Apartment(ID=271, Description='Stunning South Lakeview Condo', Latitude=41.9370405795648, Longitude=-87.6504065637974, NumGuests=2, Price=100, Landlord='Andrew', SafetyRating=0.0)
    ap273 = Apartment(ID=272, Description='Charming Lakeview 1BD', Latitude=41.9411073233184, Longitude=-87.6432348665211, NumGuests=2, Price=119, Landlord='Steven', SafetyRating=0.0)
    ap274 = Apartment(ID=273, Description='Airy modern home in the heart of Lincoln Square', Latitude=41.9650238368545, Longitude=-87.6809400385087, NumGuests=6, Price=400, Landlord='Nate', SafetyRating=0.0)
    ap275 = Apartment(ID=274, Description='Private Lincoln Square Garden Apt', Latitude=41.9671368538355, Longitude=-87.6961072169067, NumGuests=4, Price=100, Landlord='Sara Ellen', SafetyRating=0.0)
    ap276 = Apartment(ID=275, Description='Comfy place to stay', Latitude=41.9802206286165, Longitude=-87.7097646288332, NumGuests=2, Price=50, Landlord='Holly', SafetyRating=0.0)
    ap277 = Apartment(ID=276, Description='beautiful logan square home', Latitude=41.9215251517015, Longitude=-87.7171705275222, NumGuests=2, Price=49, Landlord='Karina', SafetyRating=0.0)
    ap278 = Apartment(ID=277, Description='Spare Room in West Town Loft', Latitude=41.8901650862482, Longitude=-87.6767465450791, NumGuests=2, Price=150, Landlord='Rebecca', SafetyRating=0.0)
    ap279 = Apartment(ID=278, Description='Private Bedroom in Beautiful Condo', Latitude=41.909478659125, Longitude=-87.6873409519281, NumGuests=2, Price=55, Landlord='Karina', SafetyRating=0.0)
    ap280 = Apartment(ID=279, Description='Loft Overlooking Chicago Skyline', Latitude=41.8916530127557, Longitude=-87.6765826835025, NumGuests=6, Price=350, Landlord='John', SafetyRating=0.0)
    ap281 = Apartment(ID=280, Description='Huge beautiful top floor 3 br/2 ba', Latitude=41.8967947690675, Longitude=-87.6679341000488, NumGuests=6, Price=210, Landlord='Stephanie', SafetyRating=0.0)
    ap282 = Apartment(ID=281, Description='Wonderful Apartment in Bronzeville!', Latitude=41.8140923285404, Longitude=-87.6045221792555, NumGuests=2, Price=95, Landlord='Jennifer', SafetyRating=0.0)
    ap283 = Apartment(ID=282, Description='10 minutes to Wrigley Field, 30 minutes to Loop!', Latitude=41.9606702832584, Longitude=-87.6776655834717, NumGuests=1, Price=50, Landlord='Nicole', SafetyRating=0.0)
    ap284 = Apartment(ID=283, Description='Bright Boho Vibes in Humbolt Park', Latitude=41.9028243290414, Longitude=-87.7092293704714, NumGuests=2, Price=65, Landlord='Aaron', SafetyRating=0.0)
    ap285 = Apartment(ID=284, Description='Urban Retreat: Bed and Breakfast', Latitude=41.8556055108318, Longitude=-87.6703092230076, NumGuests=3, Price=84, Landlord='Emmanuel', SafetyRating=0.0)
    ap286 = Apartment(ID=285, Description='near downtown and mccormick place', Latitude=41.8309238601734, Longitude=-87.6076161584908, NumGuests=4, Price=120, Landlord='Roberto', SafetyRating=0.0)
    ap287 = Apartment(ID=286, Description='Good location Hyde Park friendly host rarely home', Latitude=41.8089835156021, Longitude=-87.6029681779361, NumGuests=2, Price=38, Landlord='Maria', SafetyRating=0.0)
    ap288 = Apartment(ID=287, Description='Logan Square-Butterfly- bed 2', Latitude=41.9340548470717, Longitude=-87.7299289997576, NumGuests=1, Price=30, Landlord='Dana', SafetyRating=0.0)
    ap289 = Apartment(ID=288, Description='Great private room! Near Lincoln Square', Latitude=41.9720476230476, Longitude=-87.6961901437899, NumGuests=2, Price=40, Landlord='Judy', SafetyRating=0.0)
    ap290 = Apartment(ID=289, Description='U of C campus rooms', Latitude=41.7951169514166, Longitude=-87.6021067565564, NumGuests=2, Price=70, Landlord='Marina', SafetyRating=0.0)
    ap291 = Apartment(ID=290, Description='Great Location Near Wrigley Field & Southport', Latitude=41.9480636382387, Longitude=-87.6632525564112, NumGuests=4, Price=170, Landlord='Marina', SafetyRating=0.0)
    ap292 = Apartment(ID=291, Description='cozy lakeview east 1br close to lake', Latitude=41.9523804307589, Longitude=-87.6459032498001, NumGuests=2, Price=130, Landlord='Claire', SafetyRating=0.0)
    ap293 = Apartment(ID=292, Description='Charming Bucktown Luxury 2BD', Latitude=41.9172714332929, Longitude=-87.6741587589326, NumGuests=5, Price=170, Landlord='Mike', SafetyRating=0.0)
    ap294 = Apartment(ID=293, Description='Luxury Downtown/SouthLoop Private Room & Bathroom', Latitude=41.863933901496, Longitude=-87.6238037809996, NumGuests=3, Price=50, Landlord='Brian', SafetyRating=0.0)
    ap295 = Apartment(ID=294, Description='1 Bed/Bath. Near Lake, Zoo, Wrigley', Latitude=41.9298477698372, Longitude=-87.6435345004102, NumGuests=2, Price=119, Landlord='Tabb', SafetyRating=0.0)
    ap296 = Apartment(ID=295, Description='Private bedroom/ bath with extras.', Latitude=41.9962331115663, Longitude=-87.6646657800981, NumGuests=2, Price=120, Landlord='Zac', SafetyRating=0.0)
    ap297 = Apartment(ID=296, Description='Lots of Space in a Little Room', Latitude=41.9049648860678, Longitude=-87.6889067126362, NumGuests=3, Price=90, Landlord='Ali', SafetyRating=0.0)
    ap298 = Apartment(ID=297, Description='Spacious 3 Bedroom apartment !', Latitude=41.8987891327878, Longitude=-87.6923822016811, NumGuests=6, Price=500, Landlord='Russ', SafetyRating=0.0)
    ap299 = Apartment(ID=298, Description='Great Spacious Lincoln Sq Condo!', Latitude=41.967645792915, Longitude=-87.6903757361441, NumGuests=2, Price=102, Landlord='Fabiany & Ben', SafetyRating=0.0)
    ap300 = Apartment(ID=299, Description='NoHo Haven', Latitude=42.0206467535795, Longitude=-87.6703084087413, NumGuests=2, Price=69, Landlord='Allen', SafetyRating=0.0)
    ap301 = Apartment(ID=300, Description='Cozy room in the middle of Historic Little Italy', Latitude=41.8692912887872, Longitude=-87.6633789450366, NumGuests=1, Price=65, Landlord='Steven', SafetyRating=0.0)
    ap302 = Apartment(ID=301, Description='Charming Old Town Studio', Latitude=41.9134051622464, Longitude=-87.6346913372444, NumGuests=2, Price=99, Landlord='Carmen', SafetyRating=0.0)
    ap303 = Apartment(ID=302, Description='2 bed/2 bath Apt & a Quick 20 min Trip to Wrigley!', Latitude=41.9891154920368, Longitude=-87.6569036552702, NumGuests=4, Price=240, Landlord='Lisa', SafetyRating=0.0)
    ap304 = Apartment(ID=303, Description='Private room in Wicker Park', Latitude=41.9075764773145, Longitude=-87.6713998453845, NumGuests=2, Price=75, Landlord='Nina', SafetyRating=0.0)
    ap305 = Apartment(ID=304, Description='Sunny Condo Near Lake with Deck', Latitude=41.9560424160299, Longitude=-87.6505165276888, NumGuests=2, Price=78, Landlord='Derek', SafetyRating=0.0)
    ap306 = Apartment(ID=305, Description='Private Room & Bath | Beautiful Apt', Latitude=41.9552310582882, Longitude=-87.6538546097305, NumGuests=2, Price=70, Landlord='Alex', SafetyRating=0.0)
    ap307 = Apartment(ID=306, Description='Zen Den Garden Apt - Lincoln Square', Latitude=41.9688908134504, Longitude=-87.6890511213982, NumGuests=4, Price=89, Landlord='Evan', SafetyRating=0.0)
    ap308 = Apartment(ID=307, Description='Spacious duplex in trendy Bucktown', Latitude=41.9112902670252, Longitude=-87.6833719405667, NumGuests=7, Price=289, Landlord='Bret', SafetyRating=0.0)
    ap309 = Apartment(ID=308, Description='Cozy, Beautiful & Vintage Drenched', Latitude=41.902129182737, Longitude=-87.6759820615455, NumGuests=4, Price=144, Landlord='David', SafetyRating=0.0)
    ap310 = Apartment(ID=309, Description='Hideout at the Joinery', Latitude=41.9158476710815, Longitude=-87.6900114046024, NumGuests=6, Price=200, Landlord='John', SafetyRating=0.0)
    ap311 = Apartment(ID=310, Description='Upscale Home: 2Br/5Bed Roscoe Village/ Cubs', Latitude=41.9469114358275, Longitude=-87.6878710230713, NumGuests=6, Price=147, Landlord='Katie', SafetyRating=0.0)
    ap312 = Apartment(ID=311, Description='Beautifully Furnished Gallery Style Loft Downtown', Latitude=41.8759524790538, Longitude=-87.63093777045, NumGuests=3, Price=145, Landlord='Roberto', SafetyRating=0.0)
    ap313 = Apartment(ID=312, Description='UIC / Taylor St suite and parking', Latitude=41.8674001237872, Longitude=-87.6551958362577, NumGuests=2, Price=75, Landlord='Joseph', SafetyRating=0.0)
    ap314 = Apartment(ID=313, Description='a lovely condo + an ideal area!', Latitude=41.9209456113197, Longitude=-87.7097287507614, NumGuests=2, Price=80, Landlord='Dick', SafetyRating=0.0)
    ap315 = Apartment(ID=314, Description='Location, Location, Location', Latitude=41.9160788648048, Longitude=-87.6808304648234, NumGuests=4, Price=129, Landlord='Glenda', SafetyRating=0.0)
    ap316 = Apartment(ID=315, Description='Landmark Tree House', Latitude=41.9283548096684, Longitude=-87.7032578521353, NumGuests=4, Price=110, Landlord='Ashvin', SafetyRating=0.0)
    ap317 = Apartment(ID=316, Description='Logan Square Luxury Condo', Latitude=41.924104454166, Longitude=-87.7058982935345, NumGuests=2, Price=200, Landlord='Friday', SafetyRating=0.0)
    ap318 = Apartment(ID=317, Description='Cozy room in a charming area', Latitude=41.8936013161718, Longitude=-87.6823553541357, NumGuests=1, Price=60, Landlord='Matthew', SafetyRating=0.0)
    ap319 = Apartment(ID=318, Description='Room in beautiful Gold Coast', Latitude=41.9029212221065, Longitude=-87.6247796687619, NumGuests=3, Price=200, Landlord='Justin', SafetyRating=0.0)
    ap320 = Apartment(ID=319, Description='Fantastic River North Location 2b-4', Latitude=41.8904852971529, Longitude=-87.6272436687137, NumGuests=4, Price=559, Landlord='Justin', SafetyRating=0.0)
    ap321 = Apartment(ID=320, Description='Fantastic River North Location 3b', Latitude=41.8907698335175, Longitude=-87.6265384497146, NumGuests=6, Price=899, Landlord='Ajeenkya', SafetyRating=0.0)
    ap322 = Apartment(ID=321, Description='Spacious Lakeview Apartment w/deck', Latitude=41.9402371076499, Longitude=-87.6505631965775, NumGuests=4, Price=75, Landlord='Emily', SafetyRating=0.0)
    ap323 = Apartment(ID=322, Description='Southport Sojourn @ Wrigley Field - 2BR / 4 Beds', Latitude=41.9453395058583, Longitude=-87.6609422040735, NumGuests=6, Price=249, Landlord='Tom', SafetyRating=0.0)
    db2.session.add_all([ap2,ap3,ap4,ap5,ap6,ap7,ap8,ap9,ap10,ap11,ap12,ap13,ap14,ap15,ap16,ap17,ap18,ap19,ap20,ap21,ap22,ap23,ap24,ap25,ap26,ap27,ap28,ap29,ap30,ap31,ap32,ap33,ap34,ap35,ap36,ap37,ap38,ap39,ap40,ap41,ap42,ap43,ap44,ap45,ap46,ap47,ap48,ap49,ap50,ap51,ap52,ap53,ap54,ap55,ap56,ap57,ap58,ap59,ap60,ap61,ap62,ap63,ap64,ap65,ap66,ap67,ap68,ap69,ap70,ap71,ap72,ap73,ap74,ap75,ap76,ap77,ap78,ap79,ap80,ap81,ap82,ap83,ap84,ap85,ap86,ap87,ap88,ap89,ap90,ap91,ap92,ap93,ap94,ap95,ap96,ap97,ap98,ap99,ap100,ap101,ap102,ap103,ap104,ap105,ap106,ap107,ap108,ap109,ap110,ap111,ap112,ap113,ap114,ap115,ap116,ap117,ap118,ap119,ap120,ap121,ap122,ap123,ap124,ap125,ap126,ap127,ap128,ap129,ap130,ap131,ap132,ap133,ap134,ap135,ap136,ap137,ap138,ap139,ap140,ap141,ap142,ap143,ap144,ap145,ap146,ap147,ap148,ap149,ap150,ap151,ap152,ap153,ap154,ap155,ap156,ap157,ap158,ap159,ap160,ap161,ap162,ap163,ap164,ap165,ap166,ap167,ap168,ap169,ap170,ap171,ap172,ap173,ap174,ap175,ap176,ap177,ap178,ap179,ap180,ap181,ap182,ap183,ap184,ap185,ap186,ap187,ap188,ap189,ap190,ap191,ap192,ap193,ap194,ap195,ap196,ap197,ap198,ap199,ap200,ap201,ap202,ap203,ap204,ap205,ap206,ap207,ap208,ap209,ap210,ap211,ap212,ap213,ap214,ap215,ap216,ap217,ap218,ap219,ap220,ap221,ap222,ap223,ap224,ap225,ap226,ap227,ap228,ap229,ap230,ap231,ap232,ap233,ap234,ap235,ap236,ap237,ap238,ap239,ap240,ap241,ap242,ap243,ap244,ap245,ap246,ap247,ap248,ap249,ap250,ap251,ap252,ap253,ap254,ap255,ap256,ap257,ap258,ap259,ap260,ap261,ap262,ap263,ap264,ap265,ap266,ap267,ap268,ap269,ap270,ap271,ap272,ap273,ap274,ap275,ap276,ap277,ap278,ap279,ap280,ap281,ap282,ap283,ap284,ap285,ap286,ap287,ap288,ap289,ap290,ap291,ap292,ap293,ap294,ap295,ap296,ap297,ap298,ap299,ap300,ap301,ap302,ap303,ap304,ap305,ap306,ap307,ap308,ap309,ap310,ap311,ap312,ap313,ap314,ap315,ap316,ap317,ap318,ap319,ap320,ap321,ap322,ap323])

    db2.session.commit()

    db3 = pymysql.connect("localhost", "root", "", "airbnb")
    """
    cursor = db3.cursor()
    #cursor = mysql.connection.cursor()
    cursor.execute("select * from apartment")
    results = cursor.fetchall()
    crime_records = list(crimes.find({}))
    for apartment in results:
        rating = cal_safety(apartment, crime_records)
        cursor.execute("update apartment set SafetyRating = %s where ID = %s", (rating, apartment[0]))
        db3.commit()
    cursor.close()
    
    """
    app.run(debug=True)
