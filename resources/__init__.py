from flask import Flask, session, redirect, url_for, request, \
                  render_template, g, flash



app = Flask(__name__)
#app.jinja_env.add_extension('jinja2.ext.do')
app.config.from_pyfile('config.cfg')
#app.config.from_object(__name__)

#app = Flask(__name__)

import views, en_lib, rest, en_xml