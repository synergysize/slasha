import os
import datetime
from flask import Flask, request, render_template, redirect, url_for, session
import json

# Initialize Flask app
app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.urandom(24)  # For session management

# Mock NDB models for local development
class Model:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.key = None
    
    def put(self):
        # In a real app, this would save to the database
        # For now, we'll just print for debugging
        print(f"Saving {self.__class__.__name__}: {self.__dict__}")
        return self

class StringProperty:
    def __init__(self):
        pass

class IntegerProperty:
    def __init__(self):
        pass

class TextProperty:
    def __init__(self):
        pass

class DateTimeProperty:
    def __init__(self, auto_now=False):
        self.auto_now = auto_now

# Create a simple in-memory database
class MemoryDB:
    def __init__(self):
        self.savedata = []
        self.results = []
        self.levels = []
    
    def query(self, model_class, **filters):
        if model_class.__name__ == 'Savedata':
            return [item for item in self.savedata if self._match_filters(item, filters)]
        elif model_class.__name__ == 'Result':
            return [item for item in self.results if self._match_filters(item, filters)]
        elif model_class.__name__ == 'Level':
            return [item for item in self.levels if self._match_filters(item, filters)]
        return []
    
    def _match_filters(self, item, filters):
        for key, value in filters.items():
            if not hasattr(item, key) or getattr(item, key) != value:
                return False
        return True
    
    def save(self, item):
        if item.__class__.__name__ == 'Savedata':
            # Remove existing items with same player and campaign
            self.savedata = [s for s in self.savedata if not (s.player == item.player and s.campaign == item.campaign)]
            self.savedata.append(item)
        elif item.__class__.__name__ == 'Result':
            self.results.append(item)
        elif item.__class__.__name__ == 'Level':
            # Remove existing level with same campaign and counter
            self.levels = [l for l in self.levels if not (l.campaign == item.campaign and l.counter == item.counter)]
            self.levels.append(item)
        return item
    
    def delete(self, item):
        if item.__class__.__name__ == 'Savedata':
            self.savedata.remove(item)
        elif item.__class__.__name__ == 'Result':
            self.results.remove(item)
        elif item.__class__.__name__ == 'Level':
            self.levels.remove(item)

# Create global database instance
db = MemoryDB()

# Context manager for database operations (dummy for compatibility)
class ndb_context:
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

# Firebase Authentication setup for local development
# Uncomment and configure this if you want to use Firebase auth
"""
try:
    cred = credentials.Certificate('path/to/service-account.json')
    firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"Firebase initialization error: {e}")
"""

# Our save data models using our mock classes
class Savedata(Model):
    player = StringProperty()
    nick = StringProperty()
    campaign = StringProperty()
    counter = IntegerProperty()
    
    def put(self):
        return db.save(self)

class Result(Model):
    player = StringProperty()
    nick = StringProperty()
    campaign = StringProperty()
    counter = IntegerProperty()
    win = IntegerProperty()
    friendly_losses = IntegerProperty()
    enemy_losses = IntegerProperty()
    time = IntegerProperty()
    realtime = IntegerProperty()
    worldtime = DateTimeProperty(auto_now=True)
    
    def put(self):
        self.worldtime = datetime.datetime.now()
        return db.save(self)

class Level(Model):
    text = TextProperty()
    counter = IntegerProperty()
    campaign = StringProperty()
    owner = StringProperty()
    nick = StringProperty()
    date = DateTimeProperty(auto_now=True)
    
    def put(self):
        self.date = datetime.datetime.now()
        return db.save(self)
    
    @staticmethod
    def query():
        return LevelQuery()

class LevelQuery:
    def filter(self, *args, **kwargs):
        self.filters = kwargs
        return self
    
    def fetch(self, limit=None):
        return db.query(Level, **self.filters)

# Mock user authentication for local development
def get_current_user():
    if 'user_id' in session and 'nickname' in session:
        return {
            'user_id': session['user_id'],
            'nickname': session['nickname']
        }
    return None

# Routes
@app.route('/', methods=['GET', 'POST'])
def main_page():
    user = get_current_user()
    if user:
        return redirect(url_for('startscreen'))
    else:
        # For local development, provide a simple login form
        if request.method == 'POST':
            user_id = request.form.get('user_id', 'test_user')
            nickname = request.form.get('nickname', 'Test User')
            session['user_id'] = user_id
            session['nickname'] = nickname
            return redirect(url_for('startscreen'))
        
        return '''
        <style type="text/css">
        #container { position:absolute; top:50%; width:100%; height:10em; margin-top:-5em }
        </style>
        <center><div id="container">
            <h2>Welcome! Please sign in to continue:</h2>
            <form method="post">
                <label>User ID: <input type="text" name="user_id" value="test_user"></label><br>
                <label>Nickname: <input type="text" name="nickname" value="Test User"></label><br><br>
                <input type="submit" value="Sign In">
            </form>
        </div></center>
        '''

