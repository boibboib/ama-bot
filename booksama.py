#!/usr/bin/python

# must be python v2, will not work on python v3
import praw
import sys
import urllib2
import simplejson
import lxml.html
import time
import re
import datetime
from apiclient.discovery import build
from lxml.cssselect import CSSSelector


#
# globals
#
logBuf = ""
logTimeStamp = ""
USERNAME = ""
PASSWORD = ""
SUBREDDIT = ""
GOOGLEAPIKEY = ""
USERIP = ""


#
# functions
#

def init (useragent):
    r = praw.Reddit(user_agent=useragent)
    # so that reddit wont translate '>' into '&gt;'
    r.config.decode_html_entities = True
    return r


def login (r, username, password):
    Trying = True
    while Trying:
        try:
            r.login(username, password)
            print('Successfully logged in')
            Trying = False
        except praw.errors.InvalidUserPass:
            print('Wrong Username or Password')
            quit()
        except Exception as e:
            print("%s" % e)
            time.sleep(5)



def DEBUG(s, start=False, stop=False):

    global logBuf
    global logTimeStamp

    print (s)

    logBuf = logBuf + s + "\n\n"
    if stop:
        r.submit("bookbotlog", logTimeStamp, text=logBuf)
        logBuf = ""



def markDownLink (text, url):

    if "goo.gl" not in url and len(url) > 18:
        url = shortener(url)

    return "["+ text +"](" + url + ")"


def extractMarkDownLink (url):
    res = re.search("\[(.*?)\]\((.*?)\)", url)

    if res and res.group(1) and res.group(2):
        return (res.group(1), res.group(2))
    else:
        return url, ""

def shortener(url):

    if "goo.gl" in url:
        return url

    try:
        service = build("urlshortener", "v1", developerKey=GOOGLEAPIKEY)
        body = {"longUrl": url}
        resp = service.url().insert(body=body,userIp=USERIP).execute()
    except Exception as e:
        DEBUG('Exception in shortener() trying to short(%s): %s ' % (url, e))
        return url

    if resp['id']:
        print ("shortener(): %s" % resp['id'])
        return resp['id']
    else:
        DEBUG("shortener(): %s failed" % url)
        return ''



def linksForPrevious (oldAma):

    # Feb 19 | /u/user - Name, Author of ***Title***|[Link](url)

    data = oldAma.split("|")
    # 0 date
    # 1 time
    # 2 person
    # 3 book
    # 4 imageurl
    # 5...

    y,m,d               = data[0].split('-')
    myDate              = datetime.date(int(y), int(m), int(d)).strftime("%b %d")
    realName, dummy     = extractMarkDownLink(data[2])
    bookTitle, dummy    = extractMarkDownLink(data[3])
    dummy, imageUrl     = extractMarkDownLink(data[4])
    realName            = realName.replace("*", "")
    bookTitle           = bookTitle.replace("*", "")

    username = ""
    amaUrl = ""
    srchStr = "title:"+realName + " flair:ama"
    srch = r.search(srchStr, sort="new", subreddit="books", period="week")
    print("searching for: (%s)" % (srchStr))
    for s in srch:
        username = "/u/" + s.author.name
        amaUrl = s.short_link
        break

    if not amaUrl:
        srchStr = "flair:ama"
        srch = r.search(srchStr, sort="new", subreddit="books", period="week")
        print("searching for: (%s)" % (srchStr))
        for s in srch:
            username = "/u/" + s.author.name
            amaUrl = s.short_link
            break

    lineForReddit = "REDDIT\n\n    %s|%s - %s, Author of ***%s***|[Link](%s)\n\n" % \
                    (myDate, username, realName, bookTitle, amaUrl)

    lineForTumblr = "TUMBLR\n\n    imageUrl(%s) amaUrl(%s)\n\n" % (imageUrl, amaUrl)

    print (lineForReddit)
    print (lineForTumblr)

    sr = r.get_subreddit(SUBREDDIT)
    wp = sr.get_wiki_page("ama-old")
    wp.content_md += lineForReddit + lineForTumblr
    sr.edit_wiki_page("ama-old", wp.content_md)





