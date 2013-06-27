import re
import sqlite3
from contextlib import closing

from resources import g, app
from flask import jsonify, abort, make_response, request


def connect_db():
    """Connect to the SQLLITE DB"""
    con = sqlite3.connect(app.config.get('DATABASE'))
    con.row_factory = sqlite3.Row
    return con

def init_db():
    """initilize the database"""
    with closing(connect_db()) as db:
        with app.open_resource(app.config.get('SCHEMA')) as f:
            db.cursor().executescript(f.read())
        db.commit()
        
@app.before_request
def before_request():
    g.db = connect_db()
    
@app.teardown_request 
def teardown_request(exception):
    g.db.close()

def create_user(username, password, first_name, last_name, email_address, lead_id, use_email):
    """Adds a user to the database"""
    ret = g.db.execute('insert into users (username,password,first_name,last_name,email_address,lead_id,use_email) values (?,?,?,?,?,?,?)', 
                        [username,
                         password,
                         first_name,
                         last_name,
                         email_address,
                         lead_id, 
                         use_email])
    if ret.rowcount > 0:
        g.db.commit()
        return True
    else:
        return False

def delete_lead(username):
    """removes the lead value from the user of username"""
    ret = g.db.execute("UPDATE users SET lead_id=NULL where username=?",
                       [username])
    if ret.rowcount > 0:
        g.db.commit()
        return True
    else:
        return False

def delete_user(username):
    """removes a user from the database"""
    ret = g.db.execute('DELETE FROM users WHERE username=?',
                    [username])
    if ret.rowcount > 0:
        g.db.commit()
        return True
    else:
        return False

def get_auth_token(username):
    """Gets the authorized token (auth_token) of the user, or returns 404"""
    cur = g.db.execute("SELECT auth_token FROM users WHERE username=?",
                        [username])
    auth_token = [dict(id=row[0]) for row in cur.fetchall()]
    return auth_token

def get_authorized_user(username): 
    "get the user id, first, last that have authorized"
    cur = g.db.execute("SELECT id, first_name, last_name" \
                       " FROM users WHERE auth_token IS NOT NULL AND" \
                       " username = ?",
                       [username])
    authorized_user = [dict(id=row[0], 
                            first_name=row[1],
                            last_name=row[2]) for row in cur.fetchall()]
    return authorized_user

def get_authorized_users():
    """Get the list of users who have authorized the app"""
    cur = g.db.execute("SELECT username, first_name, last_name" \
                        " FROM users WHERE auth_token IS NOT NULL")
    # GET ALL THE AUTHORIZED USERS FOR DROPDOWN LIST
    authorized_users = [dict(id=row[0], 
                        first_name=row[1], 
                        last_name=row[2]) for row in cur.fetchall()]
    return authorized_users

def get_leads():
    """Return a list of lead username, first_name and last_name"""
    cur = g.db.execute("SELECT first_name, last_name, username" \
                       " FROM users WHERE username = " \
                       " (SELECT lead_id" \
                       " FROM users WHERE lead_id IS NOT NULL)")
    leads = [dict(first_name=row[0],
                  last_name=row[1],
                  username=row[2]) for row in cur.fetchall()]
    return leads

def get_lead(username):
    """ gets the lead username, first and last name for the user that has the lead_id populated"""
    cur = g.db.execute("SELECT first_name, last_name, username" \
                       " FROM users WHERE username = " \
                       " (SELECT lead_id FROM users WHERE username=?)",
                        [username])
    lead = [dict(first_name=row[0],
                last_name=row[1],
                username=row[2]) for row in cur.fetchall()]
    return lead

def get_notebook_ids(username):
    """  Get a comma seperated list of notebook ids from the user"""
    cur = g.db.execute("SELECT notebook_ids FROM users where username=? and notebook_ids <> ''", 
                           [username])
    notebook_ids = [dict(ids = row[0]) for row in cur.fetchall()]
    return notebook_ids

def get_shard_id(username):
    """Get the shard id of a user"""
    cur = g.db.execute("SELECT shard_id FROM users WHERE username=? and shard_id <> ''",
                       [username])
    shard_id = [dict(id=row[0]) for row in cur.fetchall()]
    return shard_id

def user_exists(username):
    """Returns true if the username exists, false if it doesn't"""
    cur = g.db.execute("SELECT COUNT(username) FROM users WHERE username=?",
                       [username])
    count = cur.fetchone()[0]
    if count > 0:
        return True
    else:
        return False
    
def get_email_status(username):
    """ Get the email address of the user if the use_email is set"""
    cur = g.db.exeuct("SELECT email_address, use_email FROM users WHERE username=?", 
                      [username])
    email_address = [dict(email_address=row[0]) for row in cur.fetchall()]
    return email_address

def get_user_info(username):
    """ Gets all user info from user table"""
    cur = g.db.execute("select * FROM users WHERE username =?",
                        [username])
    row = cur.fetchone()
    user = {}
    if row is not None:
        for key in row.keys():
            user[key] = row[key]
    return user

def get_users_info():
    """Gets all users and their info from the user table"""
    cur = g.db.execute("select username, first_name, last_name, authorized, is_admin, lead_id from users")
    users = [dict(username=row[0],
                  first_name=row[1],
                  last_name=row[2],
                  authorized=row[3],
                  is_admin=row[4],
                  lead_id=row[5]) for row in cur.fetchall()]
    return users

def set_lead(username, lead):
    """Sests the lead_id value for the user passed in as username"""
    ret = g.db.execute("UPDATE users SET lead_id=? where username=?",
                 [lead,username])
    if ret.rowcount > 0:
        g.db.commit()
        return True
    else:
        return False

def update_user(username, **kwargs):
    """Updates the user info with the values passed in"""
    payload=[]
    sql_str = 'UPDATE users'
    first=True
    for key,val in kwargs.items():
        if first:
            sql_str += " SET {}=?".format(key)
            payload.append(val)
            first=False
        else:
            sql_str += ", {}=?".format(key)
            payload.append(val)
    sql_str += ' WHERE username = ?'
    payload.append(username)
    ret = g.db.execute(sql_str, payload)
    if ret.rowcount > 0:
        g.db.commit()
        return True
    else:
        return False
        