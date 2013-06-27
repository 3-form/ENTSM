import re
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.mime.text import MIMEText
# UTILITY FUNCTION
def valid_email(email):
    """Validates the email to matching common email patterns"""
    pattern = re.compile('^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$', re.IGNORECASE)
    matches = re.findall(pattern, email)
    if len(matches) <= 0:
        return False
    else:
        return True
    
def allowed_file(filename, extensions):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in extensions
        
def send_email(en, email_server, to):
    """ Send out an email copy of the note with the issues extracted"""
    from_name='ETS@ETS.com'
    body = ''
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Exploratory Test Session on %s" %en.title.strip()
    msg['From'] = from_name
    msg['To'] = to
    issues = []
    for val in en.activity:
        if val[2].upper() =='I':
            issues.append(val[1])
    if len(issues) > 0:
        body = '<p>The following issues where identified during the test session</p>'
        body += '<ul>'
        for issue in issues:
            body +='<li>%s</li>' %issue
        body +='</ul>'
    body = body.encode("ascii", "ignore")
    en_string = en.tostring().decode("utf8")
    en_string = en_string.encode("ascii", "ignore")
    msg_body = MIMEText(body + en_string, 'html')
    msg.attach(msg_body)
    # SEND THE MAIL
    s = smtplib.SMTP(email_server)
    s.sendmail(from_name, to, msg.as_string())
    s.quit()