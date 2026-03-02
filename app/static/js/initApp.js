function submitUser() {
  form = document.getElementById("newUserForm");
  configForm = document.getElementById("configForm");
  const step1Dot = document.getElementById("step1dot");
  const step2Dot = document.getElementById("step2dot");
  form.addEventListener("submit", function (event) {
    // 1. Stop the default form submission
    event.preventDefault();
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;
    if (password !== confirmPassword) {
      alert("Passwords do not match!");
      return;
    }
    const formData = new FormData(form);
    fetch("/users/add", {
      method: "POST",

      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.message == "Success") {
          alert("User registered successfully!");
          form.classList.add("d-none");
          step2Dot.classList.add("active");
          step1Dot.classList.remove("active");
          configForm.classList.remove("d-none");
        } else {
          alert("Error: " + data.message);
        }
      })

      .catch((error) => {
        console.error("Error:", error);
        alert("An error occurred while registering the user.");
      });
  });
}
function unhideControllerInputs() {
  const apiTypeSelect = document.getElementById("apiType");
  const controllerUsernameInput = document.getElementById("controllerUsername");
  const controllerPasswordInput = document.getElementById("controllerPassword");
  const controllerApiKeyInput = document.getElementById("controllerApiKey");

  apiTypeSelect.addEventListener("change", function () {
    if (this.value == "unifi") {
      if (controllerApiKeyInput.classList.contains("d-none")) {
        controllerApiKeyInput.classList.remove("d-none");
      }
      if (!controllerUsernameInput.classList.contains("d-none")) {
        controllerUsernameInput.classList.add("d-none");
      }
      if (!controllerPasswordInput.classList.contains("d-none")) {
        controllerPasswordInput.classList.add("d-none");
      }
    } else if (this.value == "omada") {
      if (controllerUsernameInput.classList.contains("d-none")) {
        controllerUsernameInput.classList.remove("d-none");
      }
      if (controllerPasswordInput.classList.contains("d-none")) {
        controllerPasswordInput.classList.remove("d-none");
      }
      if (!controllerApiKeyInput.classList.contains("d-none")) {
        controllerApiKeyInput.classList.add("d-none");
      }
    }
  });
}
function submitConfig() {
  const btn = document.getElementById("saveConfig");
  const form = document.getElementById("configForm");
  const spinner = document.getElementById("configSpinner");
  const btnText = document.getElementById("configBtnText");
  const dbSpinner = document.getElementById("dbSpinner");

  function isValidIP(inputText) {
    const ipv4Regex =
      /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;

    if (ipv4Regex.test(inputText)) {
      return true; // The format is correct
    } else {
      return false; // The format is incorrect
    }
  }

  btn.addEventListener("click", function (e) {
    e.preventDefault();
    controllerIp = document.getElementById("controllerIpInput").value;
    if (!isValidIP(controllerIp)) {
      alert("Please enter a valid IP address.");
      return;
    }

    // Show loading spinner and disable button
    spinner.classList.remove("d-none");
    btnText.textContent = "Saving...";
    btn.disabled = true;

    const formData = new FormData(form);
    fetch("/newConfig", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        // Hide spinner and re-enable button
        spinner.classList.add("d-none");
        btnText.textContent = "Save Configuration";
        btn.disabled = false;

        if (data.message == "Success") {
          alert(data.details);
          form.classList.add("d-none");
          dbSpinner.classList.remove("d-none");

          console.log("Database initialization triggered");
          fetch("/init", { method: "GET" })
            .then((response) => response.json())
            .then((data) => {
              if (data.message == "Success") {
                alert("Database Initialization Success: "+ data.details)
                window.location.href = "/admin";
              } else {
                alert("Error during database initialization: " + data.details);
                form.classList.remove("d-none");
                dbSpinner.classList.add("d-none");
              }
            })
            .catch((error) => {
              console.error("Error:", error);
              alert("An error occurred while initializing the database.");
            });
        } else {
          alert("Error: " + data.details);
        }
      })

      .catch((error) => {
        // Hide spinner and re-enable button on error
        spinner.classList.add("d-none");
        btnText.textContent = "Save Configuration";
        btn.disabled = false;

        console.error("Error:", error);
        alert("An error occurred while saving the configuration.");
      });
  });
}

submitConfig();
unhideControllerInputs();
submitUser();
const html = document.documentElement;
const themeToggle = document.getElementById("themeToggle");
const themeIcon = document.getElementById("themeIcon");
function applyTheme(t) {
  html.setAttribute("data-bs-theme", t);
  themeIcon.className =
    t === "dark" ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
  localStorage.setItem("ks-theme", t);
}
applyTheme(localStorage.getItem("ks-theme") || "light");
themeToggle.addEventListener("click", () => {
  applyTheme(html.getAttribute("data-bs-theme") === "dark" ? "light" : "dark");
});

window.goToStep2 = function () {
  document.getElementById("step1dot").className = "step-dot done";
  document.getElementById("step1dot").innerHTML = '<i class="bi bi-check"></i>';
  document.getElementById("stepLine").classList.add("done");
  document.getElementById("step2dot").classList.add("active");
  document.getElementById("step1label").className = "step-label done";
  document.getElementById("step2label").className = "step-label active";
};
