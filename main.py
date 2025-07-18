import os, datetime
from flask import Flask, request, render_template_string, redirect, url_for, session
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Simple in-memory database
savedata_db = []
results_db = []
levels_db = []

# Our save data
class Savedata:
    def __init__(self, player="", nick="", campaign="", counter=0):
        self.player = player
        self.nick = nick
        self.campaign = campaign
        self.counter = counter

class Result:
    def __init__(self, player="", nick="", campaign="", counter=0, win=0, friendly_losses=0, enemy_losses=0, time=0, realtime=0):
        self.player = player
        self.nick = nick
        self.campaign = campaign
        self.counter = counter
        self.win = win
        self.friendly_losses = friendly_losses
        self.enemy_losses = enemy_losses
        self.time = time
        self.realtime = realtime
        self.worldtime = datetime.datetime.now()

class Level:
    def __init__(self, text="", counter=0, campaign="", owner="", nick=""):
        self.text = text
        self.counter = counter
        self.campaign = campaign
        self.owner = owner
        self.nick = nick
        self.date = datetime.datetime.now()

@app.route('/')
def main_page():
    if 'user_id' in session:
        return redirect('/startscreen')
    else:
        return '''
        <style type="text/css">
        #container { position:absolute; top:50%; width:100%; height:10em; margin-top:-5em }
        </style>
        <center><div id="container">
        <h1>Welcome to Slasha!</h1>
        <p>Please sign in to continue:</p>
        <form method="post" action="/login">
            <input type="text" name="username" placeholder="Username" required><br><br>
            <input type="submit" value="Login">
        </form>
        </div></center>
        '''

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    session['user_id'] = username
    session['nickname'] = username
    return redirect('/startscreen')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/devguide')
def devguide():
    try:
        return open('devguide.html').read()
    except:
        return "<h1>Dev Guide</h1><p>Development guide not found</p>"

@app.route('/example')
def example():
    try:
        return open('tutorial.txt').read()
    except:
        return "Tutorial file not found"

@app.route('/startscreen', methods=['GET', 'POST'])
def startscreen():
    if 'user_id' not in session:
        return redirect('/')
    
    user_id = session['user_id']
    nickname = session['nickname']
    
    # Handle campaign upload
    if request.method == 'POST':
        textcmp = request.form.get("campaign", "")
        if "---------" in textcmp:
            name = textcmp[textcmp.find(": ") + 2:textcmp.find("\n")]
            campaign_exists = any(level.campaign == name for level in levels_db)
            if not campaign_exists:
                load_campaign(textcmp, user_id, nickname)
            else:
                return "<script>alert('Campaign already exists!')</script>"
        
        if textcmp == "devguide":
            return redirect('/devguide')
    
    # Load campaigns and saves
    campaigns = {}
    for level in levels_db:
        if level.campaign not in campaigns or campaigns[level.campaign] < level.counter:
            campaigns[level.campaign] = level.counter
    
    saves = []
    campaign_status = {}
    
    for save in savedata_db:
        if save.player == user_id and save.campaign in campaigns:
            if save.campaign not in campaign_status:
                campaign_status[save.campaign] = save.counter
                saves.append({
                    'player': save.player,
                    'nick': save.nick,
                    'campaign': save.campaign,
                    'counter': save.counter,
                    'levels': campaigns[save.campaign]
                })
    
    for campaign, max_level in campaigns.items():
        if campaign not in campaign_status:
            saves.append({
                'player': user_id,
                'nick': nickname,
                'campaign': campaign,
                'counter': 1,
                'levels': max_level
            })
    
    # Generate JavaScript options
    init_vars = "options = [];\n"
    for s in saves:
        init_vars += f"options.push(['{s['campaign']}',{s['counter']},{s['levels']}]);\n"
    init_vars += "options.push(['Create new',0,0]);\n"
    init_vars += "options.push(['Paste campaign file',0,0]);\n"
    init_vars += "options.push(['View level development guide',0,0]);\n"
    
    template = '''
    <html>
    <head><title>Slasha - Start Screen</title></head>
    <body>
    <h1>Slasha Game</h1>
    <script>
    %s
    </script>
    <div id="campaigns">
    <h2>Available Campaigns:</h2>
    ''' % init_vars
    
    for save in saves:
        template += f"<p><a href='/play?campaign={save['campaign']}&counter={save['counter']}'>{save['campaign']} (Level {save['counter']}/{save['levels']})</a></p>"
    
    template += '''
    </div>
    <form method="post">
    <h3>Upload Campaign:</h3>
    <textarea name="campaign" rows="10" cols="50" placeholder="Paste campaign file here..."></textarea><br>
    <input type="submit" value="Upload Campaign">
    </form>
    <p><a href="/logout">Logout</a></p>
    </body>
    </html>
    '''
    
    return template

