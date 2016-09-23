/* global $ from jquery library */
var video = $("video")[0];

// Here, I begin to deal with playing and pausing the video.
function togglePlay() {
    if ( video.paused ) {   // If the video is paused, we play it.
        $("#play").attr("src", "css/icons/pauseButton.png");
        video.play();
        if ( video.ended ) video.load();

    } else {                // If the video is playing, we pause it.
        $("#play").attr("src", "css/icons/playButton.png");
        video.pause();

    }
}
$("#play").click(togglePlay);   // When user clicks the pause-play button.
$("video").click(togglePlay);   // When user clicks the video itself.
$("body").keydown(function(event) { // When the user presses space.
    if ( event.keyCode == 32 ) togglePlay();
});

video.onended = function() {
    $("#play").attr("src", "css/icons/playButton.png");
    video.pause();
};

// Here, I implement the time's seek-bar.
$("#time").click(function(event) {
    var position = event.layerX || event.offsetX;
    var maxPosition = $("#time")[0].offsetWidth + 3;
    var percentage = position / maxPosition;

    $("#timeBar").css("padding-right", 
        (percentage * 100).toString() + "%");
    video.currentTime = video.duration * percentage;
});

video.ontimeupdate = function(arg) {
    var percentage = video.currentTime / video.duration;
    $("#timeBar").css("padding-right", 
        (percentage * 100).toString() + "%");
};

// Here, I work on autohiding the controls.
$("#controls").fadeOut("fast");
$("body").hover(
    function(){ $("#controls").fadeIn("fast") }, 
    function(){ $("#controls").fadeOut("fast") }
);