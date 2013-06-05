#!/usr/bin/python
# MAIN LIBRARIES
import urlparse
import urllib
import sqlite3
import re 
import socket
import oauth2 as oauth

# EVERNOTE LIBRARIES
import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.type.ttypes as Types
import evernote.edam.error.ttypes as Errors

# ORGINIALLY WAS THRIFT, USING EVERNOTE LIBRARIES INSTEAD
from evernote.api.client import TBinaryProtocol
from evernote.api.client import THttpClient

# CONTEXT AND FLASK 3rd PARTY LIBRARIES
from contextlib import closing
from flask import Flask, session, redirect, url_for, request, \
                  render_template, g, flash
# INTERNAL LIBRARIES
from lib.enxml import ENXML as EN


# CONFIGURATION
APP_SECRET_KEY = \
    'YOUR KEY HERE'

EN_CONSUMER_KEY = 'zible'
EN_CONSUMER_SECRET = '367c429f031417b3'

EN_REQUEST_TOKEN_URL = 'https://sandbox.evernote.com/oauth'
EN_ACCESS_TOKEN_URL = 'https://sandbox.evernote.com/oauth'
EN_AUTHORIZE_URL = 'https://sandbox.evernote.com/OAuth.action'

EN_HOST = "sandbox.evernote.com"
EN_USERSTORE_URIBASE = "https://" + EN_HOST + "/edam/user"
EN_NOTESTORE_URIBASE = "https://" + EN_HOST + "/edam/note/"

DATABASE = 'webapp.db'
SCHEMA = 'schema.sql'

UPLOADED_FILE_DEST="upload"
ALLOWED_EXTENSIONS = set(['xml', 'enex'])

#IP = '10.1.50.32'
IP='127.0.0.1'
PORT = 5000

app = Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.do')
app.config.from_object(__name__)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def connect_db():
    """Connect to the SQLLITE DB"""
    return sqlite3.connect(app.config.get('DATABASE'))

def get_oauth_client(token=None):
    """Return an instance of the OAuth client."""
    consumer = oauth.Consumer(EN_CONSUMER_KEY, EN_CONSUMER_SECRET)
    if token:
        client = oauth.Client(consumer, token)
    else:
        client = oauth.Client(consumer)
    return client

def get_notestore():
    """Return an instance of the Evernote NoteStore. Assumes that 'shardId' is
    stored in the current session."""
    shardId = session.get('shardId')
    noteStoreUri = EN_NOTESTORE_URIBASE + shardId
    noteStoreHttpClient = THttpClient.THttpClient(noteStoreUri)
    noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
    noteStore = NoteStore.Client(noteStoreProtocol)
    return noteStore

def get_userstore():
    """Return an instance of the Evernote UserStore."""
    userStoreHttpClient = THttpClient.THttpClient(EN_USERSTORE_URIBASE)
    userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHttpClient)
    userStore = UserStore.Client(userStoreProtocol)
    return userStore

def init_db():
    """initilize the database"""
    with closing(connect_db()) as db:
        with app.open_resource(app.config.get('SCHEMA')) as f:
            db.cursor().executescript(f.read())
        db.commit()

def get_authorized_users(username=None):
    """Get the list of users who have authorized the app"""
    if username is not None:
        cur = g.db.execute("SELECT id, first_name, last_name" \
                           " FROM users WHERE identifier IS NOT NULL AND" \
                           " username != ?",
                           [username])
    else:
        cur = g.db.execute("SELECT id, first_name, last_name" \
                           " FROM users WHERE identifier IS NOT NULL")
    # GET ALL THE AUTHORIZED USERS FOR DROPDOWN LIST
    authorized_users = [dict(id=row[0], 
                        first_name=row[1], 
                        last_name=row[2]) for row in cur.fetchall()]
    return authorized_users

