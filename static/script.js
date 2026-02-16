var socket = io();

function startScan() {

    const host = document.getElementById("host").value;
    const start = document.getElementById("start").value;
    const end = document.getElementById("end").value;

    if (!host || !start || !end) {
        alert("Please fill all fields");
        return;
    }

    document.getElementById("resultsOutput").innerHTML = "";
    document.getElementById("progressBar").style.width = "0%";

    socket.emit("start_scan", {
        host: host,
        start: start,
        end: end
    });
}

socket.on("scan_result", function(data) {

    var resultDiv = document.getElementById("resultsOutput");
    var progressBar = document.getElementById("progressBar");

    var div = document.createElement("div");

    if (data.status === "OPEN") {
        div.style.color = "lightgreen";
    } else if (data.status === "CLOSED") {
        div.style.color = "red";
    } else {
        div.style.color = "yellow";
    }

    div.innerHTML = `
        <strong>Port ${data.port}</strong> - ${data.status}
        <br>
        <small>${data.banner ? data.banner : ""}</small>
        <hr>
    `;

    resultDiv.appendChild(div);
    progressBar.style.width = data.progress + "%";
});
