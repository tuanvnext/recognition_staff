from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import asc, or_
from flask_jwt_extended import decode_token

import datetime
import db_model
import db_log
Base = declarative_base()
ENGINE = db_model.get_engine()
Base.metadata.bind = ENGINE
DBSession = sessionmaker(bind=ENGINE)

#--------insert


def insert_object(object):
    session = DBSession()
    try:
        session.add(object)
        session.commit()
    except Exception as e:
        db_log.error('error at inserting object')
        db_log.error('error info: %s' % str(e))
        session.rollback()
    finally:
        session.close()

def insert_list_object(list_object):
    session = DBSession()
    try:
        session.bulk_save_objects(list_object)
        session.commit()
    except Exception as e:
        db_log.error('exxor at inserting %d objects' % len(list_object))
        db_log.error('error info: %s' % str(e))
        session.rollback()
    finally:
        session.close()


#-----------user


def get_user_id(face_id):
    session = DBSession()
    try:
        query = session.query(db_model.User).filter_by(face_id=face_id)
        records = query.all()
        if len(records) < 1:
            db_log.error('Cant find user has face_id: %s' % str(face_id))
    except Exception as e:
        db_log.error('error info: %s' % str(e))
        db_log.error('error at get_user_by_id id of user: %s'%face_id)
        records = []
    finally:
        session.close()
    return records

def get_all_user(face_id=None, start=None, end=None):
    session = DBSession()
    try:
        if face_id is not None:
            records = session.query(db_model.User)\
                .filter(db_model.User.face_id == face_id)\
                .order_by(asc(db_model.User.face_id)).all()
        elif start is not None and end is not None:
            records = session.query(db_model.User) \
                .filter(or_(db_model.User.date_created > start, db_model.User.date_created == start)) \
                .filter(db_model.User.date_created < end) \
                .order_by(asc(db_model.User.face_id)).all()
        else:
            records = session.query(db_model.User) \
                .order_by(asc(db_model.User.face_id)).all()
    except Exception as e:
        db_log.error('error info: %s' % str(e))
        db_log.error('error at get_all_user')
        records = []
    finally:
        session.close()
    return records

def update_user(face_id, avatar):
    session = DBSession()
    try:
        session.query(db_model.User).filter_by(face_id=face_id).update({"avatar": avatar})
        session.commit()
    except Exception as e:
        db_log.error('error at update_schedule object')
        db_log.error('error info: %s' % str(e))
        session.rollback()
    finally:
        session.close()


#---------schedule


def check_schedule(date, user_id):
    session = DBSession()
    try:
        records = session.query(db_model.Schedule).filter_by(date=date, user_id=user_id).all()
    except Exception as e:
        db_log.error('error info: %s' % str(e))
        db_log.error('error at check_user_by_date_and_user with date: {0}; user_id: {1}'.format(date, user_id))
        records = []
    finally:
        session.close()
    return records

def update_schedule(schedule):
    session = DBSession()
    try:
        session.query(db_model.Schedule).filter_by(date=schedule.date, user_id=schedule.user_id).update({"end_time": schedule.end_time, "modify": schedule.modify})
        session.commit()
    except Exception as e:
        db_log.error('error at update_schedule object')
        db_log.error('error info: %s' % str(e))
        session.rollback()
    finally:
        session.close()

def get_schedule(start_date, user_id, end_date):
    session = DBSession()
    try:
        query = session.query(db_model.AdminSchedule) \
            .filter(or_(db_model.AdminSchedule.date > start_date, db_model.AdminSchedule.date == start_date)) \
            .filter(db_model.AdminSchedule.date < end_date) \
            .filter(db_model.AdminSchedule.user_id == user_id)

        records = query.all()
    except Exception as e:
        db_log.error('error info: %s' % str(e))
        db_log.error('error at get_schedule')
        records = []
    finally:
        session.close()
    return records

def get_schedule_late(start_date, user_id, end_date):
    session = DBSession()
    try:
        query = session.query(db_model.AdminSchedule) \
            .filter(or_(db_model.AdminSchedule.date > start_date, db_model.AdminSchedule.date == start_date)) \
            .filter(db_model.AdminSchedule.date < end_date) \
            .filter(db_model.AdminSchedule.user_id == user_id) \
            .filter(or_(db_model.AdminSchedule.in_late > 0, db_model.AdminSchedule.out_early > 0))
        records = query.all()
    except Exception as e:
        db_log.error('error info: %s' % str(e))
        db_log.error('error at get_schedule_late')
        records = []
    finally:
        session.close()
    return records


