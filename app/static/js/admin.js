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
editUserModal();