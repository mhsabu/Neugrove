"use client";

import { useChat } from "ai/react";
import { useMemo } from "react";
import { insertDataIntoMessages } from "./transform";
import { ChatInput, ChatMessages } from "./ui/chat";
import { ref, push } from 'firebase/database';
import database from '../firebase'; 

export default function ChatSection() {
  const {
    messages,
    input,
    isLoading,
    handleSubmit,
    handleInputChange,
    reload,
    stop,
    data,
  } = useChat({
    api: process.env.NEXT_PUBLIC_CHAT_API,
    headers: {
      "Content-Type": "application/json", // using JSON because of vercel/ai 2.2.26
    },
  });

  const transformedMessages = useMemo(() => {
    return insertDataIntoMessages(messages, data);
  }, [messages, data]);
  const beforeHandleSubmit = (e:any) => {
    e.preventDefault(); // Prevent the default form submission behavior
  
    // Create a reference to the 'messages' node
    const messagesRef = ref(database, 'messages');
  
    // Push a new child to 'messages' with the input data
    push(messagesRef, {
      question: input,
    }).then(() => {
      console.log('Data saved successfully!');
      // Reset input or perform other actions upon successful data submission
    }).catch((error) => {
      console.error(error);
    });
  
    console.log("Input found", input);
  
    // Assuming handleSubmit is your custom logic to handle form submission after pushing data to Firebase
    handleSubmit(e); 
  };

  return (
    <div className="space-y-4 max-w-5xl w-full">
      <ChatMessages
        messages={transformedMessages}
        isLoading={isLoading}
        reload={reload}
        stop={stop}
      />
      <ChatInput
        input={input}
        handleSubmit={beforeHandleSubmit}
        handleInputChange={handleInputChange}
        isLoading={isLoading}
        multiModal={process.env.NEXT_PUBLIC_MODEL === "gpt-4-vision-preview"}
      />
    </div>
  );
}
