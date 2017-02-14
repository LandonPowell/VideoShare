# Asynchronous multiprocessing is necessary for using moviepy in this context.
from multiprocessing import Process
# Imports for Tornado's basic functions. Webpy was easier.
import tornado.template, tornado.ioloop, tornado.web
# Sometimes I want blocking, sometimes I don't. Is that so much to ask for in a fucking Mongo controller?
import motor.motor_tornado, pymongo 
# Required for video files. I might consider moving to ffmpeg if I can figure out an easy way to watermark with it.
import moviepy.editor as vid
# Config file. It's just a 'config.py' in the root directory. It's better this way.
import config

def to36(number): # Converts integers into base 36. Should be a default function.
    alphabet = '0123456789abcdefghijklmnopqrstuvwxyz'
    base36 = ''
    while number:
        number, i = divmod(number, 36)
        base36 = alphabet[i] + base36
    return base36

def tokenize(string):
    # To-do WIP
    string = string.lower()
    return string.split(" ")

templates   = tornado.template.Loader("html")

client      = motor.motor_tornado.MotorClient( config.db )  # Two connections,
blockClient = pymongo.MongoClient( config.db )              # because blocking.

database    = client[ config.name ]
blockDB     = blockClient[ config.name ]                

def counterStartup(value, error): # Defines counters.
    if value == None:
        database.counters.insert( {"video"  : 1} )
        database.counters.insert( {"user"   : 1} )

database.counters.find_one( # Simple test to see if the counters are defined.
    {"video": {"$gt": 0}},
    callback=counterStartup
)

class embedVideo(tornado.web.RequestHandler):
    def get(self, videoID):
        self.write( templates.load("videoPlayer.html").generate(
            name    = config.name,
            video   = "r" + videoID + ".webm",
        ) )

class watchVideo(tornado.web.RequestHandler):
    def get(self, videoID):
        value = blockDB.videos.find_one( {"vidID" : videoID} )

        if value == None:
            self.write( templates.load("error.html").generate(
                name    = config.name,
                header  = "404",
                error   = "That video doesn't exist."
            ) )
        else:
            self.write( templates.load("watchVideo.html").generate(
                name    = config.name,
                embed   = "e" + videoID,
                title   = value['title'],
                paste   = value['paste'],
            ) )

def writeVideo(videoData, videoObject):

    vidID = videoObject["vidID"]

    database.videosProcessing.update({
        "vidID" : vidID
    },{ "$set" : {
        "status" : "writing video"
    }})

    # I create a temporary video file here so that I can edit it with MoviePy
    fileType = videoData["filename"].split(".")[-1]
    with open("tempFiles/video."+fileType, "wb") as file:
        file.write(videoData["body"])
    videoClip = vid.VideoFileClip("tempFiles/video."+fileType)

    # Conditional for adding watermark. Could also be used to modify video.
    if config.watermark:
        watermark = vid.ImageClip(
            "watermark.png", 
            duration = videoClip.duration
        )
        fullVideo = vid.CompositeVideoClip([videoClip, watermark])

    else: 
        fullVideo = videoClip

    fullVideo.write_videofile(
        "videos/" + vidID + ".webm"
    )

    database.videosProcessing.update({
        "vidID" : vidID
    },{ "$set" : {
        "status" : "writing thumbnail"
    }})

    thumbnail = videoClip.volumex(0)
    thumbnail.resize( (100, 50) )

    thumbnail.write_videofile(
        "thumbnails/" + vidID + ".webm",
        fps = 2
    )

    database.videosProcessing.delete_one({ "vidID" : vidID })