@app.route('/devguide', methods=['GET', 'POST'])
def devguide():
    with open('devguide.html', 'r') as file:
        return file.read()

@app.route('/example', methods=['GET', 'POST'])
def example():
    with open('tutorial.txt', 'r') as file:
        return file.read(), 200, {'Content-Type': 'text/plain'}

def load_campaign(pkg, user):
    lines = pkg.replace("\r","").split("\n")
    name = lines[0][lines[0].find(": ") + 2:]
    n = 1
    breaks = []
    while n < len(lines):
        if "--------" in lines[n]: 
            breaks.append(n)
        n += 1
    breaks.append(len(lines))
    
    for b in range(len(breaks) - 1):
        level = Level(
            text='\n'.join(lines[breaks[b] + 1:breaks[b + 1]]),
            campaign=name,
            counter=b + 1,
            owner=user['user_id'],
            nick=user['nickname']
        )
        level.put()

def create_level(text, campaign, counter, owner, nick):
    level = Level(
        text=text,
        campaign=campaign,
        counter=counter,
        owner=owner,
        nick=nick
    )
    return level

def package_campaign(campaign):
    level_entities = db.query(Level, campaign=campaign, counter=1)
    
    if not level_entities:
        return ""
        
    s = "Name: " + campaign + "\n"
    s += "Created by: " + level_entities[0].nick + "\n"
    s += "Date: " + str(level_entities[0].date) + "\n"
    
    n = 1
    while level_entities:
        s += "-----------------------\n"
        s += level_entities[0].text + "\n"
        n += 1
        level_entities = db.query(Level, campaign=campaign, counter=n)
        
    return s

@app.route('/startscreen', methods=['GET', 'POST'])
def startscreen():
    user = get_current_user()
    
    # Redirect to login if not authenticated
    if not user:
        return redirect(url_for('main_page'))
    
    # Process uploaded campaigns from data directory
    if os.path.exists('data'):
        for d in os.listdir('data'):
            with open(os.path.join('data', d), 'r') as file:
                textcmp = file.read()
                name = textcmp[textcmp.find(": ") + 2:textcmp.find("\n")]
                
                # Check if campaign exists
                campaign_levels = db.query(Level, campaign=name)
                campaign_exists = len(campaign_levels) > 0
                
                if not campaign_exists:
                    load_campaign(textcmp, user)
    
    # Upload campaign from textbox if provided
    textcmp = request.form.get('campaign', '')
    if "---------" in textcmp:
        name = textcmp[textcmp.find(": ") + 2:textcmp.find("\n")-1]
        
        campaign_levels = db.query(Level, campaign=name)
        campaign_exists = len(campaign_levels) > 0
        
        if not campaign_exists:
            load_campaign(textcmp, user)
        else:
            return render_template('template.html', 
                                  init_vars="alert('Campaign already exists!');",
                                  js_file="javascript/startscreen.js",
                                  level_data="",
                                  campaign_data="")
    
    # Redirect to devguide if requested
    if textcmp == "devguide":
        return redirect(url_for('devguide'))
    
    # Load save data
    saves = []
    campaigns = {}
    campaign_status = {}
    
    # Get all levels
    all_levels = db.levels
    for level in all_levels:
        if not hasattr(level, 'campaign'):
            continue
        if level.campaign not in campaigns:
            campaigns[level.campaign] = 0
        if campaigns[level.campaign] < level.counter:
            campaigns[level.campaign] = level.counter
    
    # Get existing saves for the current user
    existing_saves = db.query(Savedata, player=user['user_id'])
    for save in existing_saves:
        if not hasattr(save, 'campaign'):
            continue
        save_campaign = [s.get('campaign') for s in saves if 'campaign' in s]
        if save.campaign not in save_campaign and save.campaign in campaigns:
            campaign_status[save.campaign] = save.counter
            saves.append({
                'player': save.player,
                'nick': save.nick,
                'campaign': save.campaign,
                'counter': save.counter,
                'levels': campaigns[save.campaign]
            })
    
    # Add campaigns not in saves
    for c in campaigns.keys():
        if c not in campaign_status:
            saves.append({
                'player': user['user_id'],
                'nick': user['nickname'],
                'campaign': c,
                'counter': 1,
                'levels': campaigns[c]
            })
    
    # Prepare JavaScript init variables
    init_vars = "options = [];\n"
    for s in saves:
        init_vars += f"options.push(['{s['campaign']}', {s['counter']}, {s['levels']}]);\n  "
    
    init_vars += "options.push(['Create new',0,0]);\n  "
    init_vars += "options.push(['Paste campaign file',0,0]);"
    init_vars += "options.push(['View level development guide',0,0]);"
    
    return render_template('template.html',
                          init_vars=init_vars,
                          js_file="javascript/startscreen.js",
                          level_data="",
                          campaign_data="")

