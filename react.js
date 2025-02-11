import { useEffect, useState } from "react";

function Messages(){
    const [messages, setMessages] = useState([])
    useEffect(() => {
        fetch('http://localhost:5001')
            .then(response => response.json())
            .then(data => setMessages(data));
    }, []);
    return (
        <div>
            <h1>Messages</h1>
            <ul>
                {messages.map((message, index) => (
                    <li key={index}>
                        <strong>{message.sender}</strong>: {message.content} <br />
                        <small>{message.timestamp}</small>
                    </li>
                ))}
            </ul>
        </div>
    );
};
