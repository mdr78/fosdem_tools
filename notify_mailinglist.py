#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(c) 2021 Ray Kinsella
'''Tool to distribute FOSDEM Network Devroom CFP'''
import smtplib
import ssl
import sys
import subprocess
import argparse
from argparse import RawTextHelpFormatter
import time
from email.message import EmailMessage
import os

DESCRIPTION = '''
This script reads distribution list information from STDIN in CSV format:

Email,First Name,Last Name,Full name

e.g.

foo@bar.com,Foo,Bar,Foo Bar

The format-ouput parameter indicates if output should go to STOUT or SMTP.

example usage:

cat distribution_list.txt | {s} --format-output <terminal|email> --sender
<you@me.com> --year <year> --smtp-server <server> --password <password> --cfp
<filename> --cover-letter <filename>

'''

def get_message(contact, config):
    '''Build email message from config and contact'''

    message = dict()
    message['Subject'] = 'FOSDEM {} Network Devroom CFP'.format(config['year'])

    body = config['cover-letter'].format(contact.first, config['year'])

    body += os.linesep
    body += '-' * 80
    body += os.linesep

    body += config['cfp']

    message['To'] = [contact.email]
    message['Body'] = body

    return message

class Contact():
    '''Encapsulation contact information'''

    def __init__(self, a):
        if(len(a) != 5):
            raise IndexError

        self.email, self.first, self.last, self.full, self.comment = [
            s.strip() for s in a]



class OutputEmail():
    '''Format the output for email'''
    def __init__(self, config):
        self.config = config

        self.terminal = OutputTerminal(config)
        context = ssl.create_default_context()

        # Try to log in to server and send email
        try:
            self.server = smtplib.SMTP(config['smtp_server'], 587)
            self.server.starttls(context=context) # Secure the connection
            self.server.login(config['sender'], config['password'])
        except Exception as exception:
            print(exception)
            raise exception

    def message(self,message):
        '''send email'''
        self.terminal.message(message)

        msg = EmailMessage()
        msg.set_content(message.pop('Body'))

        for key in message.keys():
            msg[key] = message[key]

        msg['From'] = self.config['sender']
        msg['Reply-To'] = self.config['sender']

        self.server.send_message(msg)

        time.sleep(1)

    def __del__(self):
        self.server.quit()

class OutputTerminal():
    '''Format the output for the terminal'''
    def __init__(self, config):
        self.config = config

    def message(self,message):
        '''Print email to terminal'''

        terminal = 'To:' + ', '.join(message['To']) + '\n'
        if 'sender' in self.config.keys():
            terminal += 'From:' + self.config['sender'] + '\n'

        terminal += 'Reply-To:' + self.config['sender'] + '\n'

        if 'CC' in message:
            terminal += 'CC:' + ', '.join(message['CC']) + '\n'

        terminal += 'Subject:' + message['Subject'] + '\n'
        terminal += 'Body:' + message['Body'] + '\n'

        print(terminal)
        print('-' * 80)

def parse_config(args):
    '''put the command line args in the right places'''
    config = {}
    error_msg = None

    outputs = {
        None : OutputTerminal,
        'terminal' : OutputTerminal,
        'email' : OutputEmail
    }

    if not os.path.isfile(args.cover_letter):
        error_msg = 'cover-letter'

    if not os.path.isfile(args.cfp):
        error_msg = 'cfp'

    if args.format_output == 'email':
        if args.smtp_server is None:
            error_msg = 'SMTP server'
        else:
            config['smtp_server'] = args.smtp_server

        if args.password is None:
            error_msg = 'password'
        else:
            config['password'] = args.password

    if args.year is None:
        error_msg = 'year'

    if args.sender is None:
        error_msg = 'sender'

    if error_msg is not None:
        print('Please specify a {} for email output'.format(error_msg))
        return None

    config['output'] = outputs[args.format_output]
    config['year'] = args.year
    config['cfp'] = open(args.cfp).read()
    config['cover-letter'] = open(args.cover_letter).read()
    config['sender'] = args.sender

    return config

def main():
    '''Main entry point'''
    parser = argparse.ArgumentParser(description=DESCRIPTION.format(s=__file__), \
                                     formatter_class=RawTextHelpFormatter)
    parser.add_argument('--cover-letter', required=True)
    parser.add_argument('--cfp', required=True)
    parser.add_argument('--year', required=True)
    parser.add_argument('--sender', required=True)

    parser.add_argument('--format-output', choices=['terminal','email'], \
                        default='terminal')
    parser.add_argument('--smtp-server')
    parser.add_argument('--password')

    args = parser.parse_args()
    config = parse_config(args)
    if config is None:
        return

    output = config['output'](config)

    for line in sys.stdin:
        line = line.rstrip('\n')

        c = Contact(line.split(','))

        message = get_message(c, config)
        output.message(message)

if __name__ == '__main__':
    main()
