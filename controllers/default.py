from ballot import ballot2form, form2ballot, blank_ballot, sign, uuid, regex_email, rsakeys
import re
import json
from threading import Timer
def index():
    return dict()

@auth.requires_login()
def elections():
    response.subtitle = T('My Elections')
    elections = db(db.election.created_by==auth.user.id).select(
        orderby=~db.election.created_on)
    ballots = db(db.voter.email == auth.user.email)(db.voter.election_id==db.election.id)(
        (db.election.deadline==None)|(db.election.deadline>request.now)).select()
    ended_elections = db(db.voter.email == auth.user.email)(db.voter.election_id==db.election.id)(
        (db.election.deadline<request.now)).select()
    for election in elections:
        if election.deadline and (election.deadline) < request.now and election.closed==False:
            print("cl")
            print(db(db.election.deadline < request.now).update(closed=True))
    return dict(elections=elections,ballots=ballots,ended_elections=ended_elections)

# @auth.requires(auth.user and auth.user.is_manager)
# @auth.requires(auth.user)
def edit():
    response.subtitle = T('Edit Ballot')
    election = db.election(request.args(0,cast=int,default=0))
    if election and not election.created_by==auth.user_id:
        redirect(URL('not_authorized'))
    if not election:
        (pubkey, privkey) = rsakeys()
        db.election.voters.default = auth.user.email
        db.election.manager.default = auth.user.email
        db.election.public_key.default = pubkey
        db.election.private_key.default = privkey
    form = SQLFORM(db.election,election,deletable=True,
                   submit_button="Save and Preview").process()
    if form.accepted:
        if len(form.vars.ballot_model)==2:
            session.flash = T('Please add a new voting question!')
            redirect(URL('edit',args=form.vars.id))
        else :
            print(form.vars.ballot_model)
            redirect(URL('start',args=form.vars.id))
    return dict(form=form)

# @auth.requires(auth.user and auth.user.is_manager)
# @auth.requires(auth.user)
def start():
    election = db.election(request.args(0,cast=int)) or redirect(URL('index'))
    check_closed(election)
    response.subtitle = election.title+T(' / Start')
    demo = ballot2form(election.ballot_model)
    # election.ballot_model = [{"preamble":"","answers":["A","V","X"],"algorithm":"simple-majority","randomize":true,"comments":false,"name":"321331244310","type":"simple-majority"}]

    return dict(demo=demo,election=election)

# @auth.requires(auth.user and auth.user.is_manager) # 信箱設置:evote\private\appconfig.ini
# @auth.requires(auth.user)
def start_callback():
    election = db.election(request.args(0,cast=int)) or redirect(URL('index'))
    check_closed(election)
    form = SQLFORM.factory(
        submit_button=T('Email Voters and Start Election Now!'))
    form.element(_type='submit').add_class('btn')
    failures = []
    emails = []
    owner_email = election.created_by.email
    url='applications/evote/uploads/'+str(election.voters)
    with open(url) as stream:
        election.voters=stream.read()
    print("test "+election.voters)
    if form.process().accepted:
        ballot_counter = db(db.ballot.election_id==election.id).count()
        for email in regex_email.findall(election.voters):
            email = email.lower()
            voter = db(db.voter.election_id==election.id)\
                (db.voter.email==email).select().first()
            if voter:
                voter_uuid = voter.voter_uuid
            else:
                # create a voter
                voter_uuid = 'voter-'+uuid()
                voter = db.voter.insert(
                    election_id=election.id,
                    voter_uuid=voter_uuid,
                    email=email,invited_on=None)
                # create a ballot
                ballot_counter+=1
                ballot_uuid = 'ballot-%i-%.6i' % (election.id,ballot_counter)
                blank_ballot_content = blank_ballot(ballot_uuid)
                signature = 'signature-'+sign(blank_ballot_content.encode("utf-8"),election.private_key).decode("utf-8")
                db.ballot.insert(
                    election_id=election.id,
                    ballot_content = blank_ballot_content,
                    ballot_uuid=ballot_uuid,
                    signature = signature)
            link_vote = URL('vote',args=(election.id,voter_uuid),scheme=SCHEME)
            link_ballots = URL('ballots',args=election.id,scheme=SCHEME)
            link_results = URL('results',args=election.id,scheme=SCHEME)
            body = message_replace(vote_email_default,
                                      election_id = election.id,
                                      owner_email = owner_email,
                                      title=election.title,
                                      link=link_vote,
                                      link_ballots=link_ballots,
                                      link_results=link_results)
            if election.comments_not_voted_email!= None:
                body=election.comments_vote_email+"\n"+body
            print(body)
            subject = '%s [%s]' % (election.title, election.id)
            emails.append((voter,email,subject,body))
        db.commit()
        sender = election.email_sender or mail.settings.sender
        for voter, to, subject, body in emails:
            if mail.send(to=to, subject=subject, message=body, sender=sender):
                db(db.voter.id==voter).update(invited_on=request.now)
            else:
                failures.append(to)
        if not failures:
            session.flash = T('Emails sent successfully')
            print("election started!!!!----------------------" )
            election.update_record(started=True)
            redirect(URL('elections'),client_side=True)
    return dict(form=form,failures=failures,election=election)


