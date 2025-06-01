import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Contact } from '../types';

export default function ContactList() {
  const [contacts, setContacts] = useState<Contact[]>([]);

  useEffect(() => {
    fetch('/api/contacts')
      .then(res => res.json())
      .then(setContacts);
  }, []);

  return (
    <div style={{ padding: '1rem' }}>
      <h2>Contacts</h2>
      <ul>
        {contacts.map(contact => (
          <li key={contact.id}>
            <Link to={`/conversation/${contact.id}`}>
              {contact.contact_name || contact.address}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