@app.route('/play', methods=['POST'])
def game():
    user = get_current_user()
    if not user:
        return redirect(url_for('main_page'))
    
    info = request.form.get('info', '')
    infoarray = info.split(' ')
    lastscore = request.form.get('score', '')
    scorearray = lastscore.split(' ')
    
    campaign = infoarray[0]
    counter = int(infoarray[1])
    
    rminloss = [99999, "null"]
    rmaxratio = [0, "null"]
    rmintime = [99999, "null"]
    rminrt = [99999, "null"]
    
    # Handle save game state
    # Delete inferior saves
    existing_saves = db.query(Savedata, player=user['user_id'], campaign=campaign)
    for save in existing_saves:
        if save.counter < counter:
            db.delete(Savedata, save)
    
    # Create a new save
    save = Savedata(
        player=user['user_id'],
        nick=user['nickname'],
        campaign=campaign,
        counter=counter
    )
    save.put()
    
    # Record score if provided
    if len(scorearray) >= 5:
        score = Result(
            player=user['user_id'],
            nick=user['nickname'],
            campaign=campaign,
            win=int(scorearray[0]),
            counter=int(counter) if int(scorearray[0]) != 1 else int(counter - 1),
            friendly_losses=int(scorearray[1]),
            enemy_losses=int(scorearray[2]),
            time=int(scorearray[3]),
            realtime=int(scorearray[4])
        )
        score.put()
    
    message = request.form.get('message', '')
    
    # Check if user can edit the level
    wecanedit = 0
    if len(infoarray) > 2:
        current_levels = db.query(Level, campaign=campaign, counter=counter)
        
        if current_levels and current_levels[0].owner == user['user_id']:
            wecanedit = 1
        elif not current_levels:
            # Check if adding to existing campaign
            same_campaign = db.query(Level, campaign=campaign)
            
            if same_campaign and same_campaign[0].owner == user['user_id']:
                wecanedit = 1  # Adding to a campaign
            elif not same_campaign:
                wecanedit = 1  # Creating a new campaign
    
    # Handle level editing if allowed
    if wecanedit == 1:
        if len(infoarray) > 2 and infoarray[2] == 'save':
            data = request.form.get('data', '').replace('\r', '')
            
            # Delete existing level
            current_levels = db.query(Level, campaign=campaign, counter=counter)
            for level in current_levels:
                db.delete(Level, level)
            
            # Create and save the updated level
            level = Level(
                text=data,
                campaign=campaign,
                counter=counter,
                owner=user['user_id'],
                nick=user['nickname']
            )
            level.put()
        
        elif len(infoarray) > 2 and infoarray[2] == 'delete':
            # Delete the current level
            current_levels = db.query(Level, campaign=campaign, counter=counter)
            for level in current_levels:
                db.delete(Level, level)
            
            # Shift later levels back by one
            later_levels = db.query(Level, campaign=campaign)
            later_levels = [level for level in later_levels if level.counter > counter]
            
            for level in later_levels:
                level_data = {
                    'text': level.text,
                    'campaign': level.campaign,
                    'counter': level.counter - 1,
                    'owner': level.owner,
                    'nick': level.nick
                }
                db.delete(Level, level)
                
                new_level = Level(**level_data)
                new_level.put()
            
            # Adjust player progress
            if counter > 1:
                counter -= 1
            
            # Update savepoints
            existing_saves = db.query(Savedata, player=user['user_id'], campaign=campaign)
            for save in existing_saves:
                save_counter = save.counter
                db.delete(Savedata, save)
                
                if save_counter > counter:
                    save_counter -= 1
                
                if save_counter > 0:
                    new_save = Savedata(
                        player=save.player,
                        nick=save.nick,
                        campaign=save.campaign,
                        counter=save_counter
                    )
                    new_save.put()
    
    # Get high scores for the level
    results = db.query(Result, campaign=campaign, counter=counter, win=1)
    
    for result in results:
        if result.friendly_losses < rminloss[0]:
            rminloss = [result.friendly_losses, result.nick]
        
        ratio = result.enemy_losses / (result.friendly_losses + 0.01)
        if ratio > rmaxratio[0]:
            rmaxratio = [ratio, result.nick]
        
        if result.time < rmintime[0]:
            rmintime = [result.time, result.nick]
        
        if result.realtime * 0.001 < rminrt[0]:
            rminrt = [result.realtime * 0.001, result.nick]
    
    # Get level data
    current_level = db.query(Level, campaign=campaign, counter=counter)
    
    if not current_level:
        return redirect(url_for('startscreen'))
    
    # Prepare JavaScript initialization variables
    init_vars = f'minloss = [{rminloss[0]}, \'{rminloss[1]}\'];\n'
    init_vars += f'maxratio = [{rmaxratio[0]}, \'{rmaxratio[1]}\'];\n'
    init_vars += f'mintime = [{rmintime[0]}, \'{rmintime[1]}\'];\n'
    init_vars += f'minrt = [{rminrt[0]}, \'{rminrt[1]}\'];\n'
    
    # If we lost, go straight to time = 0
    if len(scorearray) < 5 or scorearray[0] == "1":
        init_vars += "start_time = -1;\n"
    else:
        init_vars += "start_time = 0;\n"
    
    init_vars += f"campaign = '{campaign}';\ncounter = {counter};\n"
    
    # Set edit status
    if current_level[0].owner == user['user_id']:
        init_vars += "edit_status = 'CAN';"
    else:
        init_vars += "edit_status = 'CANNOT';"
    
    # Package campaign data for owner
    campaign_data = ""
    if user['user_id'] == current_level[0].owner:
        campaign_data = package_campaign(campaign)
    
    level_data = current_level[0].text
    
    return render_template('template.html',
                          init_vars=init_vars,
                          js_file="javascript/main.js",
                          level_data=level_data,
                          campaign_data=campaign_data)

