#! /usr/bin/env python
# Public domain; MZMcBride; 2011

import codecs
import os
import re
import time
import wikitools
import config

# Define variables
directory = config.directory
username = config.username
base_page = config.base_page
access_list = base_page + '/' + config.access_list
status_page = base_page + '/' + config.status
spam = base_page + '/' + config.spam

# Create a home wiki (Meta-Wiki) object
home_wiki = wikitools.Wiki('https://meta.wikimedia.org/w/api.php'); home_wiki.setMaxlag(-1)

# Functions to do various tasks
def kill_self():
    os._exit(0)

def check_status(home_wiki, page):
    status_page_obj = wikitools.Page(home_wiki, status_page, followRedir=False)
    return status_page_obj.getWikiText().lower()

def change_status(status_message):
    status_page_obj = wikitools.Page(home_wiki, status_page, followRedir=False)
    status_page_obj.edit(status_message, summary='Bot: Updated status.', bot=1)
    log.write('will edit with content: %s\n' % status_message)
    return

def top_user(home_wiki, page):
    params = {'action'  : 'query',
              'prop'    : 'revisions',
              'rvprop'  : 'user',
              'titles'  : page}
    req = wikitools.api.APIRequest(home_wiki, params)
    response = req.query()
    latest_editor = response[u'query'][u'pages'].popitem()[1][u'revisions'][0][u'user']
    return latest_editor

def trusted_users(home_wiki, page):
    trusted_users = []
    params = {'action'      : 'query',
              'prop'        : 'links',
              'titles'      : page,
              'pllimit'     : 500,
              'plnamespace' : 2}
    req = wikitools.api.APIRequest(home_wiki, params)
    response = req.query()
    users = response[u'query'][u'pages'].popitem()[1][u'links']
    for entry in users:
        trusted_users.append(entry[u'title'].split(':', 1)[1])
    return trusted_users

def retrieve_config(page):
    spam_page = wikitools.Page(home_wiki, spam, followRedir=False)
    spam_page_text = spam_page.getWikiText()
    spam_page_text_parts = re.search(r'''\<source lang="text" enclose="div">.*?
# KEY(.+)
# RECIPIENTS \(PAGE LIST\)(.+)
# SUBJECT(.+)
# BODY(.+)
</source>''', spam_page_text, re.I|re.U|re.M|re.DOTALL)
    return {'key': spam_page_text_parts.group(1),
            'recip_page': spam_page_text_parts.group(2),
            'subject': spam_page_text_parts.group(3),
            'body': spam_page_text_parts.group(4)}

def read_keys():
    f = open(directory+'deliverybot-3-keys.txt', 'r')
    keys = f.read().strip('\n').split('\n')
    f.close()
    return list(keys)

def add_key(key):
    f = open(directory+'deliverybot-3-keys.txt', 'a')
    f.write('%s\n' % key)
    f.close()
    return

def edit_page(target_site, target_input_page):
    try:
        user_talk = wikitools.Page(target_site, target_input_page, followRedir=True)
    except KeyError:
        log.write('some issue: %s %s' % (target_input_page.decode('utf-8'), target_input_site))
        return
    try:
        page_text = user_talk.getWikiText()
    except:
        page_text = ''
    try:
        if not re.search(r'(<!-- %s %s -->)' % (username, current_key), page_text, re.I|re.U):
            user_talk.edit(text=body_text_final, summary=subject_line, section='new', bot=1, skipmd5=True)
            log.write('Edited: %s at %s\n' % (target_input_page.decode('utf-8'), target_input_site))
        else:
            log.write('Skipped: %s at %s\n' % (target_input_page.decode('utf-8'), target_input_site))
    except:
        time.sleep(2)
        try:
            try:
                page_text = user_talk.getWikiText()
            except:
                page_text = ''
            if not re.search(r'(<!-- %s %s -->)' % (username, current_key), page_text, re.I|re.U):
                user_talk.edit(text=body_text_final, summary=subject_line, section='new', bot=1, skipmd5=True)
                log.write('Edited: %s at %s\n' % (target_input_page.decode('utf-8'), target_input_site))
            else:
                log.write('Skipped: %s at %s\n' % (target_input_page.decode('utf-8'), target_input_site))
        except:
            log.write('WTF1 %s at %s\n' % (target_input_page.decode('utf-8'), target_input_site))
            pass
        log.write('WTF2 %s at %s\n' % (target_input_page.decode('utf-8'), target_input_site))
        pass
    return