def get_lead(username):
    """ gets the lead id, first and last name from the id"""
    
    lead = dict(id=None, first_name=None, last_name=None)
    cur = g.db.execute('SELECT leadID FROM users where username=?',
                        [username])
    row = cur.fetchall()
    if len(row) > 0 and row[0][0] is not None:
        lead= row[0][0]
        cur = g.db.execute('SELECT id, first_name, last_Name FROM users where id=?',
                           [lead])
        row = cur.fetchone()
        lead = dict(id=row[0],
                    first_name=row[1],
                    last_name=row[2])
    return lead

def get_notebooks():
    """ Creates a list of notebooks and notes metadata"""
    authToken = session.get('identifier')
    noteStore = get_notestore()
    notebooks = noteStore.listNotebooks(authToken)
    notebook_list = []
    for notebook in notebooks:
        notebook_dict = {'name':notebook.name, 'guid':notebook.guid}
        notebook_dict['notes'] = get_note_metadata(notebook_dict['guid'])
        notebook_dict['session_id'] = session.get('shardId')
        notebook_list.append(notebook_dict)   
    return notebook_list

def get_note_metadata(guid):
    """ Finds all the notes metadata"""
    authToken = session['identifier']
    noteStore = get_notestore()
    nb_filter = NoteStore.NoteFilter()
    nb_filter.ascending = True
    nb_spec = NoteStore.NotesMetadataResultSpec(includeTitle=True,
                                                includeContentLength=True,
                                                includeNotebookGuid=True, 
                                                includeTagGuids=True, 
                                                includeAttributes=True,
                                                includeLargestResourceMime=True,
                                                includeLargestResourceSize=True)
    nb_filter.notebookGuid = guid
    note_list = noteStore.findNotesMetadata(authToken, nb_filter, 0, 100, nb_spec)
    if len(note_list.notes) != note_list.totalNotes:
        note_list.append(noteStore.findNotesMetadata(authToken, 
                                                     nb_filter, 
                                                     len(note_list.notes), 
                                                     100, 
                                                     nb_spec))
    return note_list.notes

def get_note(guid):
    """Takes the guid of a note and returns the content"""
    guid = guid
    authToken = session['identifier']
    noteStore = get_notestore()
    note = noteStore.getNote(authToken, 
                             guid, 
                             withContent=True, 
                             withResourcesData=False, 
                             withResourcesRecognition=False, 
                             withResourcesAlternateData=False)
    #output = open('content2.xml', 'w')
    #note.content.replace('&nbsp', '&#160')
    #output.write(note.content)
    #output.close()
    #import xml.etree.ElementTree as ET
    #tree = ET.parse('content2.xml')
    #root = tree.getroot()
    #tree.write('content.xml', 'utf-8', True)
    return note.content

def update_note(content, guid, title):
    """Create a new note template from a local file, or the content passed in"""
    # GET THE NOTESTORE
    authToken = session['identifier']
    noteStore = get_notestore()
    template_note = Types.Note()
    template_note.title = title
    template_note.content = content
    template_note.guid = guid
    try:
        noteStore.updateNote(authToken, template_note)
    except Errors.EDAMUserException as edue:
        return "EDAMUserException: {}".format(edue)
    except Errors.EDAMNotFoundException as edue:
        return "EDAMNNotFoundException: Invalid parent notebook GUID"
    return 'Note %s Successfully parsed and updated' %title

@app.before_request
def before_request():
    g.db = connect_db()
    
@app.teardown_request 
def teardown_request(exception):
    g.db.close()

##################
# WEB NAVIGATION
##################