def create_level(text, campaign, counter, owner, nick):
    level = Level(text, counter, campaign, owner, nick)
    levels_db.append(level)
    return level

def load_campaign(pkg, user_id, nickname):
    lines = pkg.replace("\r", "").split("\n")
    name = lines[0][lines[0].find(": ") + 2:]
    breaks = []
    for i, line in enumerate(lines[1:], 1):
        if "--------" in line:
            breaks.append(i)
    breaks.append(len(lines))
    
    for i in range(len(breaks) - 1):
        level_text = '\n'.join(lines[breaks[i] + 1:breaks[i + 1]])
        create_level(level_text, name, i + 1, user_id, nickname)

@app.route('/play', methods=['GET', 'POST'])
def game():
    if 'user_id' not in session:
        return redirect('/')
    
    user_id = session['user_id']
    nickname = session['nickname']
    
    if request.method == 'POST':
        info = request.form.get('info', '')
        lastscore = request.form.get('score', '')
        
        if info:
            infoarray = info.split(' ')
            campaign = infoarray[0]
            counter = int(infoarray[1])
            
            # Handle save data
            # Remove old saves
            savedata_db[:] = [s for s in savedata_db if not (s.player == user_id and s.campaign == campaign and s.counter < counter)]
            
            # Create new save
            save = Savedata(user_id, nickname, campaign, counter)
            savedata_db.append(save)
            
            # Handle score
            if lastscore:
                scorearray = lastscore.split(' ')
                if len(scorearray) >= 5:
                    result = Result(
                        user_id, nickname, campaign, counter,
                        int(scorearray[0]), int(scorearray[1]), int(scorearray[2]),
                        int(scorearray[3]), int(scorearray[4])
                    )
                    results_db.append(result)
    
    # Get campaign and counter from URL params
    campaign = request.args.get('campaign', '')
    counter = int(request.args.get('counter', 1))
    
    # Find the level
    current_level = None
    for level in levels_db:
        if level.campaign == campaign and level.counter == counter:
            current_level = level
            break
    
    if not current_level:
        return redirect('/startscreen')
    
    # Generate game page
    template = f'''
    <html>
    <head><title>Slasha - {campaign} Level {counter}</title></head>
    <body>
    <h1>{campaign} - Level {counter}</h1>
    <div id="game-area">
    <pre>{current_level.text}</pre>
    </div>
    <form method="post">
    <input type="hidden" name="info" value="{campaign} {counter}">
    <input type="hidden" name="score" value="1 0 0 0 0">
    <input type="submit" value="Complete Level">
    </form>
    <p><a href="/startscreen">Back to Start Screen</a></p>
    </body>
    </html>
    '''
    
    return template

@app.route('/edit', methods=['GET', 'POST'])
def editor():
    if 'user_id' not in session:
        return redirect('/')
    
    user_id = session['user_id']
    nickname = session['nickname']
    
    campaign = request.args.get('campaign', '')
    counter = int(request.args.get('counter', 1))
    
    # Find the level
    current_level = None
    for level in levels_db:
        if level.campaign == campaign and level.counter == counter:
            current_level = level
            break
    
    if not current_level:
        return redirect('/startscreen')
    
    # Check if user owns the level
    if current_level.owner != user_id:
        return "You don't own this level!"
    
    if request.method == 'POST':
        data = request.form.get('data', '')
        if data:
            current_level.text = data
    
    template = f'''
    <html>
    <head><title>Edit {campaign} Level {counter}</title></head>
    <body>
    <h1>Edit {campaign} - Level {counter}</h1>
    <form method="post">
    <textarea name="data" rows="20" cols="80">{current_level.text}</textarea><br>
    <input type="submit" value="Save Level">
    </form>
    <p><a href="/startscreen">Back to Start Screen</a></p>
    </body>
    </html>
    '''
    
    return template

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