def strip_cruft(str):
    str = re.sub(r'^(\s|\n)*', '', str)
    str = re.sub(r'(\s|\n)*$', '', str)
    return str

def parse_input_page(home_wiki, input_page):
    # Define two nasty regexen
    target_template_user_re = re.compile(r'\{\{\s*target\s*\|\s*user\s*=\s*(.+)\s*\|\s*site\s*=\s*(.+)\s*\}\}')
    target_template_page_re = re.compile(r'\{\{\s*target\s*\|\s*page\s*=\s*(.+)\s*\|\s*site\s*=\s*(.+)\s*\}\}')

    valid_sites = get_valid_sites(home_wiki)
    targets_list = []
    targets_obj = wikitools.Page(home_wiki, input_page, followRedir=False)
    targets_page_text = targets_obj.getWikiText()
    for line in targets_page_text.split('\n'):
        if target_template_user_re.search(line):
            input_target_user = target_template_user_re.search(line).group(1).strip()
            input_target_site = target_template_user_re.search(line).group(2).strip()
            if input_target_site in valid_sites:
                targets_list.append([input_target_site, 'User talk:' + input_target_user])
        elif target_template_page_re.search(line):
            input_target_user = target_template_page_re.search(line).group(1).strip()
            input_target_site = target_template_page_re.search(line).group(2).strip()
            if input_target_site in valid_sites:
                targets_list.append([input_target_site, input_target_user])
    targets_list = sorted(targets_list)
    return targets_list

def expand_wikitext(wiki, wikitext):
    params = {'action' : 'expandtemplates',
              'text'   : wikitext}
    req = wikitools.api.APIRequest(wiki, params)
    response = req.query()
    expanded_wikitext = response[u'expandtemplates']['*']
    return expanded_wikitext.encode('utf-8')

def get_valid_sites(home_wiki):
    valid_sites = set()
    params = {'action' : 'sitematrix',
              'smsiteprop' : 'url'}
    req = wikitools.api.APIRequest(home_wiki, params)
    response = req.query()
    for grouping in response[u'sitematrix'].values():
        if type(grouping) is dict:
            for site in grouping[u'site']:
                domain = site[u'url'].split('//', 1)[1]
                valid_sites.add(domain.encode('utf-8'))
        elif type(grouping) is list:
            for site in grouping:
                domain = site[u'url'].split('//', 1)[1]
                valid_sites.add(domain.encode('utf-8'))
    return valid_sites

status = check_status(home_wiki, status_page)

log = codecs.open(directory+'deliverybot-3-log.txt', 'a', 'utf-8')

if status in ('start', 'run', 'really start', 'restart'):
    home_wiki.login(config.username, config.password)
    top_user = top_user(home_wiki, spam)
    trusted_users = trusted_users(home_wiki, access_list)
    old_keys = read_keys()
    configuration = retrieve_config(spam)
    current_key = strip_cruft(configuration['key'])
    add_key(current_key)
    input_page = strip_cruft(configuration['recip_page'])
    targets_list = parse_input_page(home_wiki, input_page)
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
                log.write('use the page list\n')
                change_status('Running')
                target_sites = []
                for target in targets_list:
                    # Edit here!
                    target_input_site = target[0]
                    target_input_page = target[1]
                    log.write('processing %s\n' % target_input_page.decode('utf-8'))
                    if target_input_site not in target_sites:
                        target_sites.append(target_input_site)
                        log.write('target input site: ' + target_input_site + '\n')
                        target_site = wikitools.Wiki('https://%s/w/api.php' % target_input_site); target_site.setMaxlag(-1)
                        target_site.login(config.username, config.password)
                        log.write('logged in to: %s\n' % target_input_site)
                    if target_input_page.find('{') != -1:
                        log.write('need to expand the wikitext...\n')
                        target_input_page = expand_wikitext(target_site, target_input_page)
                        log.write('expanded wikitext: %s\n' % target_input_page.decode('utf-8'))
                    log.write('will edit %s at %s\n' % (target_input_page.decode('utf-8'), target_input_site))
                    edit_page(target_site, target_input_page)
                change_status('Completed run successfully')

        else:
            log.write('key is old, edit status page to indicate such and die\n')
            change_status('Error: Key is invalid')
            kill_self()
    else:
        log.write('user not authorized to use bot; edit status page to indicate such and die\n')
        change_status('Error: User [[%s|not authorized]] to use bot' % access_list)
        kill_self()

# Close the log!
log.close()
