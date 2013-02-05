#! /usr/bin/env python
# Public domain; MZMcBride, bjweeks; 2011

import codecs
import os
import re
import time
import wikitools
import settings

# Define variables
directory = settings.directory
username = settings.username
user_namespace = settings.user_namespace
access_list = user_namespace + ':' + username + '/' + settings.access_list
log = user_namespace + ':' + username + '/' + settings.log
status_page = user_namespace + ':' + username + '/' + settings.status
spam = user_namespace + ':' + username + '/' + settings.spam
wiki = wikitools.Wiki(settings.apiurl); wiki.setMaxlag(-1)

# Functions to do various tasks
def log_in():
    wiki.login(settings.username, settings.password)
    return

def kill_self():
    os._exit(0)

def check_status(page):
    status_page_obj = wikitools.Page(wiki, status_page, followRedir=False)
    return status_page_obj.getWikiText().lower()

def change_status(status_message):
    status_page_obj = wikitools.Page(wiki, status_page, followRedir=False)
    status_page_obj.edit(status_message, summary='[[WP:BOT|Bot]]: Updated status.', bot=1)
    log.write('will edit with content: %s\n' % status_message)
    return

def top_user(wiki, page):
    params = {'action'  : 'query',
              'prop'    : 'revisions',
              'rvprop'  : 'user',
              'titles'  : page}
    req = wikitools.api.APIRequest(wiki, params)
    response = req.query()
    latest_editor = response[u'query'][u'pages'].popitem()[1][u'revisions'][0][u'user']
    return latest_editor

def trusted_users(wiki, page):
    trusted_users = []

    params = {'action'      : 'query',
              'prop'        : 'links',
              'titles'      : page,
              'pllimit'     : 500,
              'plnamespace' : 2}
    req = wikitools.api.APIRequest(wiki, params)
    response = req.query()
    users = response[u'query'][u'pages'].popitem()[1][u'links']
    for entry in users:
        trusted_users.append(entry[u'title'].split(':', 1)[1])
    return trusted_users

def excluded_users(wiki, username):
    excluded_users = []

    params = {'action'      : 'query',
              'prop'        : 'links',
              'titles'      : '|'.join(['Wikipedia:Bots/Opt-out',
                                        'Wikipedia:Bots/Opt-out/%s' % username]),
              'pllimit'     : 500,
              'plnamespace' : 2}
    req = wikitools.api.APIRequest(wiki, params)
    response = req.query()
    pages = response[u'query'][u'pages']
    for k,v in pages.iteritems():
        try:
            users = v[u'links']
            for entry in users:
                excluded_users.append(entry[u'title'].split(':', 1)[1])
        except KeyError:
            pass
    return excluded_users

def retrieve_config(page):
    spam_page = wikitools.Page(wiki, spam, followRedir=False)
    spam_page_text = spam_page.getWikiText()
    spam_page_text_parts = re.search(r'''\<source lang="text" enclose="div">
# KEY(.+)
# RECIPIENTS \(PAGE LIST\)(.+)
# SUBJECT(.+)
# BODY(.+)
</source>''', spam_page_text, re.I|re.U|re.M|re.DOTALL)
    return { 'key': spam_page_text_parts.group(1),
             'recip_page': spam_page_text_parts.group(2),
             'subject': spam_page_text_parts.group(3),
             'body': spam_page_text_parts.group(4) }

def read_keys():
    f = open(directory+'deliverybot-keys.txt', 'r')
    keys = f.read().strip('\n').split('\n')
    f.close()
    return list(keys)

def add_key(key):
    f = open(directory+'deliverybot-keys.txt', 'a')
    f.write('%s\n' % key)
    f.close()
    return

def page_list_targets(wiki, full_page_title):
    page_list_targets = set()

    params = {'action'      : 'query',
              'prop'        : 'links',
              'titles'      : full_page_title,
              'pllimit'     : 500,
              'plnamespace' : '2|3'}
    req = wikitools.api.APIRequest(wiki, params)
    response = req.query()
    users = response[u'query'][u'pages'].popitem()[1][u'links']
    for entry in users:
        page_list_targets.add(entry[u'title'].split(':', 1)[1])
    return page_list_targets

def edit_talk_page(user_talk):
    global excluded_users
    user_talk = wikitools.Page(wiki, 'User talk:%s' % target, followRedir=True)
    try:
        page_text = user_talk.getWikiText()
    except:
        page_text = ''
    try:
        if target in excluded_users:
            log.write('Excluded user: %s\n' % target)
        elif not re.search(r'(<!-- %s %s -->)' % (username, current_key), page_text, re.I|re.U):
            user_talk.edit(text=body_text_final, summary=subject_line, section='new', bot=1, skipmd5=True)
            log.write('Edited: %s\n' % target)
        else:
            log.write('Skipped: %s\n' % target)
    except:
        time.sleep(2)
        try:
            try:
                page_text = user_talk.getWikiText()
            except:
                page_text = ''
            if target in excluded_users:
                log.write('Excluded user: %s\n' % target)
            elif not re.search(r'(<!-- %s %s -->)' % (username, current_key), page_text, re.I|re.U):
                user_talk.edit(text=body_text_final, summary=subject_line, section='new', bot=1, skipmd5=True)
                log.write('Edited: %s\n' % target)
            else:
                log.write('Skipped: %s\n' % target)
        except:
            log.write('WTF1 %s\n' % target)
            pass
        log.write('WTF2 %s\n' % target)
        pass
    return

def strip_cruft(str):
    str = re.sub(r'^(\s|\n)*', '', str)
    str = re.sub(r'(\s|\n)*$', '', str)
    return str

# Start actually doing something
status = check_status(status_page)

log = codecs.open(directory+'deliverybot-log.txt', 'a', 'utf-8')

if status in ('start', 'run', 'really start', 'restart'):
    log_in()
    top_user = top_user(wiki, spam)
    trusted_users = trusted_users(wiki, access_list)
    excluded_users = excluded_users(wiki, username)
    old_keys = read_keys()
    configuration = retrieve_config(spam)
    current_key = strip_cruft(configuration['key'])
    input_page = strip_cruft(configuration['recip_page'])
    subject_line = strip_cruft(configuration['subject'])
    body_text = strip_cruft(configuration['body'])
    body_text_final = body_text + '\n<!-- %s %s -->' % (username, current_key)

    log.write('status is fine, let\'s edit\n')
    if top_user in trusted_users:
        log.write('auth is fine, let\'s edit\n')
        if current_key not in old_keys or status in ('really start', 'restart'):
            log.write('key is fine, let\'s edit\n')
            if len(subject_line) > 245:
                log.write('subject line is too large, edit status page indicating so and die\n')
                change_status('Error: Subject line is too long')
                kill_self()
            else:
                if input_page != '':
                    log.write('use the page list\n')
                    change_status('Running')
                    for target in page_list_targets(wiki, input_page):
                        # Edit here!
                        edit_talk_page(target)
                    add_key(current_key)
                    change_status('Completed run successfully')
        else:
            log.write('key is old, edit status page to indicate such and die\n')
            change_status('Error: Key is invalid')
            kill_self()
    else:
        log.write('user not authorized to use bot; edit status page to indicate such and die\n')
        change_status('Error: User [[%s|not authorized]] to use bot' % access_list)
        kill_self()

log.close()
