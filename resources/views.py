# MAIN PYTHON LIBRARIES
import re
import urllib
import urlparse
import os
import oauth2 as oauth

# INTERNAL LIBRARIES
import lib
import controls
from en_xml import ENXML as EN


# FLASK LIBRARIES
from resources import app, session, redirect, url_for, flash, request, render_template
# GLOBAL CONFIG VALUES
#from resources import EN_REQUEST_TOKEN_URL,EN_AUTHORIZE_URL, EN_ACCESS_TOKEN_URL, ALLOWED_EXTENSIONS

# EN_LIB CALLS
# ALL NEED TO PROBABLY INCLUDE THE AUTH TOKEN AND POSSIBLY THE SHARD ID
from en_lib import get_notebooks, get_note, update_note, get_notebook_list, get_oauth_client, get_userstore, new_note

# PULL IN THE control calls
#from controls import get_authorized_users, get_lead, get_users_info, \
#         get_notebook_ids, get_auth_token, delete_lead, set_lead, get_user_info, \
#         user_exists, create_user, update_user, get_user_info, delete_user, get_shard_id

@app.route('/', methods=['GET', 'POST'])
def index():
    error_list = None
    # CHECK IF THE USER IS LOGGED IN, OTHERWISE REDIRECT
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    # GET THE USER INFO, REDIRECT IF NOTHING IS RETURNED
    user = controls.get_user_info(session.get('username'))
    if not user:
        redirect(url_for('logout'))
    authorized_users = controls.get_authorized_users()
    # RETURNS A JSON ObJECT OF USERNAME, FIRST AND LAST 
    lead = controls.get_lead(session.get('username'))
    if len(lead) == 0:
        lead = {'username':'', 'first_name':'', 'last_name':''}
    else:
        lead = lead[0]
    notebooks = []
    if session.get('auth_token'):
        # CHECK AND SEE IF USER HAS SELECTED NOTEBOOKS
        if user['notebook_ids'] is not None and len(user['notebook_ids']) > 0:
            guid_list = user['notebook_ids'].split(',')
            flash("Getting Notebooks and Notes")
            notebooks = get_notebooks(session.get('auth_token'), 
                                      session.get('shard_id'),
                                      guid_list) 
        else:
            return redirect(url_for('configure', guid_list=None))         
    # POST REQUESTS
    if request.method=='POST':
        error_list = []
        note_list = request.form.getlist('note')
        # GET THE NOTE CONTENT FOR EACH NOTES GUID
        for value in note_list:
            try:
                title, guid = value.split(':')
                note = get_note(session.get('auth_token'), 
                                session.get('shard_id'),
                                guid)
            except Exception as e:
                error = "Error retrieving note using guid %s" %e
                return render_template('main.html', 
                                       error=error)
            # ATTEMPT TO PARSE THE NOTE INTO A ENXML OBJECT
            # GET DOCTYPE FROM NOTE CONTENT
            rg = re.compile('(<!DOCTYPE .*?>)')
            m = rg.search(note)
            try:
                # CREATE EN OBJECT INITILIZING WITH NOTE AND DOCTYPE
                en = EN(note, doctype=m.group(1))
                # BREAK OUT TABLES
                en.break_out_tables()
                try:
                    en.set_activity_type('O')
                    en.set_activity_type('I')
                except:
                    error_list.append("Using an old Template, update your template in the future")
                    error_list.append("Unable to set Issues and Activities within the note")
                flash(update_note(session.get('auth_token'),
                                  session.get('shard_id'),
                                  en.tostring(), 
                                  guid=guid, 
                                  title=title))
                # IF EMAIL IS SET
                if user['use_email'] == 1:
                    lib.send_email(en, app.config['EMAIL_SERVER'], user['email_address'])
                    flash("Note sent as email to %s" %user['email_address'])
                # IF LEAD IS SET
                if request.form['lead'] != 'None':
                    # GET LEAD AUTH_TOKEN
                    lead = controls.get_user_info(request.form['lead'])
                    flash(new_note(shard_id=lead['shard_id'],
                                   content=en.tostring(), 
                                   title=title, 
                                   auth_token=lead['auth_token']))
                    flash("Sent note to lead: %s" %request.form['lead'])
                    controls.set_lead(session.get('username'), request.form['lead'])
                # CHANGE THE USERS LEAD ID TO THAT USED
                else: 
                    controls.delete_lead(session.get('username'))
                    lead = {'username':'', 'first_name':'', 'last_name':''}
                flash("Bug Time: %s" %en.times['B'])
                flash("Setup Time: %s" %en.times['S'])
                flash("Test Time: %s" %en.times['T'])
                flash("Session Length: %s" %en.session_length)
                en.export_xml(app.config['UPLOADED_FILE_DEST'], "%s.xml" %title)
            except Exception as e:
                error_list.append("ERROR parsing out data from note %s. Exception: [%s]" %(title, e))
    return render_template('main.html',
                            notebooks=notebooks, 
                            error=error_list,
                            authorized_users=authorized_users,
                            lead=lead) 

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """used to administrate the users of the system"""
    if request.method == 'GET':
        # SELECT ALL USERS, ADMIN_USERS, AND LEAD ID
        users = controls.get_users_info()
        # GET LEAD FIRST / LAST BASED ON lead_id
        for user in users:
            # RETURNS A JSON ObJECT OF USERNAME, FIRST AND LAST 
            lead = controls.get_lead(user['username'])
            if len(lead) > 0:
                user['lead_first'] = lead['first_name']
                user['lead_last'] = lead['last_name']
        return render_template('admin.html', users=users)
    elif request.method == 'POST':
        users = request.form.getlist('user')
        action = request.form['action']
        for user in users:
            if action == 'delete':
                controls.delete_user(user)
            elif action == 'admin':
                controls.update_user(user, is_admin=1)
            elif action == 'noadmin':
                controls.update_user(user, is_admin=0)
            elif action == 'auth':
                controls.update_user(user, auth_token=None, shard_id=None, authorized=0)
                session['authorized'] = 0
                session.pop('auth_token')
                session.pop('shard_id')
            elif action == 'pwd':
                controls.update_user(user, password='password')
        return redirect(url_for('admin'))