class uploadVideo(tornado.web.RequestHandler):
    # To-do: Optimize how this works a bit. 
    # It's currently using both the databases due to the fact that it needs to
    # write the video's url to the user but needs to do the writing to the DB as async. 
    def post(self):
        if "video" in self.request.files: # Checks if user uploaded a video.

            videoTitle  = self.get_argument("title") or "Untitled Video"
            videoTags   = self.get_argument("tags" ) or "no-tag-vid"
            pasteBin    = self.get_argument("paste", "No Pasted Info")

            videoData = self.request.files["video"][0]

            currentVideo = blockDB.counters.find_one({"video" : {"$gt":0}})['video']

            self.write( templates.load("videoProcessing.html").generate(
                name = config.name,
                id = to36(currentVideo)
            ) )

            def newVideo(value, error):
                database.counters.update(
                    {'_id'  : value['_id']      },
                    {'video': value['video']+1  }
                )

                vidID = to36( value['video'] )

                videoObject = {
                    "vidID" : vidID,
                    "title" : videoTitle,
                    "tags"  : tokenize(videoTags),
                    "paste" : pasteBin,
                }

                database.videosProcessing.insert({
                    "vidID" : vidID,
                    "status": "starting",
                })

                videoWriter = Process(
                    target  = writeVideo,
                    args    = ( videoData, videoObject )
                )
                videoWriter.start()

                database.videos.insert(videoObject)

            database.counters.find_one(
                {"video": {"$gt": 0}},
                callback=newVideo
            )

        else:
            self.write( templates.load("error.html").generate(
                name    = config.name,
                header  = "Sorry,",
                error   = "but it looks like you didn't pick a file to upload."
            ) )

def searchEngine(keywords, page, limit=config.resultsPerPage):
    # I can add to this later and adapt it later.
    # For now, it's beauty through simplicity.
    matching = blockDB.videos.find({ 
        "tags" : { "$all" : keywords }
    }).sort([("_id", -1)])

    startIndex  = page * limit
    stopIndex   = startIndex + limit

    if matching.count() == 0:
        return []

    if matching.count() < stopIndex:
        return matching[0:matching.count()]

    return matching[startIndex:stopIndex]

class search(tornado.web.RequestHandler):
    def get(self):

        try:    keywords = self.get_argument('query').split(" ")
        except: return False

        try:    page = int(keywords = self.get_argument('page'))
        except: page = 0

        searchResult = searchEngine(keywords, page)

        self.write( templates.load("search.html").generate(
            name = config.name,
            searchString = " ".join(keywords),
            videos = searchResult
        ) )

class index(tornado.web.RequestHandler):
    def get(self):
        videos = blockDB.videos.find().sort([("_id", -1)])

        limit = 5

        recentVideos = (
            videos[0:limit]
            if limit < videos.count() else
            videos[0:videos.count()]
        )

        self.write( templates.load("index.html").generate(
            name = config.name,
            recentVideos = recentVideos,
            recommended = [] # ToDo
        ) )

class status(tornado.web.RequestHandler):
    def get(self, videoID):
        info = blockDB.videosProcessing.find_one({ "vidID" : videoID })

        if info == None or 'status' not in info:
            self.write("done")
        else: self.write( info['status'] )

def makeApp():
    return tornado.web.Application([
        (r"/status/(\w*)",  status  ),

        (r"/js/(.*)",   tornado.web.StaticFileHandler, {"path":"js"}        ),      # This handles serving javascript.
        (r"/css/(.*)",  tornado.web.StaticFileHandler, {"path":"css"}       ),      # This handles the serving of stylesheets.
        (r"/thumb/(.*)",tornado.web.StaticFileHandler, {"path":"thumbnails"}),      # This handles the serving of thumbnail videos.
        (r"/r(.*)",     tornado.web.StaticFileHandler, {"path":"videos"}    ),      # It should be noted, there is no '/' after 'r'. This handles serving raw video.

        (r"/e(\w*)",    embedVideo  ),  # An embeded video.
        (r"/v(\w*)",    watchVideo  ),  # A normal video page.
        (r"/upload",    uploadVideo ),  # The uploads form.
        (r"/search",    search      ),  # Simple search page.
        (r"/.*",        index       ),  # The main page. If your post doesn't work, it goes here.
    ])

if __name__ == "__main__":
    app = makeApp()
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()