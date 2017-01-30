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

templates   = tornado.template.Loader("html")

client      = motor.motor_tornado.MotorClient( config.db )  # Two connections,
blockClient = pymongo.MongoClient( config.db )              # because blocking.

database    = client[ config.name ]
blockDB     = blockClient[ config.name ]                

def counterStartup(value, error): # Defines counters.
    if value == None:
        database.counters.insert( {"video"  : 1} )
        database.counters.insert( {"user"   : 1} )

blockDB.counters.find_one( # Simple test to see if the counters are defined.
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

class uploadVideo(tornado.web.RequestHandler):
    def post(self):
        if "video" in self.request.files: # Checks if user uploaded a video.

            videoTitle  = self.get_argument("title") or "Untitled Video"
            videoTags   = self.get_argument("tags" ) or "no-tag-vid"
            pasteBin    = self.get_argument("paste", "No Pasted Info")

            # I create a temporary video file here so that I can edit it with MoviePy
            videoData = self.request.files["video"][0]
            fileType = videoData["filename"].split(".")[-1]
            with open("tempFiles/video."+fileType, "wb") as file:
                file.write(videoData["body"])
            videoClip = vid.VideoFileClip("tempFiles/video."+fileType)

            def newVideo(value, error):
                database.counters.update(
                    {'_id'  : value['_id']      },
                    {'video': value['video']+1  }
                )

                if config.watermark:
                    watermark = vid.ImageClip(
                        "watermark.png", 
                        duration=videoClip.duration
                    )
                    fullVideo = vid.CompositeVideoClip([videoClip, watermark])

                else: 
                    fullVideo = videoClip

                fullVideo.write_videofile(
                    "videos/" + to36( value['video'] ) + ".webm"
                )

                database.videos.insert({
                    "vidID" : to36( value['video'] ),
                    "title" : videoTitle,
                    "tags"  : videoTags,
                    "paste" : pasteBin,
                })

                self.redirect("/v" + to36( value['video'] ) + ".webm")

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

def searchEngine(keywords, page):
#    for word in keywords:
#        x = blockDB.videos.find({ "tags" : word }).sort({"vidID":-1})
    print( blockDB.videos.find({ "tags" : keywords[0] }) )
    return ["xd"]

class search(tornado.web.RequestHandler):
    def get(self):

        try:    keywords = self.get_argument('query').split("+")
        except: return False

        try:    page = int(keywords = self.get_argument('page'))
        except: page = 0

        result = searchEngine(keywords, page)

        self.write("\n".join(result))

class index(tornado.web.RequestHandler):
    def get(self):
        self.write( templates.load("index.html").generate(
            name = config.name,
        ) )

def makeApp():
    return tornado.web.Application([
        (r"/js/(.*)",   tornado.web.StaticFileHandler, {"path":"js"}        ),      # This handles serving javascript.
        (r"/css/(.*)",  tornado.web.StaticFileHandler, {"path":"css"}       ),      # This handles the serving of stylesheets.
        (r"/r(.*)",     tornado.web.StaticFileHandler, {"path":"videos"}    ),      # It should be noted, there is no '/' after 'r'. This handles serving raw video.
        (r"/e(\w*)",    embedVideo  ),  # An embeded video.
        (r"/v(\w*)",    watchVideo  ),  # A normal video page.
        (r"/upload",    uploadVideo ),  # The uploads form.
        (r"/search",    search      ),
        (r"/.*",        index       ),  # The main page. If your post doesn't work, it goes here.
    ])

if __name__ == "__main__":
    app = makeApp()
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()