 // static/js/notifications.js

 function closeNotification() {
    document.getElementById('notification').classList.remove('show');
}

// Show the notification after a delay
setTimeout(function() {
    var notification = document.getElementById('notification');
    if (notification) {
        notification.classList.add('show');
    }
}, 100);

// Automatically hide the notification after a timeout
setTimeout(function() {
    var notification = document.getElementById('notification');
    if (notification) {
        notification.classList.remove('show');
    }
}, 5000);


// Function to handle the contact form popup
function setupContactFormPopup() {
    // Get the modal
    var modal = document.getElementById("contactModal");

    // Get the button that opens the modal
    var btn = document.getElementById("openContactForm");

    // Get the <span> element that closes the modal
    var span = document.getElementsByClassName("close")[0];

    // When the user clicks on the link, open the modal
    btn.onclick = function() {
        modal.style.display = "block";
    }

    // When the user clicks on <span> (x), close the modal
    span.onclick = function() {
        modal.style.display = "none";
    }

    // When the user clicks anywhere outside of the modal, close it
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    // Optional:  Handle form submission (in a real application, you'd send the data to a server)
    document.getElementById("contactForm").addEventListener("submit", function(event) {
        event.preventDefault(); // Prevent the default form submission

        // Get form values
        var name = document.getElementById("name").value;
        var email = document.getElementById("email").value;
        var title = document.getElementById("title").value;
        var message = document.getElementById("message").value;

        // Do something with the data (e.g., log to console, send to a server)
        console.log("Name: " + name);
        console.log("Email: " + email);
        console.log("Title: " + title);
        console.log("Message: " + message);

        // Close the modal after submission (optional)
        modal.style.display = "none";

        // Optionally, display a success message to the user
        alert("Message sent!"); // Replace with a better UI message
    });
}

// Other functions for your website (e.g., handling other forms, animations, etc.)
function setupOtherForm() {
    // Code for another form here
    console.log("Other form setup");
}

// Call the functions when the DOM is ready
document.addEventListener("DOMContentLoaded", function() {
    setupContactFormPopup();
    setupOtherForm(); // Or any other functions you have
});