def readMainSched ():
    DEBUG("readMainSched() Entered")
    sr = r.get_subreddit(SUBREDDIT)
    wp = sr.get_wiki_page("ama-schedule")

    es = "####\[\]\(#AMA END"
    ss = "####\[\]\(#AMA START---DO NOT REMOVE OR EDIT THIS LINE\)\r\n"
    m = re.search(ss+"(.*)"+es, wp.content_md, re.DOTALL)

    mainSched = m.group(1).split("\n")
    mainSched = [x.strip() for x in mainSched]

    while not mainSched[-1]: del mainSched[-1]

    todayInSecs = dateToSecs(datetime.date.today().strftime("%Y-%m-%d"))

    tmpList = []
    tmpList.append(mainSched[0])
    tmpList.append(mainSched[1])
    for i in range(2, len(mainSched)):
        secs = dateToSecs(mainSched[i].split("|")[0])
        if secs >= todayInSecs:
            tmpList.append(mainSched[i])
        else:
            linksForPrevious(mainSched[i])


    mainSched = tmpList

    #print ("-----MAIN SCHEDULE----")
    #print (mainSched)
    #print ("-----MAIN SCHEDULE----\n")

    return mainSched

def writeMainSched (mainSched):

    print ("\n-----writeMainSched----")
    #print ("-----MAIN SCHEDULE----")
    #print (mainSched)
    #print ("-----MAIN SCHEDULE----\n")


    sr = r.get_subreddit(SUBREDDIT)
    wp = sr.get_wiki_page("ama-schedule")

    es = "####\[\]\(#AMA END"
    ss = "####\[\]\(#AMA START---DO NOT REMOVE OR EDIT THIS LINE\)\r\n"
    m = re.search(ss+"(.*)"+es, wp.content_md, re.DOTALL)

    newSchedStr = "\n".join(mainSched)
    newSchedStr += "\n"
    newWp = wp.content_md.replace(m.group(1), newSchedStr)
    sr.edit_wiki_page("ama-schedule", newWp)

def writePublicSched (mainSched):
    try:
        print ("\n-----writePublicSched -----")
        sr = r.get_subreddit(SUBREDDIT)
        sb = sr.get_settings()["description"]

        print ("-----MAIN SCHEDULE----\n")
        print (mainSched)
        print ("-----MAIN SCHEDULE----\n")


    #    es = "####\[\]\(#AMA END"
    #    ss = "####\[\]\(#AMA START---DO NOT REMOVE OR EDIT THIS LINE\)\n"

        ss = "# Upcoming AMAs\n \\| \\| \\|\n:-:\\|:-:\\|:-:\n"

        mobj = re.search("(" + ss + ".*?)^\n", sb, re.MULTILINE|re.DOTALL)

        newSchedStr = "# Upcoming AMAs\n | | |\n:-:|:-:|:-:\n"
        print("0 + " + newSchedStr)

        for i in range(2, len(mainSched)):

            # 0 - date
            # 1 - time
            # 2 - author
            # 3 - title
            # 4 - image
            # 5 - title1
            # 6 - title2
            # 7 - twitter

            mainSched[i] = mainSched[i].strip()
            singleSched = mainSched[i].split("|")
            y,m,d = singleSched[0].split('-')

            try:
                # date & time
                newSchedStr += datetime.date(int(y), int(m), int(d)).strftime("%b %d") + " - " + str(singleSched[1]) + "|"
                # author
                newSchedStr += str(singleSched[2]) + "|"
                # description
                newSchedStr += "Author of " + str(singleSched[3])
                if singleSched[5]:
                    if singleSched[6]:
                        newSchedStr += ", " + str(singleSched[5]) + " & " + str(singleSched[6])
                    else:
                        newSchedStr += " & " + str(singleSched[5])
            except Exception as e:
                DEBUG('Exception-x in writePublicSched(): %s ' % (e))

            newSchedStr += "\n"

        print ">>> "+newSchedStr
        newSb = sb.replace(mobj.group(1), newSchedStr)
        e = sr.update_settings(description = newSb)
    except Exception as e:
        DEBUG('Exception-last in writePublicSched(): %s ' % (e))



