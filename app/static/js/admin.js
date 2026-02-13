// JavaScript for admin page
// Function to send logs to the server
function sendLog(message){
    fetch('/log', {
      method: 'POST', 
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ "message": message }),
    })
    .then(response => response.json())
    .then(data => {
      console.log('Success:', data);
    })
    .catch((error) => {
      console.error('Error:', error);
    });}
// Function to handle the edit user modal
function editUserModal(){
    button = document.querySelectorAll(".editUser")
    button.forEach((e) => { 
        e.addEventListener("click", function(event){
            const btn = event.target;
            row = btn.closest("tr");
            id = row.children[0].value;
            userName= row.children[1].textContent;
            role = row.children[2].textContent;
            console.log(role)
            formID =document.getElementById("editUserId");
            formID.value = id;
            formUsername = document.getElementById("editUsername");
            formUsername.value = userName
            formRole = document.getElementById("editRole")
            if (role == 'Admin'){
                formRole.value = 'admin'
            }

        } )
        
    });
}
// Function to handle the configuration form
function editConfig(){
apiType = document.getElementById("apiType");

function changeForm(){
    username = document.getElementById("userName");
    password = document.getElementById("configPassWord");
    apiKey = document.getElementById("apiKey");
    apiType = document.getElementById("apiType");
    if (apiType.value == 'omada'){
        apiKey.classList.add("d-none");
        username.classList.remove("d-none");
        password.classList.remove("d-none")   ;
    }
    else {
        apiKey.classList.remove("d-none");
        username.classList.add("d-none");
        password.classList.add("d-none") ;
    };
}
apiType.addEventListener("change", changeForm);
changeForm();
}

// Function to enable editing of the configuration form
function enableEdit(){
    editButton = document.getElementById("enableEdit");

    editButton.addEventListener("click", function(){
        apiType = document.getElementById("apiType");
        username = document.getElementById("userNameInput");
        password = document.getElementById("pwInput");
        apiKey = document.getElementById("apiKeyInput");
        controllerIp=document.getElementById("controllerInput");
        button = document.getElementById("submitConfig");
        sendLog("Edit Config Button Clicked");
        if (apiType.hasAttribute("disabled")){
            apiType.removeAttribute("disabled");
            username.removeAttribute("disabled");
            password.removeAttribute("disabled");
            apiKey.removeAttribute("disabled");
            controllerIp.removeAttribute("disabled");
            editButton.textContent = "Cancel Edit";
            button.classList.remove("d-none");
        }
        else {            
            apiType.setAttribute("disabled", '');
            username.setAttribute("disabled", '');
            password.setAttribute("disabled", '');
            apiKey.setAttribute("disabled", '');
            controllerIp.setAttribute("disabled", '');
             editButton.textContent = "Edit Configuration";
             button.classList.add("d-none");
            
        }
        
    })
}
//function to enable editing of the SSID table
function enableSSIDEdit(){
    editButton = document.getElementById("editSsids");
    editButton.addEventListener("click", function(){
        sendLog("Edit SSIDs Button Clicked");
        btns = document.querySelectorAll(".ssidEdit");
        btns.forEach((e) => {
            if (e.classList.contains("disabled")){
                e.classList.remove("disabled");
                
                editButton.textContent = "Cancel Edit";
            }
            else {
                e.classList.add("disabled");
                editButton.textContent = "Edit SSIDs";
            }
        })
    })
}



// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
 const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
  
  tabButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      
      // Get target tab pane
      const targetId = this.getAttribute('data-bs-target');
      
      // Hide all tab panes
      document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('show', 'active');
      });
      
      // Show target tab pane
      const targetPane = document.querySelector(targetId);
      if (targetPane) {
        targetPane.classList.add('show', 'active');
      }
      
      // Update active state on buttons
      tabButtons.forEach(btn => {
        btn.classList.remove('active');
      });
      this.classList.add('active');
    });
  });

  // Theme Management
  const themeToggle = document.getElementById('themeToggle');
  const themeSelect = document.getElementById('themeSelect');
  const applyThemeBtn = document.getElementById('applyTheme');
  const html = document.documentElement;

  // Load saved theme
  const savedTheme = localStorage.getItem('theme') || 'light';
  html.setAttribute('data-bs-theme', savedTheme);
  if (themeSelect) themeSelect.value = savedTheme;

  // Theme toggle click
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const currentTheme = html.getAttribute('data-bs-theme');
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';
      html.setAttribute('data-bs-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      if (themeSelect) themeSelect.value = newTheme;
    });
  }

  // Apply theme from dropdown
  if (applyThemeBtn) {
    applyThemeBtn.addEventListener('click', () => {
      const selectedTheme = themeSelect.value;
      if (selectedTheme === 'auto') {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const autoTheme = prefersDark ? 'dark' : 'light';
        html.setAttribute('data-bs-theme', autoTheme);
      } else {
        html.setAttribute('data-bs-theme', selectedTheme);
      }
      localStorage.setItem('theme', selectedTheme);
    });
  }

  // Now call your existing functions
  enableSSIDEdit();
  enableEdit();
  editConfig();
  editUserModal();
});