@auth.requires(False) # for now this is disabled
def self_service():
    form = SQLFORM.factory(
        Field('election_id','integer',requires=IS_NOT_EMPTY()),
        Field('email',requires=IS_EMAIL()))
    if form.process().accepted:
        election = db.election(form.vars.id)
        if not election: form.errors['election_id'] = 'Invalid'
        voter = db.voter(election=election_id,email=form.vars.email)
        if not voter: form.errors['voter'] = 'Invalid'
        if voter.voted:
            response.flash = T('User has voted alreday')
        else:
            link_vote = URL('vote',args=(election.id,voter_uuid),scheme=SCHEME)
            link_ballots = URL('ballots',args=election.id,scheme=SCHEME)
            link_results = URL('results',args=election.id,scheme=SCHEME)
            body = message_replace(vote_email_default,
                                      election_id = election.id,
                                      owner_email = owner_email,
                                      title=election.title,
                                      link=link_vote,
                                      link_ballots=link_ballots,
                                      link_results=link_results)
            body=body+"\n"+election.comments_vote_email
            print(body)
            sender = election.email_sender or mail.settings.sender
            if mail.send(to=voter.email, subject=election.title, message=body, sender=sender):
                response.flash = T('Email sent')
            else:
                response.flash = T('Unable to send email')
    return dict(form=form)

# @auth.requires(auth.user and auth.user.is_manager)
# @auth.requires(auth.user)
def reminders():
    election = db.election(request.args(0,cast=int)) or redirect(URL('index'))
    response.subtitle = election.title+T(' / Reminders')
    return dict(election=election)

# @auth.requires(auth.user and auth.user.is_manager)
# @auth.requires(auth.user)
def reminders_callback():
    election = db.election(request.args(0,cast=int)) or redirect(URL('index'))
    owner_email = election.created_by.email
    failures = []
    emails = []
    fields = []
    for email in regex_email.findall(election.voters):
        voter = db(db.voter.election_id==election.id)\
            (db.voter.email==email).select().first()
        voter_uuid = voter.voter_uuid
        key = 'voter_%s' % voter.id
        fields.append(Field(key,'boolean',default=not voter.voted,
                            label = voter.email))
        if key in request.post_vars:
            link = URL('vote',args=(election.id,voter_uuid),scheme=SCHEME)
            link_ballots = URL('ballots',args=election.id,scheme=SCHEME)
            link_results = URL('results',args=election.id,scheme=SCHEME)
            body = message_replace(vote_email_default,
                                      election_id = election.id,
                                      owner_email = owner_email,
                                      title=election.title,
                                      link=link,
                                      link_ballots=link_ballots,
                                      link_results=link_results)
            body=election.comments_vote_email+"\n"+body
            print(body)
            subject = '%s [%s]' % (election.title, election.id)
            emails.append((email,subject,body))
    form = SQLFORM.factory(*fields).process()
    if form.accepted:
        sender = election.email_sender or mail.settings.sender
        for to, subject, body in emails:
            if not mail.send(to=to, subject=subject, message=body, sender=sender):

                failures.append(email)
        if not failures:
            session.flash = T('Emails sent successfully')
            redirect(URL('elections'),client_side=True)
    return dict(form=form,failures=failures,election=election)

# @auth.requires(auth.user and auth.user.is_manager)
# @auth.requires(auth.user)
def recompute_results():
    election = db.election(request.args(0,cast=int)) or redirect(URL('index'))
    compute_results(election)
    redirect(URL('results',args=election.id))

def compute_results(election):
    query = db.ballot.election_id==election.id
    voted_ballots = db(query)(db.ballot.voted==True).select()
    counters = {}
    rankers = {}

    ballot_structure = json.loads(election.ballot_model)   #取得計票方法名稱
    # print(type(ballot_structure))
    # print(ballot_structure)

    for k,ballot in enumerate(voted_ballots):
        for name in ballot.results:  #ballot.results is a dict  name is ballot number
            # name is the name of a group as in {{name:ranking}}
            # scheme is "ranking" or "checkbox" (default)
            # value is the <input value="value"> assigned to this checkbox or input

            # 投票辦法修改處:evote\static\js\custom.js
            # INPORTANT ONLY SUPPORT SIMPLE MAJORITY
            ballot_way = ""
            for results_dict in ballot_structure:
                if results_dict['name'] == name:
                    ballot_way = results_dict['algorithm']
                    break

            key = name +'/'+ballot_way+'/' + ballot.results[name]
            (name,scheme,value) = key.split('/',3)
            # print(name,scheme,value,"aaaa")
            if scheme == 'simple-majority':

                # counters[key] counts how many times this checkbox was checked
                counters[key] = counters.get(key,0) + 1    #更新票數
    election.update_record(counters=counters)