def dateToSecs (date):

    y,m,d = date.split("-")
    t = datetime.datetime(int(y), int(m), int(d), 0, 0)
    return time.mktime(t.timetuple())


def addMainSched (mainSched, newItem):

    # 'Date|Start Time|Person|NewBook|NBI|OtherBook1|OtherBook2|InfoForTweet'
    mdBookUrl = ['','','']

    done = False

    # author name/url
    if newItem['AuthorUrl:']:
        shortUrl = shortener(newItem['AuthorUrl:'])
        print (">>>>>>>>> "+shortUrl)
        mdAuthorUrl = "[**"+newItem['author:']+"**]("+shortUrl+")"
    else:
        mdAuthorUrl = "**" + newItem['author:'] + "**"

    DEBUG("mdAuthorUrl: (%s) (%s)(%s)" % (mdAuthorUrl, newItem['author:'], newItem['AuthorUrl:']))

    # book title/url
    if newItem['BookUrl:']:
        shortUrl = shortener(newItem['BookUrl:'])
        mdBookUrl[0] = "[*"+newItem['title:']+"*]("+shortUrl+")"
    else:
        mdBookUrl[0] = "*"+newItem['title:']+"*"

    DEBUG("mdBookUrl: (%s) (%s)(%s)" % (mdBookUrl[0], newItem['title:'], newItem['BookUrl:']))

    # book image/url
    if newItem['ImageUrl:']:
        shortUrl = shortener(newItem['ImageUrl:'])
        mdImageUrl = "[pic]("+shortUrl+")"
    else:
        mdImageUrl = ""

    DEBUG("mdImageUrl: (%s) (%s)" % (mdImageUrl, newItem['ImageUrl:']))

    # additional book title/url
    if newItem['Book1Title:']:
        if newItem['Book1Url:']:
            shortUrl = shortener(newItem['Book1Url:'])
            mdBookUrl[1] = "[*"+newItem['Book1Title:']+"*]("+shortUrl+")"
        else:
            mdBookUrl[1] = "*"+newItem['Book1Title:']+"*"


    else:
        mdBookUrl[1] = ""


    # additional book title/url
    if newItem['Book2Title:']:
        if newItem['Book2Url:']:
            shortUrl = shortener(newItem['Book2Url:'])
            mdBookUrl[2] = "[*"+newItem['Book2Title:']+"*]("+shortUrl+")"
        else:
            mdBookUrl[2] = "*"+newItem['Book2Title:']+"*"

    else:
        mdBookUrl[2] = ""



    # 'Date|Start Time|Person|NewBook|NBI| OtherBook1|OtherBook2|InfoForTweet'

    newItemSecs = dateToSecs(newItem['date:'])
    newItemStr = newItem['date:'] + "|" +    \
                 newItem['time:'] + "|" +    \
                 mdAuthorUrl      + "|" +    \
                 mdBookUrl[0]     + "|" +    \
                 mdImageUrl       + "|" +    \
                 mdBookUrl[1]     + "|" +    \
                 mdBookUrl[2]     + "|" +    \
                 newItem['TweetData:']


    DEBUG("newItemStr: %s\n" % newItemStr)
    for i in range(2, len(mainSched)):
        if len(mainSched[i]) < 5:
            continue

        print ("---- LOOKING FOR SLOT----")
        print (mainSched[i])

        print ("newItemSecs: %d" % newItemSecs)
        print("tablesecs: %d" % dateToSecs(mainSched[i].split("|")[0]))


        if newItemSecs == dateToSecs(mainSched[i].split("|")[0]):
            DEBUG("AMA with the same data already exists.\n\n" + newItemStr)
            raise Exception("Duplicate Date!")
        if newItemSecs < dateToSecs(mainSched[i].split("|")[0]):
            mainSched.insert(i, newItemStr)
            done = True
            print ("INSERTED at %d" % i)
            break

    if not done:
        mainSched.append(newItemStr)
        print ("APPENDED TO END")

    print ("\n-----MAIN SCHEDULE----")
    print (mainSched)
    print ("-----MAIN SCHEDULE----\n")
    return mainSched



