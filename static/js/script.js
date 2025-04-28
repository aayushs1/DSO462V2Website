// DOM Elements
const newChatBtn = document.getElementById('new-chat-btn');
const chatArea = document.getElementById('chat-area');
const welcomeContainer = document.getElementById('welcome-container');
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const exampleQueries = document.querySelectorAll('.example-query');

// Variables
let currentChatId = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is logged in
    const userSection = document.querySelector('.user-section');
    const isLoggedIn = userSection && userSection.querySelector('.user-name') && 
                       userSection.querySelector('.user-name').textContent.trim() !== '';
    
    // If not logged in, show login message and disable chat functionality
    if (!isLoggedIn && welcomeContainer) {
        // Replace welcome container with login message
        welcomeContainer.innerHTML = `
            <div class="welcome-header">
                <h1>Please Log In</h1>
                <p>You need to log in to use GoGoPrint and access your 3D models.</p>
                <a href="/login" class="login-btn">Log In</a>
                <p class="signup-text">Don't have an account? <a href="/signup">Sign Up</a></p>
            </div>
        `;
        
        // Disable message input
        if (messageInput) {
            messageInput.disabled = true;
            messageInput.placeholder = "Please log in to chat...";
        }
        
        // Disable send button
        if (sendBtn) {
            sendBtn.disabled = true;
        }
        
        // Hide the chat history in sidebar if visible
        const historySection = document.querySelector('.history');
        if (historySection) {
            historySection.style.display = 'none';
        }
        
        // Early return to prevent other event listeners from being added
        return;
    }

    // Enable/disable send button based on input
    messageInput.addEventListener('input', () => {
        sendBtn.disabled = messageInput.value.trim() === '';
    });

    // Send message on enter key (but allow shift+enter for new lines)
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !sendBtn.disabled) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Send button click
    sendBtn.addEventListener('click', sendMessage);

    // New chat button
    if (newChatBtn) {
        newChatBtn.addEventListener('click', createNewChat);
    }

    // Example queries
    exampleQueries.forEach(query => {
        query.addEventListener('click', () => {
            const prompt = query.dataset.prompt;
            if (prompt) {
                messageInput.value = prompt;
                messageInput.dispatchEvent(new Event('input'));
                sendMessage();
            }
        });
    });

    // Chat history items
    document.querySelectorAll('.chat-history-item').forEach(item => {
        item.addEventListener('click', () => {
            const chatId = item.dataset.chatId;
            if (chatId) {
                window.location.href = `/chat/${chatId}`;
            }
        });
    });

    // Download buttons
    document.addEventListener('click', function(e) {
        // Handle download button click
        if (e.target.classList.contains('download-btn')) {
            // Find the closest download options group
            const downloadOptions = e.target.nextElementSibling;
            if (downloadOptions) {
                // Toggle display of format options
                downloadOptions.classList.toggle('show');
            }
        }

        // Handle format button click
        if (e.target.classList.contains('format-btn')) {
            const format = e.target.dataset.format;
            const modelName = e.target.closest('.model-controls').querySelector('.model-info').textContent.split(' ')[0];

            // Simulate download of the selected format
            downloadModel(modelName, format);

            // Visual feedback - add active class
            document.querySelectorAll('.format-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            e.target.classList.add('active');
        }
    });
    
    // Check if we're in an existing chat by looking at the URL
    const pathParts = window.location.pathname.split('/');
    if (pathParts.length > 2 && pathParts[1] === 'chat') {
        currentChatId = pathParts[2]; // Set the current chat ID
    }
});

