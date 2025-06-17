document.addEventListener('DOMContentLoaded', function() {
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    const fileInput = document.getElementById('file-input'); // Get file input

    sendButton.addEventListener('click', sendMessage);

    userInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });

    async function sendMessage() {
        const messageText = userInput.value.trim();
        const file = fileInput.files[0]; // Get the selected file

        if (!messageText && !file) {
            alert("Please enter a message or select a file.");
            return;
        }


        // Append user message to the chat
        if (messageText) {
            if(file) {
                appendMessage('user', messageText, file);
            }
            else {
                appendMessage('user', messageText);
            }
        }

        // Clear the input field
        userInput.value = '';

        // Clear the file input
        fileInput.value = null;  // Reset the file input to allow re-uploading the same file

        // Call the backend to get the bot's response, including the file
        getBotResponse(messageText, file);
    }

    function appendMessage(sender, messageText, file) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(`${sender}-message`);

        let iconHtml = '';
        if (sender === 'user') {
            iconHtml = '<i class="fas fa-user"></i> ';  // User Icon
        } else if (sender === 'bot') {
            iconHtml = '<i class="fas fa-robot"></i> '; // Bot Icon
        }

        let messageContent = iconHtml + messageText.replace(/\n/g, '<br>');

        if (file) {
            messageContent += `<br><strong>File:</strong> ${file.name} (${file.type}, ${file.size} bytes)`;

            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    messageContent += `<br><img src="${e.target.result}" alt="Uploaded Image" style="max-width: 200px;">`;
                    messageDiv.innerHTML = messageContent;
                    messagesContainer.appendChild(messageDiv);
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                };
                reader.readAsDataURL(file);
                return;
            }
        }

        messageDiv.innerHTML = messageContent;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }


    async function getBotResponse(message, file) {
        try {
            const formData = new FormData(); // Use FormData to send files

            if (message) {
                formData.append('message', message); // Append the text message
            }

            if (file) {
                formData.append('file', file); // Append the file
            }

            const response = await fetch('/api/chat', {
                method: 'POST',
                body: formData  // Send FormData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data && data.response) {
                appendMessage('bot', data.response);
            } else {
                appendMessage('bot', "Error: Could not get a response.");
            }


        } catch (error) {
            console.error("Error fetching bot response:", error);
            appendMessage('bot', "Error: Could not connect to the server."); // Provide user-friendly error
        }
    }
});