@app.route('/configure', methods=['GET', 'POST'])
def configure(guid_list=None):
    if request.method=='POST':
        guid_list = request.form.getlist('notebook')
        controls.update_user(session.get('username'), notebook_ids=','.join(guid_list))
        return redirect(url_for('configure'))
    else:    
        # CHECK IF THIS NEEDS SHARD/AUTH
        notebook_list=get_notebook_list(session.get('auth_token'), session.get('shard_id'))
        if guid_list is None:
            # CHECK AND SEE IF USER HAS SELECTED NOTEBOOKS
            guid_list = controls.get_notebook_ids(session.get('username'))
            if len(guid_list) == 1:
                guid_list = guid_list[0]['ids'].split(',')
            else:
                guid_list = None
        if guid_list is not None:
            for notebook in notebook_list:
                for guid in guid_list:
                    if guid == notebook['guid']:
                        notebook['selected'] = True
                        break    
    return render_template('configure.html', notebooks=notebook_list)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'GET':
        # GET USER INFO FOR SETTINGS
        user = controls.get_user_info(session.get('username'))
        if not user:
            return redirect(url_for('logout'))
        authorized_users = controls.get_authorized_users()
        lead = controls.get_lead(session.get('username'))
        if len(lead) == 0:
            lead={'first_name':'', 'last_name':'', 'username':''}
        else:
            lead=lead[0]
        return render_template('settings.html', authorized_users = authorized_users, lead=lead['username'], user=user)   
    elif request.method== 'POST':
        # UPDATE USER INFO WITH: ALL VALUES FROM THE FORM
        lead_id = request.form['lead'] if request.form['lead'] != 'None' else None
        payload ={'first_name':request.form['first_name'],
                  'last_name':request.form['last_name'],
                  'lead_id':lead_id}
        if request.form['password'] != '':
            payload['password']=request.form['password']
        if 'auth' in request.form:
            payload['authorized']=0
            payload['auth_token']=None
            session.pop('shard_id')
            session.pop('auth_token')
            session['authorized'] = 0
        payload['use_email'] = request.form['use_email']
        #payload['use_email'] = 1 if 'use_email' in request.form else 0
        controls.update_user(session.get('username'), **payload)
        flash('Settings Updated Successfully')
        session['first_name'] = request.form['first_name']
        session['last_name'] = request.form['last_name']
        return redirect(url_for('settings', lead=lead_id))
                 
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = controls.get_user_info(request.form['username'])
        if len(user) <= 0:
            error = 'Invalid username'
        elif request.form['password'] != user['password']:
            error = 'Invalid password' 
        else:
            session['logged_in'] = True
            session['username'] = request.form['username']
            session['first_name'] = user['first_name']
            session['last_name'] = user['last_name']
            # CHECK IF THIS HAS BEEN SET YET
            if user['shard_id'] is not None and len(user['shard_id']) > 0: 
                session['shard_id'] = user['shard_id']
            if user['auth_token'] is not None and len(user['auth_token']) > 0:
                session['auth_token'] = user['auth_token']
            if user['is_admin'] is not None and user['is_admin'] > 0:
                session['admin'] = True
            flash('Successfully Logged In')
            return redirect(url_for('index'))
    else:
        if session.get('logged_in'):
            return redirect(url_for('index'))
    return render_template('login.html', error=error)
 
