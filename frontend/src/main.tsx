import React from 'react';
import ReactDOM from 'react-dom/client';
import {
  createBrowserRouter,
  RouterProvider,
} from 'react-router-dom';
import '@mantine/core/styles.css';
import App from './App';
import ContactList from './pages/ContactList';
import Conversation from './pages/Conversation';
import ConversationMedia from './pages/ConversationMedia';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { path: '/', element: <ContactList /> },
      { path: '/conversation/:conversationId', element: <Conversation /> },
      { path: '/conversation/:conversationId/media', element: <ConversationMedia /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
