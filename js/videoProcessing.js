/* global id */
var statusURL = "/status/" + id;
var interval;

function getStatus() {
    var request = new XMLHttpRequest();
    request.open( "GET", statusURL, false );
    request.send( null );
    console.log(request.responseText);
    return request.responseText;
}

function statusHandler(status) {
    document.getElementById("status").innerHTML = status;
    if ( status == "done" ) {
        window.clearInterval(interval);
        document.getElementById("videoBox").innerHTML =
            '<iframe id="videoEmbed" src="e'+id+'"></iframe>';
    }
}

interval = setInterval(function () {
    statusHandler( getStatus() );
}, 1000);