def parseMsg (msg):
    """ gather the data received into a dict """

    msgData = {'title:':       '',
               'author:':      '',
               'date:':        '',
               'time:':        '',
               'AuthorUrl:':   '',
               'BookUrl:':     '',
               'ImageUrl:':    '',
               'Book1Title:':  '',
               'Book1Url:':    '',
               'Book2Title:':  '',
               'Book2Url:':    '',
               'TweetData:':   ''}

    msglist = msg.split('\n')

    for i in msglist:
        for x in msgData:
            if i.startswith(x):
                msgData[x] = i[len(x):].strip()

    return msgData


def deleteSched(r, msg, author):
    DEBUG("deleteSched() Entered")
    found = False
    replyMsg = ""
    data = parseMsg (msg)
    dateToDelete = dateToSecs (data['date:'])
    mainSched = readMainSched()

    for i in range(2, len(mainSched)):
        print("tablesecs: %d" % dateToSecs(mainSched[i].split("|")[0]))
        td = dateToSecs(mainSched[i].split("|")[0])
        if td == dateToDelete:
            del mainSched[i]
            found = True
            break

    if found:
        writeMainSched(mainSched)
        writePublicSched(mainSched)
        replyMsg = "Success!"
    else:
        replyMsg = "Could not find (%s) in schedule" % data['date:']

    return replyMsg

def editSched(r, msg, author):
    DEBUG("editSched() Entered")
    found = False
    replyMsg = ""
    data = parseMsg (msg)
    dateToDelete = dateToSecs (data['date:'])
    mainSched = readMainSched()

    for i in range(2, len(mainSched)):
        print("tablesecs: %d" % dateToSecs(mainSched[i].split("|")[0]))
        td = dateToSecs(mainSched[i].split("|")[0])
        if td == dateToDelete:

            # extract existing data
            amaToEdit = mainSched[i].split("|")
            # 0-date
            # 1-time
            # 2-author
            # 3-book
            # 4-image
            # 5-book1
            # 6-book2
            # 7-tweetdata

            mydate=mytime=author=title=image=book1title=book2title=tweetdata=""
            dummy, tmpImage = extractMarkDownLink(amaToEdit[4])

            # date, time
            mydate = amaToEdit[0]
            mytime = data['time:'] or amaToEdit[1]

            DEBUG("editSched(): date/time: %s %s" % (mydate, mytime))

            # author
            author = amaToEdit[2]
            if data['author:'] and data['AuthorUrl:']:
                author = markDownLink(data['author:'], data['AuthorUrl:'])
            elif data['author:']:
                author = data['author:']
            elif data['AuthorUrl:']:
                author, dummy = extractMarkDownLink(amaToEdit[2])
                author = markDownLink(author, data['AuthorUrl:'])

            DEBUG("editSched(): author: %s" % author)

            # book title and url
            title = amaToEdit[3]
            if data['title:'] and data['BookUrl:']:
                title = markDownLink(data['title:'], data['BookUrl:'])
            elif data['title:']:
                title = data['title:']
            elif data['BookUrl:']:
                title, dummy = extractMarkDownLink(amaToEdit[3])
                title = markDownLink(title, data['BookUrl:'])

            DEBUG("editSched(): title: " + title)

            # book image
            image = data['ImageUrl:'] or tmpImage
            image = markDownLink("pic", image)

            DEBUG("editSched(): image: " + image)

            # book1
            book1title = amaToEdit[5]
            if data['Book1Title:'] and data['Book1Url:']:
                book1title = markDownLink(data['Book1Title:'], data['Book1Url:'])
            elif data['Book1Title:']:
                book1title = data['Book1Title:']
            elif data['Book1Url:']:
                book1title, dummy = extractMarkDownLink(amaToEdit[5])
                book1title = markDownLink(book1title, data['Book1Url:'])

            DEBUG("editSched(): book1: " + book1title)

            # book2
            book2title = amaToEdit[6]
            if data['Book2Title:'] and data['Book2Url:']:
                book2title = markDownLink(data['Book2Title:'], data['Book2Url:'])
            elif data['Book2Title:']:
                book2title = data['Book2Title:']
            elif data['Book2Url:']:
                book2title, dummy = extractMarkDownLink(amaToEdit[6])
                book2title = markDownLink(book2title, data['Book2Url:'])

            DEBUG("editSched(): book2: " + book2title)

            tweetdata = data['TweetData:'] or amaToEdit[7]

            DEBUG("editSched(): TweetData: " + tweetdata)

            # format new string
            newAma = "%s|%s|%s|%s|%s|%s|%s|%s" % (mydate, mytime, author, title, image, book1title, book2title, tweetdata)
            mainSched[i] = newAma

            # save data
            writeMainSched(mainSched)
            writePublicSched(mainSched)
            replyMsg = "Success!"
            break

        else:
            replyMsg = "Could not find (%s) in schedule" % data['date:']

    return replyMsg


