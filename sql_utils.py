import pymysql

def get_rds_connection():
    return pymysql.connect(
        host='wearables-app-db.cpoyy4oa2oky.us-east-2.rds.amazonaws.com',
        user='admin',
        password='Admin123admin123',
        db='wearables_app_db',
        cursorclass=pymysql.cursors.DictCursor
    )