@app.route('/logout')
def logout():
    for key in session.keys():
        session.pop(key, None)
    flash('You were logged out')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register_user():
    """Create a user in the database"""
    error = None
    # REST CALLS
    authorized_users = controls.get_authorized_users()
    if request.method == 'POST':
        if len(request.form['username'].strip()) <= 0:
            error = 'Username cannot be blank'
        else:
            if controls.user_exists(request.form['username'].strip()):
                error = 'Username already exists'
            elif len(request.form['password'].strip()) <= 0:
                error = 'Password cannot be blank'
            elif not  lib.valid_email(request.form['email_address']):
                error='Invalid Email Address'
            else:
                if request.form['lead'] == 'None':
                    lead = None
                else:
                    lead = request.form['lead']
                if request.form['use_email'] == 'True':
                    use_email = 1
                else:
                    use_email = 0
                controls.create_user(request.form['username'], 
                                     request.form['password'],
                                     request.form['first_name'],
                                     request.form['last_name'],
                                     request.form['email_address'],
                                     lead,
                                     use_email)
                flash("New User was successfully registered")
                session['logged_in'] = True
                session['first_name'] = request.form['first_name']
                session['last_name'] = request.form['last_name']
                session['username'] = request.form['username']
                return redirect(url_for('login'))
    return render_template('register.html', 
                           error=error, 
                           authorized_users=authorized_users)

@app.route('/hello')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html', name=name)

@app.route('/auth')
def auth_start():
    """Makes a request to Evernote for the request token then redirects the
    user to Evernote to authorize the application using the request token.

    After authorizing, the user will be redirected back to auth_finish()."""
    #CHECK SHARD INFO
    client = get_oauth_client()

    # Make the request for the temporary credentials (Request Token)
    callback_ip = "%s:%d" %(app.config.get('IP'), app.config.get('PORT'))
    callback_url = 'http://%s%s' % (callback_ip, url_for('auth_finish'))
    request_url = '%s?oauth_callback=%s' % (app.config['EN_REQUEST_TOKEN_URL'],
        urllib.quote(callback_url, safe=":/"))

    resp, content = client.request(request_url, 'GET')

    if resp['status'] != '200':
        raise Exception('Invalid response %s.' % resp['status'])

    request_token = dict(urlparse.parse_qsl(content))

    # Save the request token information for later
    session['oauth_token'] = request_token['oauth_token']
    session['oauth_token_secret'] = request_token['oauth_token_secret']

    # Redirect the user to the Evernote authorization URL
    return redirect('%s?oauth_token=%s' % (app.config['EN_AUTHORIZE_URL'],
        urllib.quote(session['oauth_token'])))
   
@app.route('/authComplete')
def auth_finish():
    """After the user has authorized this application on Evernote's website,
    they will be redirected back to this URL to finish the process."""

    oauth_verifier = request.args.get('oauth_verifier', '')

    token = oauth.Token(session['oauth_token'], 
                        session['oauth_token_secret'])
    token.set_verifier(oauth_verifier)