@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    # CHECK IF THE USER IS LOGGED IN, OTHERWISE REDIRECT
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    authorized_users = get_authorized_users(session.get('username'))
    lead = get_lead(session.get('username'))
    notebooks = []
    if session.get('identifier'):
        notebooks = get_notebooks()          
    # POST REQUESTS
    if request.method=='POST':
        error_list = []
        note_list = request.form.getlist('note')
        # GET THE NOTE CONTENT FOR EACH NOTES GUID
        for value in note_list:
            try:
                title, guid = value.split(':')
                note = get_note(guid)
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
                flash(update_note(en.tostring(), guid=guid, title=title))
                # IF LEAD IS SET
                if request.form['lead'] != 'None':
                    # GET LEAD IDENTIFIER
                    cur = g.db.execute("SELECT identifier FROM users WHERE id=?",
                                      [request.form['lead']])
                    row = cur.fetchone()
                    authToken = row[0]
                    flash(new_note(en.tostring(), title=title, authToken=authToken))
                # CHANGE THE USERS LEAD ID TO THAT USED
                if request.form['lead'] == 'None':
                    leadID = None
                else:
                    leadID = request.form['lead']
                g.db.execute("UPDATE users SET leadID=?",
                             [leadID])
                g.db.commit()
                flash("Bug Time: %s" %en.times['B'])
                flash("Setup Time: %s" %en.times['S'])
                flash("Test Time: %s" %en.times['T'])
                flash("Session Length: %s" %en.session_length)
                en.export_xml(app.config['UPLOADED_FILE_DEST'], "%s.xml" %title)
            except Exception as e:
                error_list.append("ERROR parsing out data from note %s. Exception: [%s]" %(title, e))
    return render_template('main.html',
                            notebooks=notebooks, 
                            error=error,
                            authorized_users=authorized_users,
                            lead=lead['id']) 

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """used to administrate the users of the system"""
    if request.method == 'GET':
        # SELECT ALL USERS, ADMIN_USERS, AND LEAD ID
        cur = g.db.execute("select username, first_name, last_name, authorized, isadmin, leadID from users WHERE username !=?",
                           [session.get('username')])
        users = [dict(username=row[0],
                      first_name=row[1],
                      last_name=row[2],
                      authorized=row[3],
                      isadmin=row[4],
                      leadID=row[5]) for row in cur.fetchall()]
        # GET LEAD FIRST / LAST BASED ON leadID
        for user in users:
            lead = get_lead(user['username'])
            user['lead_first'] = lead['first_name']
            user['lead_last'] = lead['last_name']
        return render_template('admin.html', users=users)
    elif request.method == 'POST':
        users = request.form.getlist('user')
        action = request.form['action']
        for user in users:
            if action == 'delete':
                g.db.execute('DELETE FROM users WHERE username=?',
                             [user])
            elif action == 'admin':
                g.db.execute('UPDATE users SET isadmin=1 WHERE username=?',
                               [user])
            elif action == 'noadmin':
                g.db.execute('UPDATE users SET isadmin=0 WHERE username=?',
                             [user])
            elif action == 'auth':
                g.db.execute('UPDATE users SET identifier=Null, authorized=0 where username=?',
                             [user])
            elif action == 'pwd':
                g.db.execute("UPDATE users SET password='justastring' where username=?",
                             [user])
        g.db.commit()
        return redirect(url_for('admin'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'GET':
        authorized_users = get_authorized_users(session.get('username'))
        lead = get_lead(session.get('username'))
        # GET THIS USERS LEAD ID        #cur = g.db.execute('SELECT leadID FROM users where username=?',
        #                   [session.get('username')])
        #row = cur.fetchall()
        #leadID = row[0]
        return render_template('settings.html', authorized_users = authorized_users, lead=lead['id'])   
    elif request.method== 'POST':
        # UPDATE USER INFO WITH: ALL VALUES FROM THE FORM
        leadID = request.form['lead'] if request.form['lead'] != 'None' else 'Null'
        sql_str = "UPDATE users SET first_name=?, last_name=?, password=?"
        if request.form['lead'] == 'None':
            sql_str +=  ", leadID=NULL"
        else:
            sql_str += ", leadID={}".format(request.form['lead']) 
        if 'auth' in request.form:
            sql_str += ", authorized=0, identifier=Null"
        sql_str += " WHERE username=?"
        g.db.execute(sql_str, 
                     [request.form['first_name'],
                      request.form['last_name'],
                      request.form['password'],
                      session.get('username')])
        g.db.commit()
        authorized_users = get_authorized_users(session.get('username'))
        flash('Settings Updated Successfully')
        return redirect(url_for('settings', lead=leadID))
                 
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        cur = g.db.execute("SELECT username, password, first_name, last_name " \
                           "FROM users WHERE username = ?", 
                     [request.form['username']])
        user = [dict(username=row[0],
                     password=row[1], 
                     first_name=row[2],
                     last_name=row[3]) for row in cur.fetchall()]
        if len(user) <= 0:
            error = 'Invalid username'
        elif request.form['password'] != user[0]['password']:
            error = 'Invalid password' 
        else:
            session['logged_in'] = True
            session['username'] = request.form['username']
            session['first_name'] = user[0]['first_name']
            session['last_name'] = user[0]['last_name']
            # GET SHARD AND IDENTIFIER IF THEY EXIST USING THE USERID AS THE KEY
            cur = g.db.execute("SELECT identifier, shard_id FROM users WHERE username=?",
                               [session.get('username')])
            auth = [dict(identifier=row[0],
                         shard_id=row[1]) for row in cur.fetchall()]
            # CHECK IF THIS HAS BEEN SET YET
            if len(auth) > 0:
                session['identifier'] = auth[0]['identifier']
                session['shardId'] = auth[0]['shard_id']
            # GET ADMIN STATUS
            cur = g.db.execute("select isadmin from users where username = ?",
                               [session.get('username')])
            row = cur.fetchall()
            if row[0][0] > 0:
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
    authorized_users = get_authorized_users()
    if request.method == 'POST':
        cur = g.db.execute("select username from users where username=?",
                           [request.form['username']])
        username = [dict(username=row[0]) for row in cur.fetchall()]
        if len(username) > 0:
            error = 'Username already exists'
        elif len(request.form['password']) <= 0:
            error = 'Password cannot be blank'
        else:
            if request.form['lead'] == 'None':
                lead = None
            else:
                lead = request.form['lead']
            g.db.execute('insert into users (username, password, first_name, last_name, leadID) values (?, ?, ?, ?, ?)', 
                 [request.form['username'], 
                  request.form['password'],
                  request.form['first_name'],
                  request.form['last_name'],
                  lead])
            g.db.commit()
            flash("New User was successfully registered")
            session['logged_in'] = True
            session['first_name'] = request.form['first_name']
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

    client = get_oauth_client()

    # Make the request for the temporary credentials (Request Token)
    callback_ip = "%s:%d" %(app.config.get('IP'), app.config.get('PORT'))
    callback_url = 'http://%s%s' % (callback_ip, url_for('auth_finish'))
    request_url = '%s?oauth_callback=%s' % (EN_REQUEST_TOKEN_URL,
        urllib.quote(callback_url, safe=":/"))

    resp, content = client.request(request_url, 'GET')

    if resp['status'] != '200':
        raise Exception('Invalid response %s.' % resp['status'])

    request_token = dict(urlparse.parse_qsl(content))

    # Save the request token information for later
    session['oauth_token'] = request_token['oauth_token']
    session['oauth_token_secret'] = request_token['oauth_token_secret']

    # Redirect the user to the Evernote authorization URL
    return redirect('%s?oauth_token=%s' % (EN_AUTHORIZE_URL,
        urllib.quote(session['oauth_token'])))
   
@app.route('/authComplete')
def auth_finish():
    """After the user has authorized this application on Evernote's website,
    they will be redirected back to this URL to finish the process."""

    oauth_verifier = request.args.get('oauth_verifier', '')

    token = oauth.Token(session['oauth_token'], 
                        session['oauth_token_secret'])
    token.set_verifier(oauth_verifier)

    client = get_oauth_client()
    client = get_oauth_client(token)

    # Retrieve the token credentials (Access Token) from Evernote
    resp, content = client.request(EN_ACCESS_TOKEN_URL, 'POST')

    if resp['status'] != '200':
        raise Exception('Invalid response %s.' % resp['status'])

    access_token = dict(urlparse.parse_qsl(content))
    authToken = access_token['oauth_token']

    userStore = get_userstore()
    user = userStore.getUser(authToken)

    # Save the users information to so we can make requests later
    session['shardId'] = user.shardId
    session['identifier'] = authToken
    
    # INSERT THE SESSION AND LINK TO THE USERID
    g.db.execute("UPDATE users SET identifier=?, shard_id=?, authorized=? WHERE username=?", 
                 [session.get('identifier'), 
                  session.get('shardId'),
                  1, 
                  session.get('username')])
    g.db.commit()
    flash("Evernote Test Session Authorized!!")
    return redirect(url_for('index'))

@app.route('/createTemplate')
def new_note(content=None, guid=None, title=None, authToken = None):
    """Create a new note template from a local file, or the content passed in"""
    if content is None:
        # READ IN THE STRINGBODY
        with open('mobile testing.enex', 'r') as f:
            content = f.read()
    if title is None:
        title='Mobile Testing'
    # GET THE NOTESTORE
    if authToken is None:
        authToken = session['identifier']
    noteStore = get_notestore()
    template_note = Types.Note()
    template_note.title = title
    template_note.content = content
    try:
        if guid is None:
            noteStore.createNote(authToken, template_note)
        else:
            template_note.guid = guid
            noteStore.updateNote(authToken, template_note)
    except Errors.EDAMUserException as edue:
        return "EDAMUserException: {}".format(edue)
    except Errors.EDAMNotFoundException as edue:
        return "EDAMNNotFoundException: Invalid parent notebook GUID"
    return 'Uploaded Template successfully'

@app.route('/notes/content', methods=['POST'])
def note_content():
    """ Get the thumbnail representation of the notes posted"""
    error = None
    if request.method == 'POST':
        notes = request.form.getlist('note')
        '''<img src="https://sandbox.evernote.com/shard/{{session.shardId}}/thm/note/{{note.guid}}?auth={{session.identifier}}&size=150">'''
        return render_template('notedetails.html', 
                               notes=notes)

@app.route('/notebook/<notename>/<guid>')
def list_notes(notename,guid):
    index = int(index)
    authToken = session['identifier']
    noteStore = get_notestore()
    nb_filter = NoteStore.NoteFilter()
    nb_filter.ascending = True
    nb_spec = NoteStore.NotesMetadataResultSpec(includeTitle=True, 
                                                includeContentLength=True, 
                                                includeNotebookGuid=True, 
                                                includeTagGuids=True, 
                                                includeAttributes=True,
                                                includeLargestResourceMime=True,
                                                includeLargestResourceSize=True)
    nb_filter.notebookGuid = session['notebook_guids'][index]
    #cnt = noteStore.findNoteCounts(authToken, nb_filter, withTrash=False)
    notes = noteStore.findNotesMetadata(authToken, nb_filter, 0, 10, nb_spec).notes
    session['notes_guids'] = []
    note_str = "<ul>"
    for x in range(0, len(notes)):
        note_str += "<li><a href='/note/{1}'>{0}</a></li>".format(notes[x].title, x)
        session['notes_guids'].append(notes[x].guid)
        
    return "{}</ul>".format(note_str)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method=='POST':
        upload_file = request.files['file']
        if upload_file and allowed_file(upload_file.filename):
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
            #upload_file.save(os.path.join(app.config['UPLOADED_FILE_DEST'], filename))
        return redirect(url_for('index'))
    else:
        return render_template('upload.html') 

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    """ 
    Creates Report view of all uploaded xml files according to month and release
    """
    # THIS DATA PULLED FROM FILE STRUCTURE
    import os
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
    return render_template('reports/report_view.html', xml_list=xml_list)    
    
if __name__ == '__main__':
    app.secret_key = APP_SECRET_KEY
    import os
    if not os.path.exists(app.config.get('DATABASE')):
        init_db()
    app.run(host=app.config.get('IP'), port=app.config.get('PORT'), use_debugger=False, debug=True, use_reloader=False)
