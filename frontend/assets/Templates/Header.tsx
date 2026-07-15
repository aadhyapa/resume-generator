import React from 'react';

interface HeaderProps {
  name: string;
  contact: string;
}

export function Header({ name, contact }: HeaderProps) {
  return (
    <div className="section header">
      <h1 className="name">{name}</h1>
      <div className="contact">{contact}</div>
    </div>
  );
}

export default Header;
