export interface Conversation {
  id: number;
  name: string | null;
  contacts: Contact[]
}

export interface Contact {
  id: number;
  contact_name: string | null;
  address: string;
}

export interface Media {
  id: number;
  content_type: string;
  filename: string;
}

export interface ConversationMedia {
  id: number;
  content_type: string;
  filename: string;
  message_id: number;
  date: string;
  contact_id: number;
  contact_name: string;
  contact_address: string;
}

export interface Message {
  id: number;
  direction: 'inbox' | 'sent';
  contact: string | null;
  text: string;
  date: string;
  media: Media[];
}