@app.route('/edit', methods=['POST'])
def editor():
    user = get_current_user()
    if not user:
        return redirect(url_for('main_page'))
    
    message = request.form.get('message', '')
    messagearray = message.split(' ')
    
    if len(messagearray) < 3:
        return redirect(url_for('startscreen'))
    
    campaign = messagearray[0]
    counter = int(messagearray[1])
    
    # Check if user can edit the level
    current_levels = db.query(Level, campaign=campaign, counter=counter)
    
    wecanedit = 0
    if current_levels and current_levels[0].owner == user['user_id']:
        wecanedit = 1
    elif not current_levels:
        # Check if adding to existing campaign
        same_campaign = db.query(Level, campaign=campaign)
        
        if same_campaign and same_campaign[0].owner == user['user_id']:
            wecanedit = 1  # Adding to a campaign
        elif not same_campaign:
            wecanedit = 1  # Creating a new campaign
    
    # Handle level editing if allowed
    if wecanedit == 1 and messagearray[2] == 'add':
        try:
            with open('default_level.txt', 'r') as file:
                default_data = file.read()
        except:
            default_data = "No default level template found."
        
        # Shift all levels after this one
        later_levels = db.query(Level, campaign=campaign)
        later_levels = [level for level in later_levels if level.counter >= counter]
        
        for level in later_levels:
            level_data = {
                'text': level.text,
                'campaign': level.campaign,
                'counter': level.counter + 1,
                'owner': level.owner,
                'nick': level.nick
            }
            db.delete(Level, level)
            
            new_level = Level(**level_data)
            new_level.put()
        
        # Update savepoints
        existing_saves = db.query(Savedata, player=user['user_id'], campaign=campaign)
        for save in existing_saves:
            save_counter = save.counter
            db.delete(Savedata, save)
            
            if save_counter >= counter:
                save_counter += 1
            
            new_save = Savedata(
                player=save.player,
                nick=save.nick,
                campaign=save.campaign,
                counter=save_counter
            )
            new_save.put()
        
        # Create the new level
        if counter == 1:
            # Creating a new campaign with default level
            level = Level(
                text=default_data,
                campaign=campaign,
                counter=counter,
                owner=user['user_id'],
                nick=user['nickname']
            )
            level.put()
        else:
            # Copy classes from previous level
            prev_levels = db.query(Level, campaign=campaign, counter=(counter - 1))
            
            if prev_levels:
                # This is a simplified version
                level = Level(
                    text=default_data,
                    campaign=campaign,
                    counter=counter,
                    owner=user['user_id'],
                    nick=user['nickname']
                )
                level.put()
    
    # Get level data for editing
    current_level = db.query(Level, campaign=campaign, counter=counter)
    
    if not current_level:
        return redirect(url_for('startscreen'))
    
    # Prepare JavaScript initialization variables
    init_vars = f"var campaign = '{campaign}';\nvar counter = {counter};\n"
    init_vars += "var edit_status = 2;"
    
    level_data = current_level[0].text
    
    # Package campaign data for owner
    campaign_data = ""
    if user['user_id'] == current_level[0].owner:
        campaign_data = package_campaign(campaign)
    
    return render_template('template.html',
                          init_vars=init_vars,
                          js_file="javascript/editor.js",
                          level_data=level_data,
                          campaign_data=campaign_data)

# Create a proper Flask template renderer
@app.template_filter('render_template_string')
def render_template_string_filter(template_string, **context):
    return render_template_string(template_string, **context)

if __name__ == '__main__':
    # Run the application on localhost:5001
    app.run(host='0.0.0.0', port=5001, debug=True)