#@cache(request.env.path_info,time_expire=300,cache_model=cache.ram)
def results():
    id = request.args(0,cast=int) or redirect(URL('index'))
    election = db.election(id) or redirect(URL('index'))
    # if auth.user_id!=election.created_by and \
            # not(election.deadline and request.now>election.deadline):
        # session.flash = T('Results not yet available')
        # redirect(URL('index'))
    if not(election.deadline and request.now>election.deadline):
        session.flash = T('Results not yet available')
        redirect(URL('elections'))

    response.subtitle = election.title + T(' / Results')
    if (DEBUG_MODE or not election.counters or
        not election.deadline or request.now<=election.deadline):
        compute_results(election)
    form = ballot2form(election.ballot_model, counters=election.counters)
    return dict(form=form,election=election)

def hash_ballot(text):
    import re
    text = text.replace('checked="checked" ','')
    text = text.replace('disabled="disabled" ','')
    text = re.sub('value="\d+"','',text)
    text = re.sub('ballot\S+','',text)
    return hash(text)

def ballots():
    election = db.election(request.args(0,cast=int)) or \
        redirect(URL('invalid_link'))
    response.subtitle = election.title + T(' / Ballots')
    ballots = db(db.ballot.election_id==election.id).select(
        orderby=db.ballot.ballot_uuid)
    tampered = len(set(hash_ballot(b.ballot_content)
                       for b in ballots if b.voted))>1
    return dict(ballots=ballots,election=election, tampered=tampered)

# @auth.requires(auth.user and auth.user.is_manager)
def email_voter_and_manager(election,voter,ballot,body):
    import io
    attachment = mail.Attachment(
        filename=ballot.ballot_uuid+'.html',
        payload=io.StringIO(ballot.ballot_content))
    sender = election.email_sender or mail.settings.sender
    ret = mail.send(to=voter.email,
                    subject='Receipt for %s' % election.title,
                    message=body,attachments=[attachment],
                    sender=sender)
    # mail.send(to=election.manager,
    #           subject='Copy of Receipt for %s' % election.title,
    #           message=body,
    #           attachments=[attachment],
    #           sender=sender)
    return ret

def check_closed(election):
    if election.closed:
        session.flash = T('Election already closed')
        redirect(URL('elections'))


def close_election():
    import zipfile, os
    election = db.election(request.args(0,cast=int)) or \
        redirect(URL('invalid_link'))
    #check_closed(election)
    response.subtitle = election.title
    dialog = FORM.confirm(T('Close'),
                          {T('Cancel'):URL('elections')})
    if dialog.accepted:
        election.update_record(deadline=request.now)
        voters = db(db.voter.election_id==election.id)\
            (db.voter.voted==False).select()
        ballots = db(db.ballot.election_id==election.id)\
            (db.ballot.voted==False).select()
        if ballots and len(voters)!=len(ballots):
            session.flash = T('Voted corrupted ballots/voter mismatch')
            redirect(URL('elections'))
        owner_email = election.created_by.email
        for i in range(len(voters)):
            voter, ballot = voters[i], ballots[i]
            link = URL('ballot',args=ballot.ballot_uuid,scheme='http')
            body = message_replace(not_voted_email_default,
                                      election_id=election.id,
                                      owner_email = owner_email,
                                      title=election.title,
                                      signature=ballot.signature,link=link)
            if election.comments_not_voted_email!= None:
                body=election.comments_not_voted_email+"\n"+body
            print(body)
            email_voter_and_manager(election,voter,ballot,body)
        compute_results(election)
        zippath = os.path.join(request.folder,'static','zips')
        if not os.path.exists(zippath):
            os.mkdir(zippath)
        archive = zipfile.ZipFile(
            os.path.join(zippath,'%s.zip' % election.id),'w')
        dbset = db(db.ballot.election_id==election.id)
        ballots = dbset.select()
        for ballot in ballots:
            archive.writestr(ballot.ballot_uuid,ballot.ballot_content)
        ballots = dbset.select(
            db.ballot.election_id,
            db.ballot.ballot_uuid,
            db.ballot.voted,
            db.ballot.voted_on,
            db.ballot.signature,
            orderby=db.ballot.ballot_uuid)
        archive.writestr('ballots.csv',str(ballots))
        archive.close()
        election.update_record(closed=True)
        session.flash = 'Election Closed!'
        redirect(URL('results',args=election.id))
    return dict(dialog=dialog,election=election)