#-------------token

def update_token(token_id, user, revoked):
    session = DBSession()
    try:
        session.query(db_model.TokenBlacklist).filter_by(id=token_id, user_identity=user).update({"revoked": revoked})
        session.commit()
    except Exception as e:
        db_log.error('error at update_token object')
        db_log.error('error info: %s' % str(e))
        session.rollback()
    finally:
        session.close()

def delete_token(token):
    session = DBSession()
    try:
        session.delete(token)
        session.commit()
    except Exception as e:
        db_log.error('error at delete_token object')
        db_log.error('error info: %s' % str(e))
        session.rollback()
    finally:
        session.close()

def check_token(decoded_token):
    jti = decoded_token['jti']
    session = DBSession()
    try:
        record = session.query(db_model.TokenBlacklist).filter_by(jti=jti).one()
    except Exception as e:
        db_log.error('error info: %s' % str(e))
        db_log.error('error at check_token with jti: {0}'.format(jti))
        return False
    finally:
        session.close()
    return record.revoked

def get_token(access_token):
    decoded_token = decode_token(access_token, allow_expired=True)
    jti = decoded_token['jti']
    session = DBSession()
    try:
        records = session.query(db_model.TokenBlacklist).filter_by(jti=jti).all()
    except Exception as e:
        db_log.error('error info: %s' % str(e))
        db_log.error('error at get_token')
        records = []
    finally:
        session.close()
    return records


#-----------OT-------------


def get_ot(start_date, user_id, end_date):
    session = DBSession()
    try:
        query = session.query(db_model.OT) \
            .filter(or_(db_model.OT.date_ot > start_date, db_model.OT.date_ot == start_date)) \
            .filter(db_model.OT.date_ot < end_date) \
            .filter(db_model.OT.user_id == user_id)
        records = query.all()
    except Exception as e:
        db_log.error('error info: %s' % str(e))
        db_log.error('error at get_ots')
        records = []
    finally:
        session.close()
    return records


#----- admin
def update_admin(date):
    session = DBSession()
    try:
        records = session.query(db_model.Schedule)\
            .filter(db_model.Schedule.date == date).all()

        for record in records:
            user_id = record.user_id
            date = record.date
            start_time = record.start_time
            end_time = record.end_time
            url_image = record.url_image
            records_formtime_in = session.query(db_model.FormTime)\
                .filter(db_model.FormTime.start < start_time)\
                .filter(db_model.FormTime.end > start_time).all()
            if len(records_formtime_in) == 0:
                money = -1
            else:
                money = records_formtime_in[0].money
            records_formtime_out = session.query(db_model.FormTime) \
                .filter(db_model.FormTime.id == 6).all()
            if len(records_formtime_out) == 0:
                out_early = -1
            else:
                duration = datetime.datetime.combine(datetime.date.min, records_formtime_out[0].start) - datetime.datetime.combine(datetime.date.min, end_time)
                if duration.total_seconds() < 0:
                    out_early = 0
                else:
                    out_early = duration.total_seconds()/60
            records_ot = session.query(db_model.OT) \
                .filter(db_model.OT.user_id == user_id) \
                .filter(db_model.OT.date_ot == date).all()
            if len(records_ot) == 0:
                ot_id = -1
            else:
                ot_id = records_ot[0].id

            adminSchedule = db_model.AdminSchedule(user_id, date, start_time, end_time, url_image, money, str(out_early), ot_id)
            insert_object(adminSchedule)
    except Exception as e:
        db_log.error('error info: %s' % str(e))
        db_log.error('error at update_admin')
    finally:
        session.close()