// Function to handle model download
function downloadModel(modelName, format) {
    // Check if user is logged in before allowing download
    const userSection = document.querySelector('.user-section');
    const isLoggedIn = userSection && userSection.querySelector('.user-name') && 
                       userSection.querySelector('.user-name').textContent.trim() !== '';
    
    if (!isLoggedIn) {
        alert('Please log in to download models');
        window.location.href = '/login';
        return;
    }
    
    // In a real implementation, this would trigger the actual download
    console.log(`Downloading ${modelName} in ${format.toUpperCase()} format`);

    // You could implement an actual download here with:
    // window.location.href = `/download/${modelName}?format=${format}`;

    // Or using fetch:
    fetch(`/download/${modelName}?format=${format}`)
        .then(response => {
            if (response.status === 401) {
                // User is not authenticated
                alert('Please log in to download models');
                window.location.href = '/login';
                throw new Error('User not authenticated');
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `${modelName}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => {
            if (error.message !== 'User not authenticated') {
                console.error('Error downloading file:', error);
                alert(`Error downloading model. Please try again later.`);
            }
        });
}

// Create a new chat
function createNewChat() {
    // Return a promise that resolves with the chat ID
    return fetch('/chat/new', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.status === 401) {
            // User is not authenticated
            window.location.href = '/login';
            throw new Error('User not authenticated');
        }
        return response.json();
    })
    .then(data => {
        currentChatId = data.chat_id;

        // Hide welcome container and show empty chat
        if (welcomeContainer) {
            welcomeContainer.style.display = 'none';
        }

        // Clear any existing messages
        chatMessages.innerHTML = '';
        
        return currentChatId;
    })
    .catch(error => {
        console.error('Error creating new chat:', error);
        throw error; // Rethrow to handle it in the calling function
    });
}

// Send message
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    try {
        // Create chat if doesn't exist yet
        if (!currentChatId) {
            await createNewChat();
        }
        
        // Now send the message
        await sendMessageToServer(message);
        
        // Update sidebar with new chat if needed (without refreshing the page)
        if (!document.querySelector(`.chat-history-item[data-chat-id="${currentChatId}"]`)) {
            updateChatHistory();
        }
    } catch (error) {
        console.error('Error in send message flow:', error);
    }
}

// Update chat history in sidebar
function updateChatHistory() {
    fetch('/get_chat_history')
        .then(response => response.json())
        .then(data => {
            const historySection = document.querySelector('.history');
            if (historySection && data.recent_chats && data.recent_chats.length > 0) {
                // Remove "no chats" message if it exists
                const noChatsMsg = historySection.querySelector('.no-chats-message');
                if (noChatsMsg) {
                    noChatsMsg.remove();
                }
                
                // Clear existing history items and rebuild
                const existingItems = historySection.querySelectorAll('.chat-history-item');
                existingItems.forEach(item => item.remove());
                
                // Add history title if it doesn't exist
                if (!historySection.querySelector('.history-title')) {
                    const titleElem = document.createElement('h3');
                    titleElem.className = 'history-title';
                    titleElem.textContent = 'Recent Chats';
                    historySection.appendChild(titleElem);
                }
                
                // Add new history items
                data.recent_chats.forEach(chat => {
                    const chatItem = document.createElement('a');
                    chatItem.className = `chat-history-item ${chat._id === currentChatId ? 'active' : ''}`;
                    chatItem.href = `/chat/${chat._id}`;
                    chatItem.dataset.chatId = chat._id;
                    
                    chatItem.innerHTML = `
                        <img src="/static/img/${chat.image}" alt="${chat.title}" width="24" height="24" style="border-radius: 4px; margin-right: 10px;">
                        <p>${chat.title}</p>
                    `;
                    
                    chatItem.addEventListener('click', (e) => {
                        e.preventDefault();
                        window.location.href = chatItem.href;
                    });
                    
                    historySection.appendChild(chatItem);
                });
            }
        })
        .catch(error => {
            console.error('Error updating chat history:', error);
        });
}

// Send message to server
function sendMessageToServer(message) {
    // Add user message to UI
    addMessage('user', message);

    // Clear input
    messageInput.value = '';
    sendBtn.disabled = true;

    // Show typing indicator
    showTypingIndicator();

    // Send to server
    return fetch('/message/send', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            chat_id: currentChatId,
            message: message
        })
    })
    .then(response => {
        if (response.status === 401) {
            // User is not authenticated
            removeTypingIndicator();
            window.location.href = '/login';
            throw new Error('User not authenticated');
        }
        return response.json();
    })
    .then(data => {
        // Remove typing indicator
        removeTypingIndicator();

        // Process bot response
        const botResponse = data.bot_response;
        addMessage('bot', botResponse.content, botResponse);
        
        // Update the page title with the chat title if provided
        if (data.chat_title) {
            document.title = `${data.chat_title} - GoGoPrint`;
            
            // Also update the nav title if it exists
            const navTitle = document.querySelector('.nav-title');
            if (navTitle) {
                navTitle.textContent = data.chat_title;
            }
        }
    })
    .catch(error => {
        console.error('Error sending message:', error);
        removeTypingIndicator();
        // Only show error message if not redirecting due to auth error
        if (error.message !== 'User not authenticated') {
            addMessage('bot', 'Sorry, there was an error processing your request. Please try again.', null);
        }
    });
}

// Add message to UI
function addMessage(sender, content, botData = null) {
    const messageElement = document.createElement('div');
    messageElement.className = `chat-message ${sender === 'user' ? 'user-message' : ''}`;

    // Get user's initial for the avatar
    const userInitial = getUserInitial();
    
    let avatarHtml;
    let senderName;
    let currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    if (sender === 'user') {
        avatarHtml = `<div class="message-avatar user-message-avatar">${userInitial}</div>`;
        senderName = 'You';
    } else {
        avatarHtml = `
            <div class="message-avatar bot-avatar">
                <img src="/static/img/white_logo.png" alt="GoGoPrint Logo" width="24" height="24">
            </div>
        `;
        senderName = 'GoGoPrint AI';
    }

    let messageHtml = `
        <div class="message-content">
            <div class="message-header">
                <div class="message-sender">${senderName}</div>
                <div class="message-time">${currentTime}</div>
            </div>
            <div class="message-text">
                <p>${content}</p>
            </div>
    `;

    // Add model preview if it's a bot message with a model
    if (sender === 'bot' && botData && botData.model_preview) {
        let modelImage = botData.model_name.replace('.stl', '.png');
        messageHtml += `
            <div class="model-preview">
                <img src="/static/img/${modelImage}" alt="3D Model Preview">
                <div class="model-controls">
                    <div class="model-info">${botData.model_name} (${botData.model_size})</div>
                    <div class="model-actions">
                        <button class="model-btn download-btn">Download</button>
                        <div class="download-options">
                            <button class="format-btn" data-format="png">PNG</button>
                            <button class="format-btn" data-format="3mf">3MF</button>
                            <button class="format-btn" data-format="stl">STL</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    messageHtml += `</div>`;
    messageElement.innerHTML = avatarHtml + messageHtml;
    chatMessages.appendChild(messageElement);

    // Scroll to the bottom
    chatArea.scrollTop = chatArea.scrollHeight;
}

// Get user's initial for avatar
function getUserInitial() {
    const userSection = document.querySelector('.user-section');
    if (userSection && userSection.querySelector('.user-name')) {
        const userName = userSection.querySelector('.user-name').textContent.trim();
        return userName.charAt(0).toUpperCase();
    }
    return 'U'; // Default if no user name found
}

// Show typing indicator
function showTypingIndicator() {
    const typingElement = document.createElement('div');
    typingElement.className = 'chat-message';
    typingElement.id = 'typing-indicator';
    typingElement.innerHTML = `
        <div class="message-avatar bot-avatar">
            <img src="/static/img/white_logo.png" alt="GoGoPrint Logo" width="24" height="24">
        </div>
        <div class="message-content">
            <div class="message-header">
                <div class="message-sender">GoGoPrint AI</div>
                <div class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
            </div>
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(typingElement);
    chatArea.scrollTop = chatArea.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
    const typingElement = document.getElementById('typing-indicator');
    if (typingElement) {
        typingElement.remove();
    }
}