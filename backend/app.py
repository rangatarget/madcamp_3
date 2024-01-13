from pymongo import MongoClient
from gridfs import GridFS
from bson.objectid import ObjectId
from flask_cors import CORS
from flask import Flask, request, jsonify, url_for
from bson.json_util import dumps
from werkzeug.utils import secure_filename
import os
import json
import requests
import certifi
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)
ca = certifi.where()

client = MongoClient('mongodb+srv://dlgudwls8184:NeTSWJRhf3bF7yIe@cluster0.escpqml.mongodb.net/', tlsCAFile = ca)

db = client['DevToday']

user_collection = db['User']

velog_collection = db['Velog']
velog_rec_collection = db['Velog_Recommended']
today_collection = db['Heart']
today_rec_collection = db['Heart_Recommended']

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        grant_type = data.get('grant_type')
        client_id = data.get('client_id')
        redirect_uri = data.get('redirect_uri')
        code = data.get('code')

        print(data)
        print(grant_type)
        
        # Perform actions with the received access token (e.g., store it in the database)
        # Example: Store the access token in the database
        # Your code here...

        token_response = requests.post(
            f'https://kauth.kakao.com/oauth/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'code': code
            },
            headers={"content-type": "application/x-www-form-urlencoded"}
        )

        kakao_token = token_response.json()
        print(kakao_token)

        headers= {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cache-Control': 'no-cache',
            'Authorization': 'Bearer ' + str(kakao_token['access_token'])
        }


        user_url = "https://kapi.kakao.com/v2/user/me"

        response = requests.request("GET", user_url, headers=headers)
        print("This is the response")
        print(response.text)
        json_response = response.json()
        kakao_id = json_response.get('id')  # 카카오 아이디 가져오기
        profile = json_response.get('kakao_account').get('profile')  # 프로필 정보 가져오기
        nickname = profile['nickname']
        thumbnail_image_url = profile['thumbnail_image_url']
        print(kakao_id)
        print(nickname)
        print(thumbnail_image_url)
        finduser = user_collection.find_one({'kakao_id' : kakao_id})
        
        if(finduser):
            print("존재하는 아이디 -> 로그인 절차 실행")
            return {'user_id' : str(finduser['_id']), 'kakao_id' : str(finduser['kakao_id']), 'nickname' : str(finduser['nickname']), 'code' : str(finduser['kakao_id']), 'thumbnail_image_url' : str(finduser['thumbnail_image_url'])}
        
        else:
            print("존재하지 않는 아이디 -> db에 등록 실행")
            result = user_collection.insert_one({"kakao_id": kakao_id, "nickname": nickname, 'code' : str(kakao_id), "thumbnail_image_url" : thumbnail_image_url, "friends" : [], "location": "", "online" : False})
            return {'user_id' : str(result.inserted_id), 'kakao_id' : str(kakao_id), 'nickname' : str(nickname), 'code' : str(kakao_id), 'thumbnail_image_url' : str(thumbnail_image_url)}

@app.route('/showvelogs', methods=['POST'])
def showVelogs():
    if request.method == 'POST':
        data = request.get_json()
        tags_to_find = data['tags']
        sortby = data['sortby']
        isascending = data['isascending']
        velogs_to_show = velog_collection.find({'tags': {'$all': tags_to_find}})
        if sortby == 'time':
            sorted_velogs_to_show = sorted(velogs_to_show, key=lambda doc: doc['time'], reverse = isascending)
        elif(sortby == 'thumbs'):
            def getrecentthumbs(doc):
                doc1 = velog_rec_collection.find({'velog_id' : doc['_id']})
                score = 0
                current = datetime.now()
                for document in doc1:
                    stored_time = datetime.strptime(document['time'], "%Y-%m-%d %H:%M:%S")
                    if current - stored_time < timedelta(hours=12):
                        score += 10
                    elif current - stored_time < timedelta(days=1):
                        score += 5
                    elif current - stored_time < timedelta(days=3):
                        score += 2
                return score

            sorted_velogs_to_show = sorted(velogs_to_show, key=lambda doc: getrecentthumbs(doc), reverse = isascending)
        else:
            return {'_velogs_to_show' : None}
        return {'_velogs_to_show' : sorted_velogs_to_show}
    
