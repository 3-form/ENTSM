from datetime import datetime as dt
from lxml import etree
from StringIO import StringIO
import os

class ENXML_MISSING_ID(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class ENXML():
    '''
    Class object that will handle all the getting/setting of the various 
    parts as well as the data of the content tree
    '''
    def __init__(self, content_string=None, doctype=None, format_style="%I:%M %p"):
        '''
        Can take a string as an optional argument as well as the Doc 
        type string if the need to write back the note is needed
        @param content_string (string) - The content string from an 
        evernote note.contnet
        @param doctype (string) - the Doctype of the Evernote note
        '''
        self.content_string = content_string
        self.format_style = format_style
        self.doctype = doctype
        if self.content_string is not None:
            self.parse_note_content(self.content_string)
        self.id_error = "Missing {} id from note, bad template"

    def flatten(self, element):
        """
        Flattens a list of ul/li and returns an array of text
        """
        tx_str = ''
        tx_list = element.xpath(".//text()")
        for tx in tx_list:
            if len(tx.strip()) > 0:
                tx_str += '\n' + tx.strip()
        return tx_str
    
    def parse_note_content(self, content_string):
        '''
        Takes a string, makes it a file like object and parses Also 
        sets the tree and root objects
        @parm content_string (string) - The content string to parse
        
        '''
        f = StringIO(content_string)
        try:
            self.tree = etree.parse(f)
            self.root = self.tree.getroot()
        except etree.XMLSyntaxError:
            raise

    def break_out_tables(self):
        '''
        parses the xml root element and finds all the parts of the xml doc
        assigns each part to a part of the class object
        '''
        # TESTERS
        try:
            error = 'title'
            title = self.root.xpath(".//td[contains(@style, 'id: title')]")[0]
            error = 'flatten title'
            self.title = self.flatten(title)
            error = 'testers'
            testers = self.root.xpath(".//td[contains(@style, 'id: testers')]")[0]
            error = 'flatten testers'
            self.testers = self.flatten(testers)       
            # SESSION DATA
            error = 'month'
            month = self.root.xpath(".//td[contains(@style, 'id: month')]")[0]
            if month.text is not None:
                self.month =  month.text.strip()
            else:
                self.month=''
            error = 'build'
            build = self.root.xpath(".//td[contains(@style, 'id: build')]")[0]
            if build.text is not None:
                self.build = ((build.text.strip()).replace(' ', '_')).lower()
            else:
                self.build = ''
            error = 'team'
            team = self.root.xpath(".//td[contains(@style, 'id: team')]")[0]
            if team.text is not None:
                self.team = ((team.text.strip()).replace(' ', '_')).lower()
            else:
                self.team = ''
            # ACCEPTANCE CRITERIA
            error = 'acceptance'
            acceptance = self.root.xpath(".//td[contains(@style, 'id: acceptance')]")[0]
            error = 'flatten acceptance'
            self.acceptance = self.flatten(acceptance)
        
            # REGRESSION
            error = 'regression'
            regression = self.root.xpath(".//td[contains(@style, 'id: regression')]")[0]
            error = 'flatten regression'
            self.regression = self.flatten(regression)
        
            # GET LIST OF BUGS
            error = 'parse bugs'
            self.bugs = self.parse_bugs(self.root.xpath(".//table[contains(@style, 'id: bugs')]")[0])
        
            # DEEP TABLES THAT NEED MORE WORK TO EXTRACT
            error = 'parse activity'
            self.activity = self.parse_activty(self.root.xpath(".//table[contains(@style, 'id: activity')]")[0])
            # GET THE START AND END OF THE SESSION
            error = 'parse start stop'
            self.start_time, self.end_time = self.parse_start_stop(self.activity, self.format_style)
            # FROM ACTIVITY PARSE OUT THE SESSION LENGTH
            error = 'parse length or time'
            self.session_length, self.session_type = self.parse_session_length(self.activity, self.start_time, self.end_time, self.format_style)
            self.set_session_type(self.session_type, self.session_length)
            # GET THE S/B/T TIME
            self.times = {'S':0, 'B':0, 'T':0}
            for key in self.times.keys():
                error = 'parse activity time'
                time_list_start, time_list_stop = self.parse_activity_time(self.activity, key, self.format_style)
                self.times[key] = self.get_time(time_list_start, time_list_stop, self.session_length)
                self.set_time(key, self.times[key])
            # GET THE RESULTS, NOT YET USED
            error = 'results'
            self.results = self.root.xpath(".//table[contains(@style, 'id: results')]")[0]
        except IndexError as e:
            raise ENXML_MISSING_ID(self.id_error.format(error))
        
    def parse_activty(self, element=None):
        """
        parses out the activity table and creates a three element array
        @param element (Element Object) - if none will search and find 
        the element from root
        """
        if element is None:
            element = self.root.xpath(".//table[contains(@style, 'id: activities')]")[0]
        activity_list=[]
        # GET ALL THE ROWS IN THE ELEMENT
        tr_list = element.xpath(".//tr")
        # STARTING ON ROW 2 (0 INDEXED):
        for x in range(1, len(tr_list)):
            a_time=self.flatten(tr_list[x][0]).strip()
            a_work = self.flatten(tr_list[x][1]).strip()
            a_type = self.flatten(tr_list[x][2]).strip()
            if len(a_time) >0 and len(a_work) >0 and len(a_type) > 0:
                activity_list.append((a_time, a_work, a_type))
        return activity_list
    
    def parse_bugs(self, element=None):
        """
        takes an element and parses out the name, link, and title
        returns a hash array of the data
        """
        if element is None:
            element = self.root.xpath(".//table[contains(@style, 'id: bugs')]")[0]
        # BUG DATA STARTS AT ROW 2
        bug_list = []
        bug_data = element[1:]
        for bug in bug_data:
            # NUMBER AND POSSIBLY LINK IS IN THE FIRST CELL
            bug_number = bug.find(".//td[1]")
            num = bug_number.xpath("string()").strip()
            a = bug_number.find(".//a")
            if a is not None:
                a_link = a.get("href")
            else:
                a_link = None
            bug_name = bug.find(".//td[2]")
            name = bug_name.xpath("string()").strip()
            if len(name) > 0 or len(num) > 0:
                bug_list.append({'num':num, 'link':a_link, 'name':name})
        return bug_list
    
    def assign_time(self, time_type, time_value):
        """
        assigns the time types to the correct element
        """
        element = self.time.xpath(".//td[contains(@style, 'id: {}')]".format(time_type))[0]
        element.text = unicode(time_value, 'UTF-8')
        
    def parse_start_stop(self, activity, format_style):
        """ Get the start,stop time and set to self"""
        start_time = None
        end_time = None
        if len(activity) > 0:
            # GO THROUGH EACH TABLE ROW UNTIL A VALUE IS FOUND
            counter = 0
            while counter < len(activity):
                try: 
                    start_time = dt.strptime(activity[counter][0], format_style)
                    break
                except (ValueError, TypeError):
                    counter +=1
            counter = 1
            # GO THROUGH EACH TABLE ROW UNTIL THE END TIME IS FOUND
            while counter < len(activity):
                try:
                    end_time = dt.strptime(activity[0-counter][0], format_style)
                    break
                except (ValueError, TypeError):
                    counter +=1 
        return start_time, end_time
    
    def parse_session_length(self, activity, start_time, end_time, format_style):
        """ gets the session length start and end time given an array of activities table"""
        s_length = '90'
        actual_type = 'Normal'
        if len(activity) > 0:
            t_h = end_time.hour - start_time.hour
            t_m = end_time.minute - start_time.minute
            s_length = t_h * 60 + t_m
            # USE THE +/- 15 TO DETERMINE CALCULATED TIME OF SESSION
            # RETURN THE TYPE AND LENGTH
            actual_type = 'Normal'
            if ( s_length <= 45 ):
                actual_type = 'Small'
            elif( s_length > 45 and s_length <= 105 ):
                actual_type = 'Normal'
            elif( s_length > 105 ):
                actual_type = 'Large'
        return ( s_length, actual_type )
        
    def parse_activity_time(self, activity_array, activity_type, format_style):
        """parses out the percentage of time spent on activity vs session length"""
        nutural_list = ['D', 'O', 'I']
        start_time = []
        end_time = []
        start_flag = False
        end_flag = False
        for i in range( 0, len( activity_array ) ):
            #if 'type' in activity_array[i] and activity_array[i]['type'] == activity_type:
            # time = 0, text = 1, type = 2 i = row
            if activity_array[i][2] == activity_type and activity_array[i][0] is not None:
                if not start_flag:
                    start_flag = True
                    end_flag = False
                    start_time.append( dt.strptime( activity_array[i][0].replace( ',', '' ), format_style ) )
            elif activity_array[i][2] in nutural_list and activity_array[i][0] is not None:
                pass
            elif ( activity_array[i][2] != activity_type and
                  activity_array[i][2] not in nutural_list and
                  activity_array[i][0] is not None ):
                if not end_flag and ( end_flag != start_flag ):
                    end_flag = True
                    start_flag = False
                    end_time.append( dt.strptime( activity_array[i][0].replace( ',', '' ), format_style ) )
    
        if len( end_time ) < len( start_time ):
            index = len( activity_array ) - 1
            while True:
                if activity_array[index][0] is not None:
                    break
                else:
                    index -= 1
            end_time.append( dt.strptime( activity_array[index][0].replace( ',', '' ), format_style ) )
        return start_time, end_time

    def get_time(self, start_time, end_time, session_length):
        """takes an array of start and end times, and session_length and finds the percentage of time spent"""
        t_h = 0.00
        t_m = 0.00
        for i in range( 0, len( start_time ) ):
            t_h += end_time[i].hour - start_time[i].hour
            t_m += end_time[i].minute - start_time[i].minute
        total_t = t_h * 60 + t_m
        import math
        return int( math.ceil( ( float( total_t ) / float( session_length ) ) * 100 ) )

    def set_time(self, time_type, time_val):
        """ sets the time of the activity type """
        time_type = "{}_time".format(time_type.lower())
        el = self.root.xpath(".//td[contains(@style, 'id: {}')]".format(time_type))[0]
        el.text = str(time_val)
        
    def set_session_type(self, session_type, session_length):
        """ Finds the value and sets the session type and length """
        el = self.root.xpath(".//td[contains(@style, 'id: minutes')]")[0]
        el.text = "%s - %s" %(session_type, session_length)
    
    def write(self, filename):
        """Writes out the xml to file including the encoding and doc type"""
        with open(filename, 'w') as f:
            f.write(etree.tostring(self.tree, 
                                   pretty_print=True, 
                                   xml_declaration=True, 
                                   encoding="UTF-8", 
                                   doctype=self.doctype))
            
    def export_xml(self, directory, filename):
        """Exports the xml to a simpler format"""
        root = etree.Element('session')
        etree.SubElement(root, 'title').text=self.title
        etree.SubElement(root, 'month').text=self.month
        etree.SubElement(root, 'team').text=self.team
        etree.SubElement(root, 'build').text = self.build
        etree.SubElement(root, 'testers').text = self.testers
        etree.SubElement(root, 'session_type').text = self.session_type
        etree.SubElement(root, 'session_length').text = str(self.session_length)
        etree.SubElement(root, 'b_time').text=str(self.times['B'])
        etree.SubElement(root, 's_time').text=str(self.times['S'])
        etree.SubElement(root, 't_time').text=str(self.times['T'])
        for val in self.bugs:
            defect_node = etree.SubElement(root, 'defect')
            etree.SubElement(defect_node, 'defect_title').text=val['name']
            etree.SubElement(defect_node, 'defect_number').text=val['num']
            etree.SubElement(defect_node, 'defect_link').text=val['link']
        parent_dict = {
                     'O':etree.SubElement( root, 'opportunity' ),
                     'I':etree.SubElement( root, 'issue' ),
                     'T':etree.SubElement( root, 'test' ),
                     'S':etree.SubElement( root, 'setup' ),
                     'B':etree.SubElement( root, 'bug' )
                     }
        node_dict = {
                       'O':'o_node',
                       'I':'i_node',
                       'T':'t_node',
                       'S':'s_node',
                       'B':'b_node'
                       }
        inum = 0
        onum = 0
        for val in self.activity:
            if val[2] in parent_dict:
                if val[2] == 'I':
                    inum +=1
                elif val[2] == 'O':
                    onum += 1
                etree.SubElement( 
                              parent_dict[val[2]],
                              node_dict[val[2]]
                              ).text = val[1]
        counts = etree.SubElement(root, 'session_count')
        etree.SubElement(counts, 'i_count').text=str(inum)
        etree.SubElement(counts, 'o_count').text=str(onum)
        etree.SubElement(counts, 'b_count').text=str(len(self.bugs))
        tree = etree.ElementTree(root)
        # OPEN OR CREATE DIRECTORY SUB TREE BASED ON TEAM
        # THEN RELEASE (MONTH VALUE)
        # CHECK THAT DIRECTORY EXISTS, THEN TEAM THEN BUILD/MONTH/RELEASE
        full_path = os.path.join(directory, self.team, self.month)
        try:
            os.makedirs(full_path)
        except OSError:
            if os.path.exists(full_path):
                pass
            else:
                raise Exception
        with open(os.path.join(full_path, filename), 'w') as f:
            f.write(etree.tostring(tree, 
                                   pretty_print=True, 
                                   xml_declaration=True, 
                                   encoding="UTF-8", 
                                   doctype=self.doctype))
    
    def tostring(self):
        """ returns a string representation of the xml in self"""
        return etree.tostring(self.tree, 
                              pretty_print=True,
                              xml_declaration=True,
                              encoding="UTF-8",
                              doctype=self.doctype)

if __name__ == '__main__':
    with open('mobile testing.enex', 'r') as f:
            output = f.read()
    en = ENXML(output)
    en.break_out_tables()    
    print en.tostring()
    pass