#    client = get_oauth_client()
    client = get_oauth_client(token)

    # Retrieve the token credentials (Access Token) from Evernote
    resp, content = client.request(app.config['EN_ACCESS_TOKEN_URL'], 'POST')

    if resp['status'] != '200':
        raise Exception('Invalid response %s.' % resp['status'])

    access_token = dict(urlparse.parse_qsl(content))
    authToken = access_token['oauth_token']
    
    # MAY NEED SHARD/AUTH
    userStore = get_userstore()
    user = userStore.getUser(authToken)

    # Save the users information to so we can make requests later
    session['shard_id'] = user.shardId
    session['auth_token'] = authToken
    
    # INSERT THE SESSION AND LINK TO THE USERID
    controls.update_user(session.get('username'),
                         auth_token=session.get('auth_token'), 
                         shard_id=session.get('shard_id'),
                         authorized=1)
    flash("Evernote Test Session Authorized!!")
    return redirect(url_for('index'))

@app.route('/notes/content', methods=['POST'])
def note_content():
    """ Get the thumbnail representation of the notes posted"""
    error = None
    if request.method == 'POST':
        notes = request.form.getlist('note')
        '''<img src="https://sandbox.evernote.com/shard/{{session.shard_id}}/thm/note/{{note.guid}}?auth={{session.auth_token}}&size=150">'''
        return render_template('notedetails.html', 
                               notes=notes)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # THIS USES THE NEW_NOTE CALL, so going to move that to en_lib
    if request.method=='POST':
        upload_file = request.files['file']
        if upload_file and lib.allowed_file(upload_file.filename, app.config['ALLOWED_EXTENSIONS']):
            filename = upload_file.filename
            content = upload_file.stream.getvalue()
            # CHECK IF THIS NOTE WAS EXPORTED BY THE DESKTOP CLIENT AND IF SO STRIP OUT COMPONENTS
            pattern = re.compile('(.*?!\[CDATA\[)(.*?<\/en-note>)(.*?\]\]><\/content>.*)', re.DOTALL)
            m = pattern.search(content)
            if m is not None and len(m.group(2)) > 0:
                content = m.group(2) 
            flash(new_note(content=content, title=upload_file.filename))
            with open(os.path.join(app.config['UPLOADED_FILE_DEST'], filename), 'w') as f:
                f.write(content)
        return redirect(url_for('index'))
    else:
        return render_template('upload.html') 

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    """ 
    Creates Report view of all uploaded xml files according to month and release
    """
    # THIS DATA PULLED FROM FILE STRUCTURE
    uploads = app.config['UPLOADED_FILE_DEST']
    teams = os.walk(uploads).next()[1]
    months = {}
    for team in teams:
        months[team] = os.walk(os.path.join(uploads, team)).next()[1]
    #projects = ['360', 'control_panel', 'site_intercept']
    #months = {'360':['04','06'], 'control_panel':['04', '05','06'], 'site_intercept':['04']}
    if request.method == 'POST':
        team = int(request.form['project'])
        month = int(request.form['month'])
        path = os.path.join(teams[team], months[teams[team]][month])
        return redirect('reports/report_view/%s' %path)
        # GET XML Elements from PATH to create an array of XML that can be passed into the client. 
        # return render_template('reports/report_view.html', xml_list = xml_list)
    return render_template('reports/report_index.html', teams = teams, months=months)

@app.route('/reports/report_view/')
@app.route('/reports/report_view/<team>/<month>')
def report_view(team=None, month=None):
    xml_list = []
    from lxml import objectify
    try:
        if team is not None and month is not None:
            # GET THE PATH TO ALL THE XML FILES
            path = os.path.join(app.config['UPLOADED_FILE_DEST'], team, month)
            # CREATE A LIST OF ALL THE XML FILES
            file_list = os.listdir(path)
            for filename in file_list:
                tree = objectify.parse(os.path.join(path, filename))
                root = tree.getroot()
                xml_list.append(root)
    except IOError:
        # IF THERE IS A PARSE ERROR DO NOT APPEND TO THE LIST
        pass
    return render_template('reports/report_view.html', xml_list=xml_list, team=team, month=month)  