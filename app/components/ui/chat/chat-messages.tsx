import { useEffect, useRef, useState } from 'react';
import { Dot } from 'react-animated-dots';
import ChatItem from "./chat-item";
import "./index.css";

export interface Message {
  id: string;
  content: string;
  role: string;
}

export default function ChatMessages({
  messages,
  isLoading,
  reload,
  stop,
}:{
  messages: Message[];
  isLoading?: boolean;
  stop?: () => void;
  reload?: () => void;
}
) {
  const [currentLoadingMessage, setCurrentLoadingMessage] = useState('');
  const scrollableChatContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (scrollableChatContainerRef.current) {
      scrollableChatContainerRef.current.scrollTop =
        scrollableChatContainerRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages.length]);

  useEffect(() => {
    if (isLoading) {
      const loadingMessages = [
        'Getting Advice....',
        'Got The Advice..',
        'Preparing...',
      ];
      let messageIndex = 0;

      setCurrentLoadingMessage(loadingMessages[messageIndex]); // Set initial message

      const interval = setInterval(() => {
        messageIndex = (messageIndex + 1) % loadingMessages.length; // Cycle through messages
        setCurrentLoadingMessage(loadingMessages[messageIndex]);
      }, 6000); // Change message every 10 seconds

      return () => clearInterval(interval); // Cleanup on unmount or when isLoading changes
    }
  }, [isLoading]);

  return (
    <div className="w-full max-w-5xl p-4 bg-white rounded-xl shadow-xl wrapper">
      <div
        className="flex flex-col gap-5 divide-y h-[50vh] overflow-auto"
        ref={scrollableChatContainerRef}
      >
        {messages.map((m) => (
          <ChatItem key={m.id} {...m} />
        ))}
        {isLoading && (
          <div className="text-center p-4 textColor">
            <p>The AI is:<Dot>  {currentLoadingMessage}</Dot></p>
          </div>
        )}
      </div>
    </div>
  );
}