def ballot():
    ballot_uuid = request.args(0) or redirect(URL('index'))
    signature = request.args(1)
    election_id = int(ballot_uuid.split('-')[1])
    election = db.election(election_id) or redirect(URL('index'))
    ballot = db.ballot(election_id=election.id,ballot_uuid=ballot_uuid) \
        or redirect(URL('invalid_link'))
    if (not election.deadline or election.deadline>request.now) \
            and ballot.signature!=signature:
        session.flash = "your ballot is not visible until election is closed"
        redirect(URL('elections'))
    response.subtitle = election.title + T(' / Ballot')
    return dict(ballot_uuid=ballot_uuid,ballot=ballot,election=election)


def delete_election():
    election = db.election(request.args(0,cast=int,default=0))
    dialog = FORM.confirm(T('Delete'),{T('Cancel'):URL('elections')})
    if dialog.accepted:
        db(db.voter.election_id==election.id).delete()
        db(db.ballot.election_id==election.id).delete()
        db(db.election.id==election.id).delete()
        redirect(URL('elections'))
    return dict(dialog=dialog,election=election)

def recorded():
    return dict()

def ballot_verifier():
    response.headers['Content-Type'] = 'text/plain'
    return ballot()

def vote():
    import hashlib
    response.menu = []
    election_id = request.args(0,cast=int)
    voter_uuid = request.args(1)
    election = db.election(election_id) or redirect(URL('invalid_link'))
    voter = db(db.voter.election_id==election_id)\
        (db.voter.voter_uuid==voter_uuid).select().first() or \
        redirect(URL('invalid_link'))
    if not DEBUG_MODE and voter.voted:
        redirect(URL('voted_already'))

    if election.deadline and request.now>election.deadline:
        session.flash = T('Election is closed')
        if voter.voted:
            session.flash += T('Your vote was recorded')
        else:
            session.flash += T('Your vote was NOT recorded')
        redirect(URL('results',args=election.id))
    response.subtitle = election.title + ' / Vote'
    form = ballot2form(election.ballot_model, readonly=False)
    form.process()
    if form.accepted:
        results = form.vars
        for_update = not db._uri.startswith('sqlite') # not suported by sqlite
        # if not for_update: db.executesql('begin immediate transaction;')
        ballot = db(db.ballot.election_id==election_id)\
            (db.ballot.voted==False).select(
            orderby='<random>',limitby=(0,1),for_update=for_update).first() \
            or redirect(URL('no_more_ballots'))
        ballot_content = form2ballot(election.ballot_model,token=ballot.ballot_uuid,vars=request.post_vars,results=results)
        signature = 'signature-'+sign(ballot_content,election.private_key).decode("utf-8")
        ballot.update_record(results=results,
                             ballot_content=ballot_content,
                             signature=signature,
                             voted=True,voted_on=request.now)
        voter.update_record(voted=True)
        link = URL('ballot',args=(ballot.ballot_uuid,ballot.signature), scheme='http')

        body = message_replace(voted_email_default,link=link,
                                  election_id=election.id,
                                  owner_email = election.created_by.email,
                                  title=election.title,signature=signature)
        if election.comments_voted_email!= None:
            body=election.comments_voted_email+"\n"+body
        print(body)
        emailed = email_voter_and_manager(election,voter,ballot,body)
        session.flash = \
            T('Your vote was recorded and we sent you an email') \
            if emailed else \
            T('Your vote was recorded but we failed to email you')
        redirect(URL('recorded',vars=dict(link=link)))
    return dict(form=form)

def user():
    return dict(form=auth())

def invalid_link():
    return dict(message=T('Invalid Link'))

def voted_already():
    return dict(message=T('You already voted'))

def not_authorized():
    return dict(message=T('Not Authorized'))

def no_more_ballots():
    return dict(message=T('Run out of ballots. Your vote was not recorded'))

# @auth.requires(auth.user and auth.user.is_manager)
# @auth.requires(auth.user)
def voters_csv():
    election = db.election(request.args(0,cast=int,default=0),created_by=auth.user.id)
    return db(db.voter.election_id==election.id).select(
        db.voter.election_id,db.voter.email,db.voter.voted).as_csv()

# def features():
#     return locals()

# def support():
#     return locals()

def workflow():
    return locals()

def upload_voters():
    return dict(form=SQLFORM(db.election).process())