def updateSched(r, msg, author):

    DEBUG("updateSched() entered")
    mainSched = readMainSched()
    writeMainSched(mainSched)
    writePublicSched (mainSched)
    return "Success!"


def addSched (r, msg, author):

    data = parseMsg(msg)
    replyMsg = ""
    bookurl = ""
    imageurl = ""
    error = False

    if not data['title:'] or not data['author:'] or not data['date:']:
        replyMsg += "Error: Missing title, author or date\n\n"
        error = True

    # get author url
    if not error and not data['AuthorUrl:']:
        data['AuthorUrl:'] = getAuthorWebPage (data['author:'])
        if not data['AuthorUrl:']:
            replyMsg += "Error: Cannot get author web page for %s \n\n" % data['author:']

    # get book and image urls
    if not error and (not data['BookUrl:'] or not data['ImageUrl:']):
        grUrl = searchGoodreadsWithGoogle(data['title:'], data['author:'])
        if grUrl:
            bookurl, imageurl = getBookUrl("", grUrl=grUrl)

        if not bookurl or not imageurl:
            replyMsg += "Error getting book url or image url for %s\n\n" % data['title:']
        else:
            data['BookUrl:'] = bookurl
            data['ImageUrl:'] = imageurl


    # get data for another book...
    if not error and data['Book1Title:'] and not data['Book1Url:']:
        grUrl = searchGoodreadsWithGoogle(data['Book1Title:'], data['author:'])
        if grUrl:
            bookurl, imageurl = getBookUrl("", grUrl=grUrl)

        if not bookurl or not imageurl:
            replyMsg += "Error getting book url or image url for %s\n\n" % data['Book2Title:']
        else:
            data['Book1Url:'] = bookurl


    # get data for another book...
    if not error and data['Book2Title:'] and not data['Book2Url:']:
        grUrl = searchGoodreadsWithGoogle(data['Book2Title:'], data['author:'])
        if grUrl:
            bookurl, imageurl = getBookUrl("", grUrl=grUrl)

        if not bookurl or not imageurl:
            replyMsg += "Error getting book url or image url for %s\n\n" % data['Book2Title:']
        else:
            data['Book2Url:'] = bookurl



    print("===== PARSEMSG()START =====")
    for keys,values in data.items():
        print(keys, values)
    print("===== PARSEMSG() END =====")

    if not error:
        DEBUG("Calling readMainSched")
        mainSched = readMainSched()
        DEBUG("Calling addMainSched")
        mainSched = addMainSched(mainSched, data)
        DEBUG("Calling writeMainSched")
        writeMainSched(mainSched)
        DEBUG("Calling writePublicSched")
        writePublicSched(mainSched)
        replyMsg = "Success!"

    return replyMsg


