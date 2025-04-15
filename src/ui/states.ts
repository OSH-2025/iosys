import { reactive } from "vue";

interface Message {
  fromUser: boolean;
  content: string;
}

export const messages = reactive<Message[]>([
  {
    fromUser: false,
    content: "Hello! How can I assist you today?",
  },
  {
    fromUser: true,
    content: "I need help with my order.",
  },
  {
    fromUser: false,
    content: "Sure! Can you please provide your order number?",
  },
  {
    fromUser: true,
    content: "My order number is 12345.",
  },
  {
    fromUser: false,
    content: "Thank you! Let me check that for you.",
  },
]);