@app.route('/createvelog', methods=['POST'])
def createVelog():
    print(request)
    if 'file' in request.files:
        print('this is request.files')
        print(request.files)
        file = request.files['file']
        filename = secure_filename(file.filename)
        save_path = os.path.join('uploads', filename)
        file.save(save_path)
        print(type(filename))
        
        # 파일 저장 후 해당 이미지에 접근할 수 있는 URL 생성
        # 예를 들어, 이미지를 'uploads' 폴더에 저장했다고 가정하면:
        image_url = url_for('uploads/' + filename, filename=filename, _external=True)
        print(image_url)

        return jsonify({'message': 'Image uploaded successfully', 'url': image_url})
    else:
        return jsonify({'error': 'No image uploaded'}), 400
        

    
@app.route('/showfriends', methods=['POST'])
def showFriends():
    if request.method == 'POST':
        data = request.get_json()
        user_id = ObjectId(data['user_id'])
        user = user_collection.find_one({'_id' : user_id})
        print(user)
        friendsidlist = user['friends']
        print("this is friendsidlist")
        print(friendsidlist)
        cursor = user_collection.find({'_id' : {'$in' : friendsidlist}})
        friendslist = list(cursor)
        return jsonify(json.loads(dumps(list(friendslist))))

@app.route('/addfriends', methods=['POST'])
def addFriends():
    if request.method == 'POST':
        data = request.get_json()
        user_id = ObjectId(data['user_id'])
        print(type(user_id))
        user_code = data['code']
        findfriend = user_collection.find_one({'code' : user_code})
        if(findfriend):
            friendid = findfriend['_id']
            print(friendid)
            result = user_collection.update_one({'_id': user_id}, {'$push': {'friends': friendid}})
            print(result)
            return {'issucessful' : True}
        else:
            return {'issucessful' : False}
        
@app.route('/myvelogs', methods=['POST'])
def myVelogs():
    if request.method == 'POST':
        data = request.get_json()
        user_id = data['user_id']
        tags_to_find = data['tags']
        isascending = data['isascending']
        velogs_to_show = velog_collection.find({'tags': {'$all': tags_to_find}, 'user_id' : user_id})
        sorted_velogs_to_show = sorted(velogs_to_show, key=lambda doc: doc['time'], reverse = isascending)
        return {'_velogs_to_show' : sorted_velogs_to_show}
    
@app.route('/givethumb', methods=['POST'])
def giveThumb():
    if request.method == 'POST':
        data = request.get_json()
        user_id = data['user_id']
        velog_id = data['velog_id']
        thumbed = velog_rec_collection.find_one({'user_id' : user_id, 'velog_id' : velog_id})
        if thumbed:
            upordown = -1
        else:
            upordown = 1
            current_time = datetime.now()
            velog_collection.insert_one({'velog_id' : velog_id, 'user_id' : user_id, 'time' : current_time.strftime("%Y-%m-%d %H:%M:%S")})
        old_thumbs = velog_collection.find_one({'_id' : velog_id})['thumbs']
        result = velog_collection.update_one({'_id': velog_id}, {'$push': {'thumbs': old_thumbs + upordown}})
        if thumbed: return {'isthumbedup' : False}
        else : return {'isthumbeddown' : True}

@app.route('/giveheart', methods=['POST'])
def giveHeart():
    if request.method == 'POST':
        data = request.get_json()
        user_id = data['user_id']
        today_id = data['today_id']
        hearted = today_rec_collection.find_one({'user_id' : user_id, 'today_id' : today_id})
        if hearted:
            upordown = -1
        else:
            upordown = 1
        old_hearts = today_collection.find_one({'_id' : today_id})['hearts']
        result = today_collection.update_one({'_id': today_id}, {'$push': {'hearts': old_hearts + upordown}})
        if hearted: return {'isheartedup' : False}
        else : return {'ishearteddown' : True}

@app.route('/mytodays', methods=['POST'])
def myTodays():
    if request.method == 'POST':
        data = request.get_json()
        user_id = data['user_id']
        mytodays = list(today_collection.find({'user_id' : user_id}))
        return mytodays
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)