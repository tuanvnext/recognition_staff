from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math
from sklearn import neighbors
import os
import os.path
import pickle
import face_recognition
from face_recognition.face_recognition_cli import image_files_in_folder
from imutils.video import VideoStream
import cv2
import datetime
import json

FOLDER_CURR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(FOLDER_CURR, 'model', 'trained_knn_model.clf')
DATASET_PATH = os.path.join(FOLDER_CURR, 'datasets')
UNKNOWN_PATH = os.path.join(FOLDER_CURR, 'unknown')
AVARTAR_PATH = os.path.join(FOLDER_CURR, 'avatars')

TIME_TRAIN = datetime.datetime.strptime('22:30','%H:%M').time()

import sys
scriptpath = os.path.join(FOLDER_CURR, 'backend')
sys.path.append(os.path.abspath(scriptpath))
from backend import db_session, db_model

import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost', heartbeat_interval=0))
channel = connection.channel()
channel.queue_declare(queue='detectuser', durable=True)

DISTANCE_THRESHOLD = 0.36

def train(model_save_path=None, n_neighbors=None, knn_algo='ball_tree', verbose=False):
    users = db_session.get_all_user()
    if len(users) == 0:
        return None

    X = []
    y = []
    # Loop through each person in the training set
    for user in users:
        if not os.path.isdir(os.path.join(DATASET_PATH, user.face_id)):
            continue
        # Loop through each training image for the current person
        for img_path in image_files_in_folder(os.path.join(DATASET_PATH, user.face_id)):
            image = face_recognition.load_image_file(img_path)
            # print(type(image))
            # print(image)
            face_bounding_boxes = face_recognition.face_locations(image)

            if len(face_bounding_boxes) != 1:
                if verbose:
                    print("Image {} not suitable for training: {}".format(img_path, "Didn't find a face" if len(face_bounding_boxes) < 1 else "Found more than one face"))
            else:
                # Add face encoding for current image to the training set
                X.append(face_recognition.face_encodings(image, known_face_locations=face_bounding_boxes, num_jitters=10)[0])
                y.append(user.face_id)

    # Determine how many neighbors to use for weighting in the KNN classifier
    if n_neighbors is None:
        n_neighbors = int(round(math.sqrt(len(X))))
        if verbose:
            print("Chose n_neighbors automatically: ", n_neighbors)

    # Create and train the KNN classifier
    knn_clf = neighbors.KNeighborsClassifier(n_neighbors=n_neighbors, algorithm=knn_algo, weights='distance')
    knn_clf.fit(X, y)

    # Save the trained KNN classifier
    if model_save_path is not None:
        with open(model_save_path, 'wb') as f:
            pickle.dump(knn_clf, f)

    return knn_clf

def predict(frame, knn_clf=None, model_path=None, distance_threshold=DISTANCE_THRESHOLD):
    """
    Recognizes faces in given image using a trained KNN classifier
    :param X_img_path: path to image to be recognized
    :param knn_clf: (optional) a knn classifier object. if not specified, model_save_path must be specified.
    :param model_path: (optional) path to a pickled knn classifier. if not specified, model_save_path must be knn_clf.
    :param distance_threshold: (optional) distance threshold for face classification. the larger it is, the more chance
           of mis-classifying an unknown person as a known one.
    :return: a list of names and face locations for the recognized faces in the image: [(name, bounding box), ...].
        For faces of unrecognized persons, the name 'unknown' will be returned.
    """
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    if knn_clf is None and model_path is None:
        raise Exception("Must supply knn classifier either thourgh knn_clf or model_path")

    # Load a trained KNN model (if one was passed in)
    if knn_clf is None:
        with open(model_path, 'rb') as f:
            knn_clf = pickle.load(f)

    X_face_locations = face_recognition.face_locations(rgb)

    # If no faces are found in the image, return an empty result.
    if len(X_face_locations) == 0:
        return []

    # Find encodings for faces in the test iamge
    faces_encodings = face_recognition.face_encodings(rgb, known_face_locations=X_face_locations)

    # Use the KNN model to find the best matches for the test face
    closest_distances = knn_clf.kneighbors(faces_encodings, n_neighbors=1)
    are_matches = [closest_distances[0][i][0] for i in range(len(X_face_locations))]

    # Predict classes and remove classifications that aren't within the threshold
    return [(pred, loc, dist) for pred, loc, dist in zip(knn_clf.predict(faces_encodings), X_face_locations, are_matches)]

def update_detect_person(face_id, frame):
    '''
    when staff is the first time checkin then save image.
    from the seconds, update schedule
    :param face_id: id of staff
    :param frame: image of staff
    :return: null
    '''
    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    if face_id == 'unknown':
        # save_image(os.path.join(UNKNOWN_PATH, face_id), frame)
        return
    users = db_session.get_user_id(face_id)
    if len(users) == 0:
        return
    records = db_session.check_schedule(today, users[0].id)
    if len(records) > 0:
        if current_time not in records[0].modify:
            modify = records[0].modify + ',' + current_time
            log = db_model.Schedule(records[0].user_id, today, current_time, current_time, 'Null', modify)
            db_session.update_schedule(log)
    else:
        filename = save_image(os.path.join(DATASET_PATH, face_id), frame)
        log = db_model.Schedule(users[0].id, today, current_time, current_time, filename, current_time)
        db_session.insert_object(log)
        #
        message = {'face_id': users[0].face_id, 'fullname': users[0].fullname, 'avatar': users[0].avatar, 'time_in':current_time}
        channel.basic_publish(exchange='',routing_key='detectuser', body=json.dumps(message), properties=pika.BasicProperties(
                     delivery_mode = 2, # make message persistent
                  ))

def save_image(path, frame):
    if not os.path.isdir(path):
        os.mkdir(path)
    try:
        files = [int(os.path.splitext(f)[0]) for f in os.listdir(path)]
        if len(files) == 0:
            filename = '1.png'
        else:
            filename = str(max(files) + 1) + '.png'
        cv2.imwrite(os.path.join(path, filename), frame)
        return filename
    except Exception as e:
        print('cant save image with error: ' % e)
        return None

def check_time_to_train():
    now = datetime.datetime.now()
    if now.time() == TIME_TRAIN:
        knn = train(model_save_path=MODEL_PATH, n_neighbors=2)
        db_session.update_admin(now.date())

def main(is_train=False):
    print("Training KNN classifier...")
    if not os.path.isfile(MODEL_PATH) or is_train:
        classifier = train(model_save_path=MODEL_PATH, n_neighbors=2)
        if classifier == None:
            raise Exception("Model is None")

    vs = VideoStream(src=0).start()
    while True:

        check_time_to_train()

        frame = vs.read()
        predictions = predict(frame, model_path=MODEL_PATH)

        for name, (top, right, bottom, left), dist in predictions:
            print("- Found {0} with distance: ({1:.2f})".format(name, dist))
            crop_img = frame[top:bottom, left:right]
            if dist >= DISTANCE_THRESHOLD:
                name = 'unknown'
            update_detect_person(name, crop_img)
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            y = top - 15 if top - 15 > 15 else top + 15
            cv2.putText(frame, '{0}: {1:.2f}'.format(name, dist), (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
    cv2.destroyAllWindows()
    vs.stop()
    #close rabbitMQ
    connection.close()

if __name__ == "__main__":
    main(is_train=False)