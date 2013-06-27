import re
import sqlite3
from contextlib import closing

from resources import g, app
from flask import jsonify, abort, make_response, request

from controls import *
  
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)  

@app.errorhandler(400)
def missing_resource(error):
    return make_response(jsonify({'error': 'Missing Values in request'}), 400)
          
@app.errorhandler(500)
def server_error(error):
    return make_response(jsonify({'error': 'Server Error processing request'}), 500)

@app.route('/api/v1.0/auth_token/<username>', methods=['GET'])
def rest_get_auth_token(username):
    """Gets the authorized token (auth_token) of the user, or returns 404"""
    auth_token = get_auth_token(username)
    if len(auth_token) == 0:
        abort(404)
    return jsonify({'auth_token':auth_token[0]})

@app.route('/api/v1.0/authorized/<username>', methods=['GET'])
def rest_get_authorized_user(username): 
    "get the user id, first, last that have authorized"
    authorized_user = get_authorized_user(username)
    if len(authorized_user) == 0:
        abort(404)
    return jsonify({'user': authorized_user[0]})
    
@app.route('/api/v1.0/authorized/', methods=['GET'])   
def rest_get_authorized_users():
    """Get the list of users who have authorized the app"""
    return jsonify({'users':get_authorized_users()})

###############
# LEAD
###############
@app.route('/api/v1.0/lead/', methods=['DELETE'])
def rest_delete_lead():
    """removes the lead value from the user of username"""
    if not request.json or not 'username' in request.json:
        abort(400)
    username = request.json['username']
    ret = delete_lead(username)
    if ret:
        return jsonify({'result':'success', 
                        'user':username, 
                        'desc':'lead username removed for user'})
    else:
        abort(500)

@app.route('/api/v1.0/lead/', methods=['GET'])
def rest_get_leads():
    """Return a list of lead username, first_name and last_name"""
    return jsonify({'leads':get_leads()})

@app.route('/api/v1.0/lead/<username>', methods=['GET'])
def rest_get_lead(username):
    """ gets the lead username, first and last name for the user that has the lead_username populated"""
    lead = get_lead(username)
    if len(lead) == 0:
        abort(404)
    return jsonify( { 'lead':lead[0] } )

@app.route('/api/v1.0/lead/', methods=['POST'])
def rest_set_lead():
    """Sests the lead_id value for the user passed in as username"""
    if not request.json or 'username' not in request.json or'lead' not in request.json:
        abort(400)
    username = request.json['username']
    lead = request.json['lead']
    ret = set_lead()
    if ret:
        return jsonify({'result':'success','user':username,'lead_id':lead})
    else:
        abort(500)

###############
# NOTEBOOKS
###############

@app.route('/api/v1.0/notebook_ids/<username>', methods=['GET'])
def rest_get_notebook_ids(username):
    """  Get a comma seperated list of notebook ids from the user"""
    notebook_ids = get_notebook_ids(username)
    if len(notebook_ids) == 0:
        abort(404)
    return jsonify({'notebook':notebook_ids[0]})

###############
# USERS
###############

@app.route('/api/v1.0/users/exists/<username>', methods=['GET'])
def rest_get_user_exists(username):
    exists = get_user_exists(username)
    if exists:
        return jsonify({'username':username, 'status':'exists'})
    else:
        return jsonify({'username':username, 'status':'does not exist'})

@app.route('/api/v1.0/users', methods=['GET'])
def rest_get_users_info():
    users = get_users_info()
    return jsonify({'users':users})

@app.route('/api/v1.0/users/<username>', methods=['GET'])
def rest_get_user_info(username):
    user = get_user_info(username)
    if len(user)  == 0:
        abort(404)
    return jsonify({'user':user[0]})

@app.route('/api/v1.0/users', methods=['DELETE'])
def rest_delete_user():
    if not request.json or 'username' not in request.json:
        abort(400)
    username = request.json['username']
    ret = delete_user(username)
    if ret:
        return jsonify({'result':'success', 'user':username, 'desc':'User removed from database'})
    else:
        abort(500)
        
@app.route('/api/v1.0/users', methods=['UPDATE'])
def rest_update_user():
    if not request.json or 'username' not in request.json:
        abort(400)
    username = request.json['username']
    del request.json['username']
    ret = update_user(username, request.json)
    if ret:
        return jsonify({'result':'success', 'user':username, 'dec':'updated user'})
    else:
        abort(500)
        
@app.route('/api/v1.0/users', methods=['POST'])
def rest_create_user():
    if not request.json:
        abort(400)
    if 'username' not in request.json:
        abort(400)
    if 'first_name' not in request.json:
        abort(400)
    if 'last_name' not in request.json:
        abort(400)
    if 'password' not in request.json:
        abort(400)
    if 'email_address' not in request.json:
        abort(400)
    if 'use_email' not in request.json:
        abort(400)
    if 'lead_id' not in request.json:
        abort(400)
    # VALIDATION ON USERNAME, FIRST, LAST, EMAIL NEEDS TO HAPPEN
    ret = create_user(request.json['username'], 
                      request.json['password'], 
                      request.json['first_name'], 
                      request.json['last_name'], 
                      request.json['email_address'], 
                      request.json['lead_id'], 
                      request.json['use_email'])
    if ret:
        return jsonify({'result':'success'})
    else:
        abort(500)