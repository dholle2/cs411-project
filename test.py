"""
@app.route('/admin_search.html', methods=['GET', 'POST'])
def admin_search():
    results = []
    if request.method == 'POST':
        if 'search_listing' in request.form:
            zipcode = request.form.get('zipcode')
            guest = request.form.get('guest')
            lowerprice = request.form.get('lowerprice')
            upperprice = request.form.get('upperprice')
            safety = request.form.get('safety')
            landlord = request.form.get('landlord')
            description = request.form.get('description')
            results = Apartment.query.all()
            condition = Apartment.ID != ''
            if zipcode:
                condition = and_(condition, Apartment.Zipcode == zipcode)
            if guest:
                condition = and_(condition, Apartment.NumGuests == guest)
            if lowerprice:
                condition = and_(condition, Apartment.Price >= lowerprice)
            if upperprice:
                condition = and_(condition, Apartment.Price <= upperprice)
            if safety:
                condition = and_(condition, Apartment.SafetyRating >= safety)
            if landlord:
                condition = and_(condition, Apartment.Landlord.like('%' + landlord + '%'))
            if description:
                condition = and_(condition, Apartment.Description.like('%' + description + '%'))
            results = Apartment.query.filter(condition).all()
        if 'new_listing' in request.form:
            listingDetails = request.form
            description = listingDetails['description']
            zipcode = listingDetails['zipcode']
            num_guests = listingDetails['num_guests']
            price = listingDetails['price']
            landlord = listingDetails['landlord']
            safety_rating = listingDetails['safety_rating']

            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO apartment VALUES(null, %s, %s, %s, %s, %s, %s)", (str(description), zipcode, num_guests, price, str(landlord), safety_rating))
            mysql.connection.commit()
            cur.close()
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
        landlord = request.form.get('landlord')
        description = request.form.get('description')
        results = Apartment.query.all()
        condition = Apartment.ID != ''
        if zipcode:
            condition = and_(condition, Apartment.Zipcode == zipcode)
        if guest:
            condition = and_(condition, Apartment.NumGuests == guest)
        if lowerprice:
            condition = and_(condition, Apartment.Price >= lowerprice)
        if upperprice:
            condition = and_(condition, Apartment.Price <= upperprice)
        if safety:
            condition = and_(condition, Apartment.SafetyRating >= safety)
        if landlord:
            condition = and_(condition, Apartment.Landlord.like('%' + landlord + '%'))
        if description:
            condition = and_(condition, Apartment.Description.like('%' + description + '%'))
        results = Apartment.query.filter(condition).all()
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
"""

from pymongo import MongoClient
import pymysql
from pygeodesy import ellipsoidalVincenty as ev

client = MongoClient('mongodb+srv://user1:user1password@cluster0-9dppt.mongodb.net/crimedata?retryWrites=true&w=majority')
db = client['crimedata']
collection = db['crimeRecords']
db = pymysql.connect("localhost","root","","airbnb" )
cursor = db.cursor()
cursor.execute("select * from apartment")
results = cursor.fetchall()
crimes = list(collection.find({})) # if not use list, the results returned by mongodb is a cursor object and can only be used in a loop once
#print(results, type(results),type(results[1]))
#print(crimes[0])
#print(type(crimes[0]['arrest']))

crime_score = {'ARSON':8, 'ASSAULT':8, 'BATTERY':8, 'BURGLARY':7, 'CONCEALED CARRY LICENSE VIOLATION':5,
               'CRIM SEXUAL ASSAULT':8, 'CRIMINAL DAMAGE':5, 'CRIMINAL SEXUAL ASSAULT':8, 'CRIMINAL TRESPASS':7,
               'DECEPTIVE PRACTICE':5, 'GAMBLING':5, 'HOMICIDE':10, 'HUMAN TRAFFICKING':9, 'INTERFERENCE WITH PUBLIC OFFICER':5,
               'INTIMIDATION':7, 'KIDNAPPING':9, 'LIQUOR LAW VIOLATION':3, 'MOTOR VEHICLE THEFT':5, 'NARCOTICS':6,
               'OBSCENITY':5, 'OFFENSE INVOLVING CHILDREN':8, 'OTHER NARCOTIC VIOLATION':6, 'OTHER OFFENSE':5,
               'PROSTITUTION':5, 'PUBLIC INDECENCY':5, 'PUBLIC PEACE VIOLATION':5, 'ROBBERY':6, 'SEX OFFENSE':7,
               'STALKING':6, 'THEFT':5, 'WEAPONS VIOLATION':5, 'PUBLIC PEACE VIOLATION':7, 'RITUALISM':5,
               'NON-CRIMINAL':1, 'CRIMINAL ABORTION':1
               }

#print(crimes[0]['primary_type'], crime_score[crimes[0]['primary_type']])
#print(isinstance(crimes[0], dict))


test = []
for apartment in results:
    total_score = 0
    for crime in crimes:
        start = ev.LatLon(apartment[2], apartment[3])
        end = ev.LatLon(crime['latitude'], crime['longitude'])
        distance = float(start.distanceTo(end)) # meter
        #test.append(distance)
        #if distance <5000:
           # print('test',distance)
            #print(distance)
            #print(apartment[0], crime['_id'])
        if distance>3000:
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
    rating = round(10-total_score/100, 2)
    cursor.execute("update apartment set SafetyRating = %s where ID = %s", (rating, apartment[0]))
    db.commit()
    test.append(rating)
print(test)
"""
i=0
for crime in crimes:
    if not crime['primary_type'] in crime_score.keys():
        i += 1
        print(crime['_id'], crime)
        print(type(crime))
print(i)
"""
