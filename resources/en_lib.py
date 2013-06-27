import oauth2 as oauth

# EVERNOTE SDK LIBRARIES
import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.type.ttypes as Types
import evernote.edam.error.ttypes as Errors

# ORGINIALLY WAS THRIFT, USING EVERNOTE LIBRARIES INSTEAD
from evernote.api.client import TBinaryProtocol
from evernote.api.client import THttpClient

from resources import app

# GLOBAL SETTINGS
#from resources import EN_CONSUMER_KEY, EN_CONSUMER_SECRET, EN_USERSTORE_URIBASE, EN_NOTESTORE_URIBASE

def get_notebooks(auth_token, shard_id, guid_list=None):
    """ Creates a list of notebooks and notes metadata"""
    noteStore = get_notestore(shard_id)
    if guid_list is not None:
        notebooks = []
        for guid in guid_list:
            notebooks.append(noteStore.getNotebook(auth_token, guid))
    else:
        notebooks = noteStore.listNotebooks(auth_token)
    notebook_list = []
    for notebook in notebooks:
        notebook_dict = {'name':notebook.name, 'guid':notebook.guid}
        notebook_dict['notes'] = get_note_metadata(auth_token, shard_id, notebook_dict['guid'])
        # THIS SHOULD BE RENAMED TO shardId not session_id, that is misleading 
        notebook_dict['session_id'] = shard_id
        notebook_list.append(notebook_dict) 
    return notebook_list

def get_notebook_list(auth_token, shard_id):
    """ Creates a list of notebook title/guids"""
    noteStore = get_notestore(shard_id)    
    notebooks = noteStore.listNotebooks(auth_token)
    notebook_list = []
    for notebook in notebooks:
        notebook_list.append({'name':notebook.name, 'guid':notebook.guid})
    return notebook_list

def get_notestore(shard_id):
    """Return an instance of the Evernote NoteStore. Assumes that 'shardId' is
    stored in the current session."""
    noteStoreUri = app.config['EN_NOTESTORE_URIBASE'] + shard_id
    noteStoreHttpClient = THttpClient.THttpClient(noteStoreUri)
    noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
    noteStore = NoteStore.Client(noteStoreProtocol)
    return noteStore

def get_note(auth_token, shard_id, guid):
    """Takes the guid of a note and returns the content"""
    noteStore = get_notestore(shard_id)
    note = noteStore.getNote(auth_token, 
                             guid, 
                             withContent=True, 
                             withResourcesData=False, 
                             withResourcesRecognition=False, 
                             withResourcesAlternateData=False)
    return note.content

def get_note_metadata(auth_token, shard_id, guid):
    """ Finds all the notes metadata"""
    noteStore = get_notestore(shard_id)
    nb_filter = NoteStore.NoteFilter()
    nb_filter.ascending = True
    nb_spec = NoteStore.NotesMetadataResultSpec(includeTitle=True,
                                                #includeContentLength=True,
                                                includeNotebookGuid=True,) 
                                                #includeTagGuids=True, 
                                                #includeAttributes=True,
                                                #includeLargestResourceMime=True,
                                                #includeLargestResourceSize=True)
    nb_filter.notebookGuid = guid
    note_list = noteStore.findNotesMetadata(auth_token, nb_filter, 0, 100, nb_spec)
    if len(note_list.notes) != note_list.totalNotes:
        note_list.append(noteStore.findNotesMetadata(auth_token, 
                                                     nb_filter, 
                                                     len(note_list.notes), 
                                                     100, 
                                                     nb_spec))
    return note_list.notes

def get_oauth_client(token=None):
    """Return an instance of the OAuth client."""
    consumer = oauth.Consumer(app.config['EN_CONSUMER_KEY'], app.config['EN_CONSUMER_SECRET'])
    if token:
        client = oauth.Client(consumer, token)
    else:
        client = oauth.Client(consumer)
    return client

def get_userstore():
    """Return an instance of the Evernote UserStore."""
    userStoreHttpClient = THttpClient.THttpClient(app.config['EN_USERSTORE_URIBASE'])
    userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHttpClient)
    userStore = UserStore.Client(userStoreProtocol)
    return userStore

def new_note(auth_token, shard_id, content=None, guid=None, title=None):
    """Create a new note template from a local file, or the content passed in"""
    # THIS WHOLE FUNCTION PROBABLY NEEDS TO GET RE-WORKED AS THERE ARE EVERNOTE CALLS IN THE FUNCTION
    # INSTEAD IT SHOULD JUST PUT ALL THIS INTO THE EN_LIB AND THIS VIEW CALLS THAT FUCNTION, 
    # SPECIALLy SINCE IT DOESN'T RETURN A TEMPLATE
    if content is None:
        # READ IN THE STRINGBODY
        with open('mobile testing.enex', 'r') as f:
            content = f.read()
    if title is None:
        title='Mobile Testing'
    noteStore = get_notestore(shard_id)
    template_note = Types.Note()
    template_note.title = title
    template_note.content = content
    try:
        if guid is None:
            noteStore.createNote(auth_token, template_note)
        else:
            template_note.guid = guid
            noteStore.updateNote(auth_token, template_note)
    except Errors.EDAMUserException as edue:
        return "EDAMUserException: {}".format(edue)
    except Errors.EDAMNotFoundException as edue:
        return "EDAMNNotFoundException: Invalid parent notebook GUID"
    return 'Uploaded Template successfully'

def update_note(auth_token, shard_id, content, guid, title):
    """Create a new note template from a local file, or the content passed in"""
    # GET THE NOTESTORE
    noteStore = get_notestore(shard_id)
    template_note = Types.Note()
    template_note.title = title
    template_note.content = content
    template_note.guid = guid
    try:
        noteStore.updateNote(auth_token, template_note)
    except Errors.EDAMUserException as edue:
        return "EDAMUserException: {}".format(edue)
    except Errors.EDAMNotFoundException as edue:
        return "EDAMNNotFoundException: Invalid parent notebook GUID"
    return 'Note %s Successfully parsed and updated' %title