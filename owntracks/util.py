__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

from owntracks import cf

def tsplit(topic, nparts=cf.topicparts):
    ''' split a slash-separated topic into a prefix and a suffix,
        putting `nparts' of the topic into prefix, rest in suffix.
        Handle the case where topic begins with a slash.

        /oo/gg/JP/cmd/out              '/oo/gg/JP'     'cmd/out'
        oo/gg/JP                       'oo/gg/JP'     ''
        aa/bb                          'aa/bb'     ''
        oo/gg/JP/cmd                   'oo/gg/JP'     'cmd'
        /aa/bb                         '/aa/bb'     ''
    '''

    prefix = suffix = ""
    badslash = False

    if topic.startswith('/'):
        badslash = True
        topic = topic[1:]

    p = topic.split('/')
    if len(p) <= nparts:
        prefix = topic
        suffix = ""
    else:
        prefix = "/".join(p[0:nparts])
        suffix = "/".join(p[nparts:])


    if badslash:
        prefix = '/' + prefix
    return prefix, suffix