def readConfig ():
    f = open('BooksAMA.conf', 'r')
    buf = f.readlines()
    f.close()

    global USERNAME
    global PASSWORD
    global SUBREDDIT
    global GOOGLEAPIKEY
    global USERIP


    for b in buf:
        if b[0] == '#' or len(b) < 5:
            continue

        if b.startswith('username:'):
            USERNAME = b[len('username:'):].strip()

        if b.startswith('password:'):
            PASSWORD = b[len('password:'):].strip()

        if b.startswith('subreddit:'):
            SUBREDDIT = b[len('subreddit:'):].strip()

        if b.startswith('googleapikey:'):
            GOOGLEAPIKEY = b[len('googleapikey:'):].strip()

        if b.startswith('userip:'):
            USERIP = b[len('userip:'):].strip()


    if not USERNAME or not PASSWORD or not SUBREDDIT or not GOOGLEAPIKEY or not USERIP:
        print ("Missing param from conf file")


def getAuthorWebPage (author):

    authorUrl = ""
    try:
        authorName = author.replace(" ", "%20")
        authorName = "\"" + authorName + "\"" + "%20author"

        url = 'https://ajax.googleapis.com/ajax/services/search/web?v=1.0&q='+authorName

        request = urllib2.Request(url, None, {'Referer': 'www.reddit.com'})
        response = urllib2.urlopen(request)
        results = simplejson.load(response)
        authorUrl = results['responseData']['results'][0]['url'].encode('ascii', 'ignore')

    except Exception as e:
        DEBUG('Exception in getAuthorWebPage(): %s ' % (e))

    return authorUrl

def searchGoodreadsWithGoogle(title, author):

    DEBUG("searchGoodreads...(): ENTER " + title + author)
    grUrl = ""
    try:
        titleName = title.replace(" ", "%20")
        authorName = author.replace(" ", "%20")

        url = "https://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=site%3agoodreads%2ecom%20%22" + titleName + "%22%20%22" + authorName + "%22"
        DEBUG("searchGoodreads...(): google search url " + url)

        request = urllib2.Request(url, None, {'Referer': 'www.reddit.com'})
        response = urllib2.urlopen(request)
        results = simplejson.load(response)
        grUrl = results['responseData']['results'][0]['url'].encode('ascii', 'ignore')

    except Exception as e:
        DEBUG('Exception in searchGoodreadsWithGoogle(): %s ' % (e))

    DEBUG("searchGoodreads...(): google search results: " + grUrl)
    return grUrl



def getISBN (title, author):

    global GOOGLEAPIKEY
    found = False
    bookISBN = ""

    # book['volumeInfo']['canonicalVolumeLink']  google bookUrl
    # book['volumeInfo']['imageLinks']['thumbnail']  google image url

    try:
        service = build('books', 'v1', developerKey=GOOGLEAPIKEY)
        request = service.volumes().list(source='public', q=title)
        response = request.execute()
        DEBUG('Found %d books: for %s - %s' % (len(response['items']), title, author))

        authorName = author.split()
        for book in response.get('items', []):

            if 'title' in book['volumeInfo'].keys() and 'authors' in book['volumeInfo'].keys():

                #see if the author's last name is in the book results
                if authorName[-1].lower() in str(book['volumeInfo']['authors']).lower():
                    DEBUG('Title: %s, Authors: %s' % (book['volumeInfo']['title'],book['volumeInfo']['authors']))

                    isbnNum = len(book['volumeInfo']['industryIdentifiers'])
                    print book['volumeInfo']['industryIdentifiers']
                    for i in range (isbnNum):
                        if len(book['volumeInfo']['industryIdentifiers'][i]['identifier']) == 13:
                            bookISBN = book['volumeInfo']['industryIdentifiers'][i]['identifier'].encode('ascii', 'ignore')
                            found = True
                            break
            if found:
                break

    except Exception as e:
        DEBUG('Exception in getISBN(): %s ' % (e))

    return bookISBN



