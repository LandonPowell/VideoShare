var uploadButton    = document.getElementById("uploadButton");
var uploadForm      = document.getElementById("upload");

uploadButton.onclick = function() {
    uploadForm  .classList.toggle("close");
    uploadButton.classList.toggle("close");
};