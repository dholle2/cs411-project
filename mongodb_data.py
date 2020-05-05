import pandas as pd
from sodapy import Socrata
from pymongo import MongoClient
from datetime import datetime

# id='aks2zxz0qspiy8kr84g20ati7'
# secret = '3aac1vlcd2kyqh79vcaa5dtpb1kusow1gdb5cyolxkqqcaasc5'

# Unauthenticated client only works with public data sets. Note 'None'
# in place of application token, and no username or password:
client = Socrata("data.cityofchicago.org", None)

# Example authenticated client (needed for non-public datasets):
# client = Socrata(data.cityofchicago.org,
#                  MyAppToken,
#                  userame="user@example.com",
#                  password="AFakePassword")

results = client.get("qzdf-xmn8", limit=1000)
results_df = pd.DataFrame.from_records(results, exclude=['location','district','block', 'y_coordinate', 'description',
                                                         'location_description', 'updated_on', 'community_area',
                                                         'iucr', 'x_coordinate', 'ward', 'year', 'domestic', 'fbi_code',
                                                         'beat','id'])
# convert datatype
results_df['date'] = results_df['date'].str.slice(0,10)
#results_df['date'] = pd.to_datetime(results_df['date'].str.slice(0,10))
results_df['latitude'] = results_df['latitude'].astype(float)
results_df['longitude'] = results_df['longitude'].astype(float)
results_df['case_number'] = results_df['case_number'].astype(str)
results_df['primary_type'] = results_df['primary_type'].astype(str)
results_df.dropna(axis=0, how='any', inplace=True)

print(results[0], type(results[-1]), len(results))
print(results_df.dtypes)

results_group=results_df.groupby(['latitude', 'longitude', 'primary_type', 'arrest'])
crimes = []
i = 1
for k,v in results_group:
    each_record = {}
    detail = []
    each_record['_id']=i
    i+=1
    each_record['latitude'] = k[0]
    each_record['longitude'] = k[1]
    each_record['primary_type'] = k[2]
    each_record['arrest'] = k[3]
    each_record['frequency'] = v.shape[0]
    for j in range(v.shape[0]):
        each_crime = {}
        each_crime['case_number']=v.iloc[j,2]
        #each_crime['date']=pd.Timestamp.date(v.iloc[j,0])
        each_crime['date']=datetime.strptime(v.iloc[j,0], '%Y-%m-%d')
        #each_crime['date'] = v.iloc[j,0]
        detail.append(each_crime)
        each_record['detail'] = detail
    crimes.append(each_record)

client = MongoClient('mongodb+srv://user1:user1password@cluster0-9dppt.mongodb.net/crimedata?retryWrites=true&w=majority')
db = client['crimedata']
collection = db['crimeRecords']
collection.delete_many({})
collection.insert_many(crimes)