def getBookUrl(isbn, grUrl=""):
    url = "http://www.goodreads.com/search/search?search_type=books&search%5Bquery%5D=" + isbn
    image = ""

    if grUrl:
        url = grUrl
        DEBUG("getBookUrl(): Using grUrl")
    try:
        usock = urllib2.urlopen(url)
        data = usock.read()
        usock.close()
    except Exception as e:
        DEBUG('Exception1 in getBookUrl(): %s ' % (e))
        return "", ""


    try:
        # get the 'coverImage'
        tree = lxml.html.fromstring(data)
        sel = CSSSelector('img#coverImage')
        css = sel(tree)
        image = css[0].get('src')

        # get the 'canonical' url - the real url of this webpage
        sel = CSSSelector('head link')
        css = sel(tree)
        for acss in css:
          if acss.get('rel') == 'canonical':
              url = acss.get('href')
              break

    except Exception as e:
        DEBUG('Exception2 in getBookUrl(): %s ' % (e))
        return "", ""

    return url, image






### find my public ip
#       simplejson.load(urllib2.urlopen('http://httpbin.org/ip'))['origin']




def getMail ():

    global logTimeStamp

    commands = {
        "addsched":      addSched,
        "deletesched":   deleteSched,
        "editsched":     editSched,
        "updatesched":   updateSched,
    }



    sr = r.get_subreddit(SUBREDDIT)
    mods = sr.get_moderators()

    while True:
        time.sleep(5)
        try:
            inboxMsg = None
            inbox = r.get_unread(limit=300)

            if not inbox:
                print ("aint got no messages")
            else:
                for inboxMsg in inbox:
                    isMod = False
                    error = False
                    cmd = ""
                    subred = ""
                    logTimeStamp = "cmrc - /r/" + SUBREDDIT + " - " + time.strftime("%d%b%Y-%H:%M:%S")

                    print ("msg from " + inboxMsg.author.name)
                    if inboxMsg.author.name == "mod_mailer":
                        inboxMsg.mark_as_read()
                        inboxMsg = None
                        continue


                    DEBUG("Msg **%s** from **%s**" % (inboxMsg.subject, inboxMsg.author.name))

                    #
                    # did the msg come from a moderator?
                    #
                    for mod in mods:
                        if mod.name == inboxMsg.author.name:
                            isMod = True
                            break

                    if not isMod:
                        msg = "*I am a bot* and I only talk to /r/books moderators."
                        print(msg)
                        error = True

                    #
                    # did they send the cmd and subreddit in the subject field?
                    #
                    if not error:
                        try:
                            cmd, subred = inboxMsg.subject.split()
                        except:
                            pass

                        if not cmd or not subred:
                            msg = "unknown cmd: (%s) " % inboxMsg.subject.strip()
                            print(msg)
                            error = True

                    #
                    # is the subreddit valid?
                    #
                    if not error:
                        if subred != 'books' and subred != "boibtest":
                            msg = "invalid subreddit: " + subred
                            print(msg)
                            error = True

                    #
                    # if the cmd is valid, execute!
                    #
                    if not error:
                        if cmd.lower() in commands:
                            try:
                                msg = commands[cmd](r, inboxMsg.body, inboxMsg.author.name)
                            except Exception as e:
                                DEBUG('Exception in getMail() after command: %s ' % (e))
                                msg = "There was an error..."

                            #DEBUG("Reply to (%s):\n\n%s" % (inboxMsg.author.name, msg), stop=True)
                        else:
                            msg = "unknown cmd: (%s) (%s) " % (cmd, subred)

                    #
                    # log it, reply to sender, mark it read
                    #
                    DEBUG(msg, stop=True)
                    if len(msg) == 0:
                        msg="thanks for playing"
                    try:
                        inboxMsg.reply(msg)
                    except:
                        pass
                    inboxMsg.mark_as_read()
                    inboxMsg = None


        except Exception as e:
            if "503" not in e:
                DEBUG('Exception in getMail(): %s ' % (e))
            if inboxMsg:
                try:
                    inboxMsg.reply("**Error:** " + e)
                    inboxMsg.mark_as_read()
                    inboxMsg = None
                except:
                    DEBUG('An error has occured trying to reply: %s ' % (e))
            continue





#########  main()  ########################
if __name__=='__main__':

    readConfig ()

    print("==============================")
    r = init("ama-bot v1.0 - /u/" + USERNAME)
    login(r, USERNAME, PASSWORD)
    print("==============================")

    getMail()





