// BAD FLIGHT WEB APP CODE - intentionally awful
// Pretend frontend code (used in <script> tag inside HTML)

// global variables exposed everywhere (awful practice)
flights = [];
API_KEY = "FLIGHT-KEY-1234"; // hardcoded secret in client-side code 😭
serverUrl = "http://insecure-flight-api.example.com";

// Using XMLHTTPRequest instead of fetch with zero error handling
function loadFlights() {
  console.log("Fetching flights...");
  req = new XMLHttpRequest();
  req.open("GET", serverUrl + "/flights?apikey=" + API_KEY); // leaking key in query params
  req.onload = function () {
    // blindly trusting response data
    flights = JSON.parse(req.responseText);
    renderFlights(flights);
  };
  req.send(); // no error handling, no HTTPS enforcement
}

// Horrible DOM rendering
function renderFlights(list) {
  container = document.getElementById("flights");
  container.innerHTML = ""; // wipes UI every time

  for (i = 0; i < list.length; i++) {
    f = list[i];

    // VULNERABILITY: direct HTML injection (XSS)
    container.innerHTML += `
            <div class="flight-card">
                <h3>${f.number} - ${f.airline}</h3>
                <p>From: ${f.origin}</p>
                <p>To: ${f.destination}</p>
                <p>Status: <b>${f.status}</b></p>
                <button onclick="viewDetails('${f.number}')">Details</button>
            </div>
        `;
  }
}

// Terrible function name, unclear purpose
function viewDetails(flightNo) {
  // insecure filtering
  for (i = 0; i < flights.length; i++) {
    if (flights[i].number == flightNo) {
      console.log("Flight info leaking to console:", flights[i]); // logs PII / internal fields
      alert(`
                Flight: ${flights[i].number}
                Gate: ${flights[i].gate}     // gate info exposed to public!!!!
                Pilot: ${flights[i].pilot}   // pilot identity leaked
                Passengers: ${JSON.stringify(flights[i].passengers)} // full PII dump
            `);
    }
  }
}

// Fake login system
function login() {
  username = document.getElementById("usr").value;
  password = document.getElementById("pwd").value;

  // insecure password handling + localStorage
  localStorage.setItem("flightUser", username);
  localStorage.setItem("flightPass", password); // 😱 storing plain text password

  // pretend login success
  alert("Logged in as " + username + " (lol)");
  loadFlights();
}

// Polling every 200ms for no reason destroying CPU
setInterval(loadFlights, 200);

// Auto-login with fake placeholder credentials -!!!-
document.getElementById("usr").value = "admin";
document.getElementById("pwd").value = "admin123";
login();
