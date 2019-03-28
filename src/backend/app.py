
import os
import os.path
import cv2
import datetime

FOLDER_CURR = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append(os.path.abspath(FOLDER_CURR))

from src.backend import db_session
from src.backend import db_model
from src.backend.models import Response

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS


from flask_jwt_extended import JWTManager, decode_token
from flask_jwt_extended import (
    jwt_refresh_token_required, get_jwt_identity, create_access_token,
    create_refresh_token, jwt_required
)

AVARTAR_PATH = os.path.join(FOLDER_CURR, '..', 'avatars')
DATASET_PATH = os.path.join(FOLDER_CURR, '..', 'datasets')
MODEL_PATH = os.path.join(FOLDER_CURR, '..', 'model', 'trained_knn_model.clf')

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    CORS(app, headers=['Content-Type', 'Authorization'])
    app.secret_key = 'test'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.config['JWT_BLACKLIST_ENABLED'] = True
    app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    jwt.init_app(app)
    # In a real application, these would likely be blueprints
    register_endpoints(app)

    return app

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def register_endpoints(app):

    @jwt.token_in_blacklist_loader
    def check_if_token_revoked(access_token):
        decoded_token = decode_token(access_token, allow_expired=True)
        return db_session.check_token(decoded_token)

    @app.route('/api/v1/auth/login/', methods=['POST'])
    def login_user():
        try:
            content = request.get_json()
            face_id = content['face_id']
            password = content['password']

            records = db_session.get_user_id(face_id=face_id)
            for record in records:
                result = record.validate_password(password)
                if result:
                    expires = datetime.timedelta(hours=1)
                    access_token = create_access_token(identity=record.face_id, expires_delta=expires)

                    decoded_token = decode_token(access_token, allow_expired=True)
                    jti = decoded_token['jti']
                    token_type = decoded_token['type']
                    user_identity = decoded_token[app.config['JWT_IDENTITY_CLAIM']]
                    expires = datetime.datetime.fromtimestamp(decoded_token['exp'])
                    revoked = False

                    db_token = db_model.TokenBlacklist(
                        jti=jti,
                        token_type=token_type,
                        user_identity=user_identity,
                        expires=expires,
                        revoked=revoked,
                    )
                    db_session.insert_object(db_token)

                    response = {
                        'access_token': access_token
                    }

                    status = 201
                    data = response
                    message = 'success'
                    return jsonify(Response(data, status, message).to_json()), 201
            status = 404
            data = None
            message = 'The user is not found'
            return jsonify(Response(data, status, message).to_json()), 201
        except Exception:
            status = 500
            data = None
            message = 'Something Wrong'
            return jsonify(Response(data, status, message).to_json()), 500

    # @app.route('/api/v1/auth/refresh', methods=['POST'])
    # @jwt_refresh_token_required
    # def refresh():
    #     # Do the same thing that we did in the login endpoint here
    #     current_user = get_jwt_identity()
    #     print(current_user)
    #     access_token = create_access_token(identity=current_user)
    #     blacklist_helper.add_token_to_database(access_token, app.config['JWT_IDENTITY_CLAIM'])
    #     return jsonify({'access_token': access_token}), 201

    @app.route('/api/v1/auth/token', methods=['GET'])
    @jwt_required
    def get_tokens():
        user_identity = get_jwt_identity()
        all_tokens = db_session.get_token(user_identity)
        ret = [token.to_dict() for token in all_tokens]

        status = 200
        data = ret
        message = 'success'
        return jsonify(Response(data, status, message).to_json()), 200

    @app.route('/api/v1/avatars/<face_id>.jpg', methods=['GET'])
    def get_avatar(face_id):
        path = os.path.join(AVARTAR_PATH, face_id, '0.jpg')
        if not os.path.exists(path):
            response = {'message': 'face_id is not found'}
            return jsonify(response), 404
        with open(path, 'rb') as image:
            image_binary = image.read()
            response = make_response(image_binary)
            response.headers.set('Content-Type', 'image/jpeg')
            response.headers.set(
                'Content-Disposition', 'attachment', filename='%s_0.jpg' %face_id)
            return response, 200

    @app.route('/api/v1/upload/<face_id>', methods=['POST'])
    def upload_image(face_id):
        path = os.path.join(DATASET_PATH, face_id)
        if not os.path.exists(path):
            status = 404
            data = None
            message = 'Folder face_id is not found'
            return jsonify(Response(data, status, message).to_json()), 404

        if request.method == 'POST':
            if 'file' not in request.files:
                status = 404
                data = None
                message = 'File is not found'
                return jsonify(Response(data, status, message).to_json()), 404

            file = request.files['file']
            if file.filename == '':
                status = 444
                data = None
                message = 'File is empty'
                return jsonify(Response(data, status, message).to_json()), 444

            if file and allowed_file(file.filename):
                #filename = secure_filename(file.filename)
                #dung cach khac nhe
                files = [int(os.path.splitext(f)[0]) for f in os.listdir(path)]
                if len(files) == 0:
                    filename = '1.png'
                else:
                    filename = str(max(files) + 1) + '.png'
                dataset_path = os.path.join(path, filename)
                file.save(dataset_path)
                if len(files) == 0:
                    avatar_folder = os.path.join(AVARTAR_PATH, face_id)
                    if not os.path.exists(avatar_folder):
                        os.mkdir(avatar_folder)
                    img = cv2.imread(dataset_path)
                    avatar_path = os.path.join(avatar_folder, '0.jpg')
                    cv2.imwrite(avatar_path, img)
                    db_session.update_user(face_id, '/api/v1/avatars/{0}.jpg'.format(face_id))

                status = 201
                data = None
                message = 'Upload is success'
                return jsonify(Response(data, status, message).to_json()), 201
        status = 500
        data = None
        message = 'Something wrong'
        return jsonify(Response(data, status, message).to_json()), 500

    @app.route('/api/v1/users/', methods=['GET'])
    def get_users():

        try:
            auth_token = request.headers.get('Authorization')
            access_token = auth_token.split(' ')[1]

            tokens = db_session.get_token(access_token)
            if len(tokens) == 0:
                status = 401
                data = None
                message = 'token is revoked'
                return jsonify(Response(data, status, message).to_json()), 401

            id = tokens[0].id
            expired = tokens[0].expires
            user_identity = tokens[0].user_identity
            revoked = tokens[0].revoked

            if expired < datetime.datetime.now() or revoked:
                db_session.update_token(id, user_identity, True)
                status = 401
                data = None
                message = 'token is revoked'
                return jsonify(Response(data, status, message).to_json()), 401

            users = db_session.get_user_id(user_identity)
            if len(users) == 0:
                status = 404
                data = None
                message = 'User is not found'
                return jsonify(Response(data, status, message).to_json()), 404
            level = users[0].level

            face_id = request.args.get('face_id')
            start = request.args.get('start_date')
            end = request.args.get('end_date')

            if level == 1:
                records = users
            else:
                records = db_session.get_all_user(face_id, start, end)

            result = []
            for user in records:
                res_user = {
                    'id': user.id,
                    'face_id': user.face_id,
                    'fullname': user.fullname,
                    'date_created': str(user.date_created),
                    'avatar': user.avatar
                }
                result.append(res_user)
            status = 200
            data = {
                'user': result
            }
            message = 'success'
            return jsonify(Response(data, status, message).to_json()), 200
        except Exception:
            status = 500
            data = None
            message = 'Something Wrong'
            return jsonify(Response(data, status, message).to_json()), 500

    @app.route('/api/v1/users/new/', methods=['POST'])
    def new_user():

        try:
            auth_token = request.headers.get('Authorization')
            access_token = auth_token.split(' ')[1]

            tokens = db_session.get_token(access_token)
            if len(tokens) == 0:
                status = 401
                data = None
                message = 'token is revoked'
                return jsonify(Response(data, status, message).to_json()), 401

            id = tokens[0].id
            expired = tokens[0].expires
            user_identity = tokens[0].user_identity
            revoked = tokens[0].revoked

            if expired < datetime.datetime.now() or revoked:
                db_session.update_token(id, user_identity, True)
                status = 401
                data = None
                message = 'token is revoked'
                return jsonify(Response(data, status, message).to_json()), 401

            users = db_session.get_user_id(user_identity)
            if len(users) == 0:
                status = 404
                data = None
                message = 'User is not found'
                return jsonify(Response(data, status, message).to_json()), 404
            level = users[0].level

            if level == 1:
                status = 404
                data = None
                message = 'you are not auth'
                return jsonify(Response(data, status, message).to_json()), 404

            content = request.get_json()
            face_id = content['face_id']
            password = content['password']
            fullname = content['fullname']
            date_created = datetime.datetime.now()
            users = db_session.get_user_id(face_id)
            avatar = '/api/v1/avatars/default.jpg'
            if len(users) > 0:
                status = 409
                data = None
                message = 'The user has existed'
                return jsonify(Response(data, status, message).to_json()), 409
            else:
                if fullname is None or fullname == '':
                    fullname = face_id
                user = db_model.User(face_id=face_id, password=password, fullname=fullname, avatar=avatar,
                                     date_created=str(date_created))
                # chua check neu fail
                db_session.insert_object(user)

                folder_avatar_user = os.path.join(AVARTAR_PATH, face_id)
                folder_dataset_user = os.path.join(DATASET_PATH, face_id)
                if not os.path.exists(folder_avatar_user):
                    os.mkdir(folder_avatar_user)

                if not os.path.exists(folder_dataset_user):
                    os.mkdir(folder_dataset_user)

                status = 201
                data = {'face_id': face_id,
                        'fullname': fullname,
                        'avatar': avatar}
                message = 'success'
                return jsonify(Response(data, status, message).to_json()), 201

        except Exception:
            status = 500
            data = None
            message = 'Something Wrong'
            return jsonify(Response(data, status, message).to_json()), 500


    @app.route('/api/v1/schedules/', methods=['GET'])
    def get_schedule():

        try:
            auth_token = request.headers.get('Authorization')
            access_token = auth_token.split(' ')[1]

            tokens = db_session.get_token(access_token)
            if len(tokens) == 0:
                status = 401
                data = None
                message = 'token is revoked'
                return jsonify(Response(data, status, message).to_json()), 401

            id = tokens[0].id
            expired = tokens[0].expires
            user_identity = tokens[0].user_identity
            revoked = tokens[0].revoked

            if expired < datetime.datetime.now() or revoked:
                db_session.update_token(id, user_identity, True)
                status = 401
                data = None
                message = 'token is revoked'
                return jsonify(Response(data, status, message).to_json()), 401

            users = db_session.get_user_id(user_identity)
            if len(users) == 0:
                status = 404
                data = None
                message = 'User is not found'
                return jsonify(Response(data, status, message).to_json()), 404
            level = users[0].level

            face_id = request.args.get('face_id')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            if start_date is None:
                start_date = datetime.datetime.now().date()

            if end_date is None:
                end_date = datetime.datetime.now().date()

            if level == 2:
                if face_id is None:
                    # get by month
                    records = db_session.get_all_user()
                elif face_id is not None:
                    # get by face_id
                    records = db_session.get_user_id(face_id=face_id)
                else:
                    # get all
                    records = db_session.get_all_user()
            else:
                records = users

            result_user = []
            if len(records) == 0:
                status = 404
                data = None
                message = 'The user is not found'
                return jsonify(Response(data, status, message).to_json()), 404
            for user in records:
                result_schedule = []
                records_detail = db_session.get_schedule(user_id=user.id, start_date=start_date, end_date=end_date)
                for schedule in records_detail:
                    response_shedule = {
                        'date': str(schedule.date),
                        'start_time': str(schedule.start_time),
                        'end_time': str(schedule.end_time),
                        'url_image': str(schedule.url_image),
                        'money': str(schedule.in_late)
                    }
                    result_schedule.append(response_shedule)
                response_user = {
                    'face_id': str(user.face_id),
                    'fullname': str(user.fullname),
                    'avatar': str(user.avatar),
                    'date_created': str(user.date_created),
                    'schedule_date': result_schedule
                }
                result_user.append(response_user)

            response = {
                'schedule': result_user
            }
            status = 200
            data = response
            message = 'success'
            return jsonify(Response(data, status, message).to_json()), 200
        except Exception:
            status = 500
            data = None
            message = 'Something Wrong'
            return jsonify(Response(data, status, message).to_json()), 500

    @app.route('/api/v1/schedules/lates/', methods=['GET'])
    def get_schedule_late():
        try:
            auth_token = request.headers.get('Authorization')
            access_token = auth_token.split(' ')[1]

            tokens = db_session.get_token(access_token)
            if len(tokens) == 0:
                status = 401
                data = None
                message = 'token is revoked'
                return jsonify(Response(data, status, message).to_json()), 401

            id = tokens[0].id
            expired = tokens[0].expires
            user_identity = tokens[0].user_identity
            revoked = tokens[0].revoked

            if expired < datetime.datetime.now() or revoked:
                db_session.update_token(id, user_identity, True)
                status = 401
                data = None
                message = 'token is revoked'
                return jsonify(Response(data, status, message).to_json()), 401

            users = db_session.get_user_id(user_identity)
            if len(users) == 0:
                status = 404
                data = None
                message = 'User is not found'
                return jsonify(Response(data, status, message).to_json()), 404
            level = users[0].level

            face_id = request.args.get('face_id')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')

            if start_date is None:
                start_date = datetime.datetime.now().date()

            if end_date is None:
                end_date = datetime.datetime.now().date()

            if level == 2:
                if face_id is None:
                    records = db_session.get_all_user()
                elif face_id is not None:
                    records = db_session.get_user_id(face_id=face_id)
                else:
                    # get all
                    records = db_session.get_all_user()
                    pass
            else:
                records = users

            result_user = []
            if len(records) == 0:
                status = 404
                data = None
                message = 'The user is not found'
                return jsonify(Response(data, status, message).to_json()), 404
            for user in records:
                result_schedule = []
                records_detail = db_session.get_schedule_late(user_id=user.id, start_date=start_date, end_date=end_date)
                for schedule in records_detail:
                    response_shedule = {
                        'date': str(schedule.date),
                        'start_time': str(schedule.start_time),
                        'end_time': str(schedule.end_time),
                        'url_image': str(schedule.url_image),
                        'money': str(schedule.in_late)
                    }
                    result_schedule.append(response_shedule)
                response_user = {
                    'face_id': str(user.face_id),
                    'fullname': str(user.fullname),
                    'avatar': str(user.avatar),
                    'date_created': str(user.date_created),
                    'schedule_date': result_schedule
                }
                result_user.append(response_user)

            response = {
                'schedule': result_user
            }
            status = 200
            data = response
            message = 'success'
            return jsonify(Response(data, status, message).to_json()), 200
        except Exception:
            status = 500
            data = None
            message = 'Something Wrong'
            return jsonify(Response(data, status, message).to_json()), 500

    @app.route('/api/v1/ots/new/', methods=['POST'])
    def register_ot():

        try:
            auth_token = request.headers.get('Authorization')
            access_token = auth_token.split(' ')[1]

            tokens = db_session.get_token(access_token)
            if len(tokens) == 0:
                status = 401
                data = None
                message = 'token is revoked'
                return jsonify(Response(data, status, message).to_json()), 401

            id = tokens[0].id
            expired = tokens[0].expires
            user_identity = tokens[0].user_identity
            revoked = tokens[0].revoked

            if expired < datetime.datetime.now() or revoked:
                db_session.update_token(id, user_identity, True)
                status = 401
                data = None
                message = 'token is revoked'
                return jsonify(Response(data, status, message).to_json()), 401

            users = db_session.get_user_id(user_identity)
            if len(users) == 0:
                status = 404
                data = None
                message = 'User is not found'
                return jsonify(Response(data, status, message).to_json()), 404
            level = users[0].level

            face_id = request.args.get('face_id')
            date = request.args.get('date')
            start_time = request.args.get('start_time')
            end_time = request.args.get('end_time')

            if level == 2:
                reg_users = db_session.get_user_id(face_id)
                if len(reg_users) == 0:
                    status = 404
                    data = None
                    message = 'face_id is not found'
                    return jsonify(Response(data, status, message).to_json()), 404
                ot = db_model.OT(reg_users[0].id, datetime.datetime.now(), date, start_time, end_time)
                db_session.insert_object(ot)
                status = 201
                data = ''
                message = 'Create OT is success'
                return jsonify(Response(data, status, message).to_json()), 201

            status = 500
            data = None
            message = 'Something is wrong'
            return jsonify(Response(data, status, message).to_json()), 500
        except Exception:
            status = 500
            data = None
            message = 'Something Wrong'
            return jsonify(Response(data, status, message).to_json()), 500

    @jwt_required
    @app.route('/api/v1/ots/', methods=['GET'])
    def get_ot():

        try:
            auth_token = request.headers.get('Authorization')
            access_token = auth_token.split(' ')[1]
            tokens = db_session.get_token(access_token)
            if len(tokens) == 0:
                status = 401
                data = None
                message = 'token is revoked'
                return jsonify(Response(data, status, message).to_json()), 401
            id = tokens[0].id
            expired = tokens[0].expires
            user_identity = tokens[0].user_identity
            revoked = tokens[0].revoked
            if expired < datetime.datetime.now() or revoked:
                db_session.update_token(id, user_identity, True)
                status = 401
                data = None
                message = 'token is revoked'
                return jsonify(Response(data, status, message).to_json()), 401

            users = db_session.get_user_id(user_identity)
            if len(users) == 0:
                status = 404
                data = None
                message = 'User is not found'
                return jsonify(Response(data, status, message).to_json()), 404
            level = users[0].level

            face_id = request.args.get('face_id')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')

            if start_date is None:
                start_date = datetime.datetime.now().date()

            if end_date is None:
                end_date = datetime.datetime.now().date()

            if level == 2:
                if face_id is None:
                    records = db_session.get_all_user()
                elif face_id is not None:
                    # get by face_id
                    records = db_session.get_user_id(face_id=face_id)
                else:
                    # get all
                    records = db_session.get_all_user()
                    pass
            else:
                records = users

            result_user = []
            if len(records) == 0:
                status = 404
                data = None
                message = 'The user is not found'
                return jsonify(Response(data, status, message).to_json()), 404
            for user in records:
                result_ots = []
                records_detail = db_session.get_ot(user_id=user.id, start_date=start_date, end_date=end_date)
                for ot in records_detail:
                    response_ot = {
                        'date_ot': str(ot.date_ot),
                        'start_time': str(ot.start_time),
                        'end_time': str(ot.end_time),
                        'date_created': str(ot.date_created)
                    }
                    result_ots.append(response_ot)
                response_user = {
                    'face_id': str(user.face_id),
                    'fullname': str(user.fullname),
                    'avatar': str(user.avatar),
                    'date_created': str(user.date_created),
                    'ot_date': result_ots
                }
                result_user.append(response_user)

            response = {
                'ot': result_user
            }
            status = 200
            data = response
            message = 'success'
            return jsonify(Response(data, status, message).to_json()), 200
        except Exception:
            status = 500
            data = None
            message = 'Something Wrong'
            return jsonify(Response(data, status, message).to_json()), 500

    @app.route('/api/v1/train', methods=['GET'])
    def train():
        classifier = train(model_save_path=MODEL_PATH, n_neighbors=2)
        if classifier == None:
            raise Exception("Model is None")
        response = {'message': 'Train is success!'}
        return jsonify(response), 200

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)