if __name__ == '__main__':
    tuanlv = db_model.User(face_id='tuanlv', password='tuanlv', date_created = str(datetime.datetime.now()), level=1, fullname='Le Van Tuan', avatar= '/api/avatars/tuanlv/0.jpg')
    ducpv = db_model.User(face_id='ducpv', password='ducpv', date_created = str(datetime.datetime.now()), level=1, fullname='Pham Van Duc',avatar= '/api/avatars/ducpv/0.jpg')
    hungvv = db_model.User(face_id='hungvv', password='hungv', date_created = str(datetime.datetime.now()), level=1, fullname='Vuong Van Hung',avatar= '/api/avatars/hungvv/0.jpg')
    phuongdv = db_model.User(face_id='phuongdv', password='phuongdv', date_created = str(datetime.datetime.now()), level=2, fullname='Dang Van Phuong',avatar= '/api/avatars/phuongdv/0.jpg')
    insert_object(tuanlv)
    insert_object(ducpv)
    insert_object(hungvv)
    insert_object(phuongdv)

    r1 = db_model.FormTime(start='7:00:00', end='8:46:00', money=0)
    r2 = db_model.FormTime(start='8:45:59', end='9:16:00', money=20000.0)
    r3 = db_model.FormTime(start='9:15:59', end='9:46:00', money=40000.0)
    r4 = db_model.FormTime(start='9:45:59', end='10:16:00', money=60000.0)
    r5 = db_model.FormTime(start='10:15:59', end='12:00:00', money=-0.5)
    r6 = db_model.FormTime(start='17:30:00', end='22:00:00', money=0)
    insert_object(r1)
    insert_object(r2)
    insert_object(r3)
    insert_object(r4)
    insert_object(r5)
    insert_object(r6)

    s1 = db_model.Schedule(user_id=1, date=20181010, start='8:30:00', end='17:30:00', url_image='test', modify='17:30:00')
    s2 = db_model.Schedule(user_id=1, date=20181011, start='8:30:00', end='17:30:00', url_image='test', modify='17:30:00')
    s3 = db_model.Schedule(user_id=2, date=20181010, start='9:00:00', end='17:30:00', url_image='test', modify='17:30:00')
    s4 = db_model.Schedule(user_id=2, date=20181011, start='9:30:00', end='17:30:00', url_image='test', modify='17:30:00')
    s5 = db_model.Schedule(user_id=3, date=20181010, start='9:15:00', end='17:30:00', url_image='test', modify='17:30:00')
    s6 = db_model.Schedule(user_id=3, date=20181011, start='10:00:00', end='17:30:00', url_image='test', modify='17:30:00')
    insert_object(s1)
    insert_object(s2)
    insert_object(s3)
    insert_object(s4)
    insert_object(s5)
    insert_object(s6)

    ot1 = db_model.OT(user_id=1, date_created = str(datetime.datetime.now()), date_ot=20181015, start_time='18:00:00', end_time='20:00:00')
    ot2 = db_model.OT(user_id=2, date_created = str(datetime.datetime.now()), date_ot=20181015, start_time='19:00:00', end_time='21:00:00')
    insert_object(ot1)
    insert_object(ot2)

    update_admin(20181010)
    update_admin(20181011)
    # Bienpt = db_model.User(face_id='Bienpt', fullname='Phan Trong Bien', avatar='/api/avatars/Bientpt.jpg')
    # Datnv = db_model.User(face_id='Datnv', fullname='Nguyen Van Dat', avatar='/api/avatars/Datnv/0.jpg')
    # Diepct = db_model.User(face_id='Diepct', fullname='Cu Thi Diep', avatar='/api/avatars/Diepct/0.jpg')
    # Diepnv = db_model.User(face_id='Diepnv', fullname='Nguyen Van Diep', avatar='/api/avatars/Diepnv/0.jpg')
    # Ducpv = db_model.User(face_id='Ducpv', fullname='Pham Trong Duc',avatar= '/api/avatars/Ducpv/0.jpg')
    # Dungnt2 = db_model.User(face_id='Dungnt2', fullname='Nguyen Dung',avatar= '/api/avatars/Dungnt2/0.jpg')
    # HoangAnh = db_model.User(face_id='HoangAnh', fullname='Hoang Thi Anh',avatar= '/api/avatars/HoangAnh/0.jpg')
    # Hungpb = db_model.User(face_id='Hungpb', fullname='Pham Ba Hung',avatar= '/api/avatars/Hungpb/0.jpg')
    # Huudv = db_model.User(face_id='Huudv', fullname='Do Van Huu', avatar='/api/avatars/Huudv/0.jpg')
    # Lanhnt = db_model.User(face_id='Lanhnt', fullname='Nguyen Thi Lanh',avatar= '/api/avatars/Lanhnt/0.jpg')
    # Lienbp = db_model.User(face_id='Lienbp', fullname='Bui Phuong Lien', avatar='/api/avatars/Lienbp/0.jpg')
    # Locnt = db_model.User(face_id='Locnt', fullname='Nguyen Thi Loc',avatar= '/api/avatars/Locnt/0.jpg')
    # Luanvv = db_model.User(face_id='Luanvv', fullname='Vu Van Luan',avatar= '/api/avatars/Luanvv/0.jpg')
    # Lucnv = db_model.User(face_id='Lucnv', fullname='Nguyen Van Luc', avatar='/api/avatars/Lucnv/0.jpg')
    # Luongvh = db_model.User(face_id='Luongvh', fullname='Vu Hien Luong',avatar= '/api/avatars/Luongvh/0.jpg')
    # Ngannt = db_model.User(face_id='Ngannt', fullname='Nguyen Thi Ngan', avatar='/api/avatars/Ngannt/0.jpg')
    # Phuongdv = db_model.User(face_id='Phuongdv', fullname='Dang Van Phuong',avatar= '/api/avatars/Phuongdv/0.jpg')
    # Quynhtt = db_model.User(face_id='Quynhtt', fullname='Tran Thi Quynh', avatar='/api/avatars/Quynhtt/0.jpg')
    # Sonnh = db_model.User(face_id='Sonnh', fullname='Nguyen Huy Son', avatar='/api/avatars/Sonnh/0.jpg')
    # Sonnv = db_model.User(face_id='Sonnv', fullname='Nguyen Van Son', avatar='/api/avatars/Sonnv/0.jpg')
    # ThanhHoa = db_model.User(face_id='ThanhHoa', fullname='Thanh Hoa',avatar= '/api/avatars/ThanhHoa/0.jpg')
    # Thao = db_model.User(face_id='Thao', fullname='Thao', avatar='/api/avatars/Thao/0.jpg')
    # Thuannq = db_model.User(face_id='Thuannq', fullname='Nguyen Quang Thuan',avatar= '/api/avatars/Thuannq/0.jpg')
    # Truongtx = db_model.User(face_id='Truongtx', fullname='Tong Xuan Truong', avatar='/api/avatars/Truongtx/0.jpg')
    # TuanAnh = db_model.User(face_id='TuanAnh', fullname='Tuan Anh', avatar='/api/avatars/TuanAnh/0.jpg')
    # Tuanlv = db_model.User(face_id='Tuanlv', fullname='Le Van Tuan',avatar= '/api/avatars/Tuanlv/0.jpg')
    # Tungds = db_model.User(face_id='Tungds', fullname='Do Son Tung', avatar='/api/avatars/Tungds/0.jpg')
    # Tungnt = db_model.User(face_id='Tungnt', fullname='Nguyen Thanh Tung', avatar='/api/avatars/Tungnt/0.jpg')
    # VietAnh = db_model.User(face_id='VietAnh', fullname='Viet Anh',avatar= '/api/avatars/VietAnh/0.jpg')
    # Vietdb = db_model.User(face_id='Vietdb', fullname='Duong Bao Viet',avatar= '/api/avatars/Vietdb/0.jpg')
    # insert_object(Bienpt)
    # insert_object(Datnv)
    # insert_object(Diepct)
    # insert_object(Diepnv)
    # insert_object(Ducpv)
    # insert_object(Dungnt2)
    # insert_object(HoangAnh)
    # insert_object(Hungpb)
    # insert_object(Huudv)
    # insert_object(Sonnh)
    # insert_object(Lanhnt)
    # insert_object(Lienbp)
    # insert_object(Locnt)
    # insert_object(Luanvv)
    # insert_object(Lucnv)
    # insert_object(Luongvh)
    # insert_object(Ngannt)
    # insert_object(Phuongdv)
    # insert_object(Quynhtt)
    # insert_object(Sonnv)
    # insert_object(ThanhHoa)
    # insert_object(Thao)
    # insert_object(Thuannq)
    # insert_object(Truongtx)
    # insert_object(TuanAnh)
    # insert_object(Tuanlv)
    # insert_object(Tungds)
    # insert_object(Tungnt)
    # insert_object(VietAnh)
    # insert_object(Vietdb)

