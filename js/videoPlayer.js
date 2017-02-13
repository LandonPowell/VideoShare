var video = document.getElementsByTagName("video")[0];
var playButton  = document.getElementById("play");
var time        = document.getElementById("time");
var timeBar     = document.getElementById("timeBar");
var controls    = document.getElementById("controls");
// Here, I begin to deal with playing and pausing the video.
function togglePlay() {
    if ( video.paused ) {   // If the video is paused, we play it.
        playButton.src =  "css/icons/pauseButton.png";
        video.play();
        if ( video.ended ) video.load();

    } else {                // If the video is playing, we pause it.
        playButton.src = "css/icons/playButton.png";
        video.pause();

    }
}
playButton.onclick  = togglePlay;   // When user clicks the pause-play button.
video.onclick       = togglePlay;   // When user clicks the video itself.
document.body.onkeydown = function(event) { // When the user presses space.
    if ( event.keyCode == 32 ) togglePlay();
};

video.onended = function() {
    playButton.src = "css/icons/playButton.png";
    video.pause();
};

// Here, I implement the time's seek-bar.
time.onclick = function(event) {
    var position = event.layerX || event.offsetX;
    var maxPosition = time.offsetWidth + 3;
    var percentage = position / maxPosition;

    timeBar.style["padding-right"] = (percentage * 100).toString() + "%";
    video.currentTime = video.duration * percentage;
};

video.ontimeupdate = function(arg) {
    var percentage = video.currentTime / video.duration;
    timeBar.style["padding-right"] = (percentage * 100).toString() + "%";
};

// Here, I autohide the controls.
document.body.onmouseover   = function(){ controls.className = "fadeIn" };
document.body.onmouseout    = function(){ controls.className = "fadeOut" };